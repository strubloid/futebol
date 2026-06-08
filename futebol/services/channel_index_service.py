"""Service that reads M3U files and generates a curated channels/ index.

No longer writes individual per-channel JSON files — only a single aggregate
``channels/index.json`` and a ``channels/manifest.json`` summary.
Stream testing is always performed during a sync so the ``working`` flag
reflects real reachability.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import md5
from pathlib import Path
from typing import Any

import httpx

from futebol.services.playlist_parser_service import PlaylistParserService


@dataclass
class ChannelIndexEntry:
    """One channel entry for the aggregate index."""

    tvg_id: str
    name: str
    stream_url: str
    group_title: str
    logo_url: str | None
    source_playlist: str  # e.g. "sports" or "br"
    source_playlist_id: str  # e.g. "sports-m3u" or "br-m3u"
    working: bool = True
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tvgId": self.tvg_id,
            "name": self.name,
            "streamUrl": self.stream_url,
            "groupTitle": self.group_title,
            "logoUrl": self.logo_url,
            "sourcePlaylist": self.source_playlist,
            "sourcePlaylistId": self.source_playlist_id,
            "working": self.working,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelIndexEntry:
        return cls(
            tvg_id=data["tvgId"],
            name=data["name"],
            stream_url=data["streamUrl"],
            group_title=data["groupTitle"],
            logo_url=data.get("logoUrl"),
            source_playlist=data["sourcePlaylist"],
            source_playlist_id=data["sourcePlaylistId"],
            working=data.get("working", True),
            tags=list(data.get("tags", [])),
        )


class ChannelIndexService:
    """Reads M3U files and builds/updates the channels/ index.

    The output is a single ``channels/index.json`` file (the aggregate) and
    ``channels/manifest.json`` (summary stats).  No per-channel files are
    written.
    """

    _extinf_pattern = re.compile(r'([\w-]+)="([^"]*)"')

    def __init__(self, m3u_dir: Path, channels_dir: Path) -> None:
        self.m3u_dir = m3u_dir
        self.channels_dir = channels_dir
        self._parser = PlaylistParserService()

    # ------------------------------------------------------------------
    # Public commands
    # ------------------------------------------------------------------

    def load_and_test(
        self,
        concurrency: int = 20,
        timeout: float = 8.0,
    ) -> tuple[int, int]:
        """Read all M3U files, parse channels, and test every stream.

        Each channel's stream URL is probed with a HEAD request (falling
        back to a partial GET for servers that reject HEAD).  Working
        streams are marked ``working=True``; unresponsive ones are
        marked ``working=False``.

        This is the **only** sync method — stream testing is mandatory.
        There is no "preserve previous flags" path; every load is a fresh
        assessment.

        Returns:
            ``(total_entries, working_entries)``
        """
        m3u_files = sorted(self.m3u_dir.glob("*.m3u")) + sorted(self.m3u_dir.glob("*.m3u8"))
        if not m3u_files:
            print("No M3U files found in", self.m3u_dir)
            return 0, 0

        self.channels_dir.mkdir(parents=True, exist_ok=True)

        raw_entries: list[ChannelIndexEntry] = []
        seen_tvg_ids: set[str] = set()

        for m3u_path in m3u_files:
            playlist_name = m3u_path.stem
            playlist_id = m3u_path.name.replace(".", "-")
            for suffix in ("-m3u", "-m3u8"):
                if playlist_id.endswith(suffix):
                    playlist_id = playlist_id[: -len(suffix)]
                    break
            content = m3u_path.read_text(encoding="utf-8", errors="replace")
            entries = self._parse_file(content, playlist_name, playlist_id)
            for entry in entries:
                tvg_key = entry.tvg_id
                if tvg_key in seen_tvg_ids:
                    continue  # first occurrence wins
                seen_tvg_ids.add(tvg_key)
                raw_entries.append(entry)

        # ---------- test streams in parallel ----------
        total = len(raw_entries)
        tested_entries: list[ChannelIndexEntry] = list(raw_entries)
        tested = 0
        ok = 0

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_map = {
                executor.submit(self._test_stream_url, e.stream_url, timeout): i
                for i, e in enumerate(tested_entries)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                tested += 1
                try:
                    is_alive = future.result()
                except Exception:
                    is_alive = False
                tested_entries[idx].working = is_alive
                if is_alive:
                    ok += 1

        self._write_index(tested_entries)
        return total, ok

    def set_working(self, tvg_id: str, working: bool) -> bool:
        """Toggle the working flag for a channel in the aggregate index.

        Returns True if the channel was found and updated.
        """
        entries = self._load_all_entries()
        found = False
        for entry in entries:
            if entry.tvg_id == tvg_id:
                entry.working = working
                found = True
                break
        if not found:
            return False
        self._write_index(entries)
        return True

    def list_working(self) -> list[ChannelIndexEntry]:
        """List all entries marked as working."""
        return [e for e in self._load_all_entries() if e.working]

    def list_all(self) -> list[ChannelIndexEntry]:
        """List all entries including non-working."""
        return self._load_all_entries()

    # ------------------------------------------------------------------
    # Stream testing
    # ------------------------------------------------------------------

    @staticmethod
    def _test_stream_url(url: str, timeout: float = 8.0) -> bool:
        """Probe a stream URL — returns True if reachable (2xx/3xx)."""
        try:
            with httpx.Client(follow_redirects=True, timeout=timeout) as client:
                try:
                    resp = client.head(url)
                except httpx.HTTPError:
                    return False
                if resp.status_code in {405, 403}:
                    try:
                        resp = client.get(url, headers={"Range": "bytes=0-256"})
                    except httpx.HTTPError:
                        return False
                return 200 <= resp.status_code < 400
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_file(
        self,
        content: str,
        playlist_name: str,
        playlist_id: str,
    ) -> list[ChannelIndexEntry]:
        """Parse M3U content into ChannelIndexEntry list."""
        entries: list[ChannelIndexEntry] = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        pending_attrs: dict[str, str | None] | None = None

        for line in lines:
            if line.startswith("#EXTVLCOPT") or line.startswith("#EXTHTTP"):
                continue
            if line.startswith("#EXTINF"):
                pending_attrs = self._parse_extinf(line)
                continue
            if line.startswith("#"):
                continue

            if pending_attrs is None:
                continue

            tvg_id = pending_attrs.get("tvg-id")
            if not tvg_id or tvg_id == "None":
                tvg_id = "ch-" + md5(line.encode()).hexdigest()[:12]

            entries.append(
                ChannelIndexEntry(
                    tvg_id=tvg_id,
                    name=pending_attrs.get("name") or self._name_from_url(line),
                    stream_url=line,
                    group_title=pending_attrs.get("group-title") or "Ungrouped",
                    logo_url=pending_attrs.get("tvg-logo"),
                    source_playlist=playlist_name,
                    source_playlist_id=playlist_id,
                )
            )
            pending_attrs = None

        return entries

    def _parse_extinf(self, line: str) -> dict[str, str | None]:
        """Parse #EXTINF line attributes."""
        attributes: dict[str, str | None] = {
            key: value for key, value in self._extinf_pattern.findall(line)
        }
        attributes["name"] = (
            line.rsplit(",", maxsplit=1)[-1].strip() if "," in line else None
        )
        return attributes

    @staticmethod
    def _name_from_url(url: str) -> str:
        try:
            parsed = __import__("urllib.parse").urlparse(url)
            parts = [p for p in parsed.path.split("/") if p]
            return parts[-1] if parts else parsed.netloc or url
        except Exception:
            return url

    def _write_index(self, entries: list[ChannelIndexEntry]) -> None:
        """Write the aggregate ``index.json`` and ``manifest.json``.

        No individual per-channel files are written.
        """
        # 1. Write aggregate index.json for the frontend
        index_path = self.channels_dir / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "generatedAt": datetime.now(timezone.utc).isoformat(),
                    "channels": [e.to_dict() for e in entries],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # 2. Write manifest.json with summary
        manifest_path = self.channels_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "generatedAt": datetime.now(timezone.utc).isoformat(),
                    "totalChannels": len(entries),
                    "workingChannels": sum(1 for e in entries if e.working),
                    "playlists": list(
                        {
                            e.source_playlist_id: {
                                "id": e.source_playlist_id,
                                "name": e.source_playlist,
                            }
                            for e in entries
                        }.values()
                    ),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _load_all_entries(self) -> list[ChannelIndexEntry]:
        """Load all entries from the aggregate index.json."""
        index_path = self.channels_dir / "index.json"
        if not index_path.exists():
            return []
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            return [ChannelIndexEntry.from_dict(ch) for ch in data.get("channels", [])]
        except (OSError, json.JSONDecodeError, KeyError):
            return []
