"""Service that reads M3U files and manages the single channels/ index.

All three public operations (load_servers, update_channels, restore_channels)
work directly on ``channels/index.json`` — the single source of truth for
both the backend and the Angular frontend.

No per-channel files, no bridge service — the list IS the source of truth.
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import time
import urllib.error
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor, as_completed, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import md5
from pathlib import Path
from typing import Any

import httpx

from futebol.services.playlist_parser_service import PlaylistParserService


@dataclass
class ChannelIndexEntry:
    """One channel entry in the aggregate index."""

    tvg_id: str
    name: str
    stream_url: str
    group_title: str
    logo_url: str | None
    source_playlist: str  # e.g. "sports" or "br"
    source_playlist_id: str  # e.g. "sports-m3u" or "br-m3u"
    working: bool = True
    tags: list[str] = field(default_factory=list)
    extra_headers: dict[str, str] = field(default_factory=dict)
    """Extra HTTP headers the stream needs (e.g. Referer, User-Agent)."""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
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
        if self.extra_headers:
            d["extraHeaders"] = dict(self.extra_headers)
        return d

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
            extra_headers=dict(data.get("extraHeaders", {})),
        )


@dataclass
class LoadServersResult:
    """Result of a load_servers() run."""

    total: int
    working: int
    new_working: int
    updated_urls: int
    backup_path: str | None = None


@dataclass
class UpdateChannelsResult:
    """Result of an update_channels() run."""

    before: int
    after: int
    removed: int
    backup_path: str | None = None


class ChannelIndexService:
    """Reads M3U files and manages ``channels/index.json``.

    Three public entry points:

    * ``load_servers`` — parse M3U sources, test streams, merge into index
    * ``update_channels`` — re-test every channel, keep only working ones
    * ``restore_channels`` — restore index from ``channels/backup.json``
    """

    _extinf_pattern = re.compile(r'([\w-]+)="([^"]*)"')

    def __init__(self, m3u_dir: Path, channels_dir: Path) -> None:
        self.m3u_dir = m3u_dir
        self.channels_dir = channels_dir
        self._parser = PlaylistParserService()
        # Paths
        self._index_path = channels_dir / "index.json"
        self._manifest_path = channels_dir / "manifest.json"
        self._backup_path = channels_dir / "backup.json"
        self._frontend_dir = (
            channels_dir.parent / "frontend" / "public" / "channels"
        )

    # ------------------------------------------------------------------
    # 1. Load Servers
    # ------------------------------------------------------------------

    def load_servers(
        self,
        concurrency: int = 20,
        timeout: float = 8.0,
    ) -> LoadServersResult:
        """Parse all M3U files in ``m3u/`` and merge into the channel index.

        * **New channels** — stream is tested; only added if working.
        * **Existing channels, same URL** — kept untouched (preserves order).
        * **Existing channels, different URL** — new URL is tested; updated
          only if the new stream is reachable, otherwise old entry stays.
        * Working new channels are **appended** to the end of the list.

        Existing ``index.json`` is backed up to ``backup.json`` before
        overwriting.

        Returns:
            A :class:`LoadServersResult` with counts.
        """
        # 1. Read existing index
        existing: dict[str, ChannelIndexEntry] = {}
        existing_order: list[str] = []  # preserves insertion order
        for entry in self._load_all_entries():
            existing[entry.tvg_id] = entry
            existing_order.append(entry.tvg_id)

        # 2. Parse all M3U sources
        m3u_files = sorted(self.m3u_dir.glob("*.m3u")) + sorted(
            self.m3u_dir.glob("*.m3u8")
        )
        if not m3u_files:
            print("No M3U files found in", self.m3u_dir)
            return LoadServersResult(total=0, working=0, new_working=0, updated_urls=0)

        parsed: list[ChannelIndexEntry] = []
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
                if entry.tvg_id not in seen_tvg_ids:
                    seen_tvg_ids.add(entry.tvg_id)
                    parsed.append(entry)

        # 3. Decide what to test and what to keep
        test_jobs: list[tuple[int, ChannelIndexEntry, str | None]] = []
        # (index_in_parsed, entry, old_url_or_None_if_new)

        kept_entries: list[ChannelIndexEntry] = []

        for i, pe in enumerate(parsed):
            existing_entry = existing.get(pe.tvg_id)

            if existing_entry is None:
                # NEW channel — test stream, only add if working
                test_jobs.append((i, pe, None))
            elif existing_entry.stream_url == pe.stream_url:
                # Same URL — keep existing as-is (preserve order & status)
                # Don't re-test, don't change anything
                kept_entries.append(existing_entry)
            else:
                # URL changed — test new URL first
                test_jobs.append((i, pe, existing_entry.stream_url))

        # 4. Test streams in parallel
        new_working_count = 0
        updated_url_count = 0
        tested_results: dict[int, ChannelIndexEntry] = {}
        job_details: dict[int, str | None] = {}  # idx → old_url (None = new)

        with ThreadPoolExecutor(max_workers=concurrency) as executor:

            def test_and_return(idx: int, entry: ChannelIndexEntry, old_url: str | None) -> tuple[int, ChannelIndexEntry, bool]:
                """Test stream, return (idx, entry_or_fallback, changed)."""
                is_alive = self._test_stream_url(entry.stream_url, timeout, entry.extra_headers)
                if is_alive:
                    return idx, entry, True
                # Stream failed — if this was a URL update, keep the old entry
                if old_url is not None:
                    old_entry = existing.get(entry.tvg_id)
                    if old_entry is not None:
                        return idx, old_entry, False
                # Stream failed and it's a new channel — don't add
                entry.working = False
                return idx, entry, False

            future_map: dict[Future, tuple[int, ChannelIndexEntry, str | None]] = {}
            for parsed_idx, entry, old_url in test_jobs:
                future_map[executor.submit(test_and_return, parsed_idx, entry, old_url)] = (
                    parsed_idx, entry, old_url,
                )
                job_details[parsed_idx] = old_url

            deadline = time.monotonic() + timeout + 5.0
            while future_map:
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    for f in future_map:
                        f.cancel()
                    break

                done, not_done = wait(
                    future_map.keys(),
                    timeout=min(remaining_time, 2.0),
                )
                for future in done:
                    parsed_idx, result_entry, was_live = future.result(timeout=0.1)
                    tested_results[parsed_idx] = result_entry
                    future_map.pop(future, None)
                    if was_live:
                        old_url = job_details.get(parsed_idx)
                        if old_url is None:
                            new_working_count += 1
                        else:
                            updated_url_count += 1

                # On last stretch, cancel stragglers
                if not_done and remaining_time <= 2.0:
                    for f in not_done:
                        f.cancel()
                    cancel_done, _ = wait(not_done, timeout=0.5)
                    for future in cancel_done:
                        parsed_idx, result_entry, was_live = future.result(timeout=0.1)
                        tested_results[parsed_idx] = result_entry
                        future_map.pop(future, None)
                    for f in list(future_map.keys()):
                        parsed_idx = future_map[f][0]
                        f.cancel()
                        future_map.pop(f, None)
                        # Don't add failed channel

        # 5. Build final list: existing order + new working channels appended
        final_entries: list[ChannelIndexEntry] = []

        # Preserve existing order first
        for tvg_id in existing_order:
            if tvg_id in existing:
                entry = existing[tvg_id]
                # Check if this entry was in the test results (URL changed)
                parsed_idx = next(
                    (i for i, pe in enumerate(parsed) if pe.tvg_id == tvg_id),
                    None,
                )
                if parsed_idx is not None and parsed_idx in tested_results:
                    final_entries.append(tested_results[parsed_idx])
                else:
                    final_entries.append(entry)

        # Append new working channels at the end
        for idx, entry, old_url in test_jobs:
            if old_url is None:  # was new
                result_entry = tested_results.get(idx)
                if result_entry is not None and result_entry.working:
                    final_entries.append(result_entry)

        # 6. Backup existing index before overwriting
        backup_path = self._backup_current_index()

        # 7. Write
        total = len(final_entries)
        working_count = sum(1 for e in final_entries if e.working)
        self._write_index(final_entries)

        return LoadServersResult(
            total=total,
            working=working_count,
            new_working=new_working_count,
            updated_urls=updated_url_count,
            backup_path=str(backup_path) if backup_path else None,
        )

    # ------------------------------------------------------------------
    # 2. Update Channels — re-test all, keep only working
    # ------------------------------------------------------------------

    def update_channels(
        self,
        concurrency: int = 20,
        timeout: float = 8.0,
    ) -> UpdateChannelsResult:
        """Re-test every channel's stream; remove non-working ones.

        The index is backed up to ``channels/backup.json`` before
        overwriting.
        """
        all_entries = self._load_all_entries()
        before = len(all_entries)

        if before == 0:
            return UpdateChannelsResult(before=0, after=0, removed=0)

        # Test all streams in parallel with hard timeout per channel
        # We use wait() with a deadline so stuck threads don't hang forever
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_map: dict[Future, int] = {
                executor.submit(
                    self._test_stream_url, e.stream_url, timeout, e.extra_headers
                ): i
                for i, e in enumerate(all_entries)
            }

            deadline = time.monotonic() + timeout + 5.0  # 5s grace beyond per-request timeout
            while future_map:
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    # Hard deadline hit — cancel everything still pending
                    for f in future_map:
                        f.cancel()
                    break

                done, not_done = wait(
                    future_map.keys(),
                    timeout=min(remaining_time, 2.0),
                )
                for future in done:
                    idx = future_map.pop(future)
                    try:
                        all_entries[idx].working = future.result(timeout=0.1)
                    except Exception:
                        all_entries[idx].working = False

                # Mark any still-pending as not working (will be cancelled on next loop
                # or when deadline hits)
                if not_done and remaining_time <= 2.0:
                    for f in not_done:
                        f.cancel()
                    done, _ = wait(not_done, timeout=0.5)
                    for future in done:
                        idx = future_map.pop(future)
                        try:
                            all_entries[idx].working = future.result(timeout=0.1)
                        except Exception:
                            all_entries[idx].working = False
                    # Anything left gets marked not working but already popped
                    for f in list(future_map.keys()):
                        idx = future_map.pop(f)
                        f.cancel()
                        all_entries[idx].working = False

        # Keep only working channels
        working = [e for e in all_entries if e.working]
        after = len(working)
        removed = before - after

        # Backup before overwriting
        backup_path = self._backup_current_index()

        self._write_index(working)

        return UpdateChannelsResult(
            before=before,
            after=after,
            removed=removed,
            backup_path=str(backup_path) if backup_path else None,
        )

    # ------------------------------------------------------------------
    # 3. Restore Channels — from backup
    # ------------------------------------------------------------------

    def restore_channels(self) -> int:
        """Restore ``channels/index.json`` from ``channels/backup.json``.

        Returns the number of channels restored, or 0 if no backup exists.
        """
        if not self._backup_path.exists():
            return 0

        try:
            data = json.loads(self._backup_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0

        if "channels" in data:
            entries = [ChannelIndexEntry.from_dict(ch) for ch in data["channels"]]
        else:
            return 0

        self._write_index(entries)
        self._sync_to_frontend()
        return len(entries)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_working(self) -> list[ChannelIndexEntry]:
        """List only working channels."""
        return [e for e in self._load_all_entries() if e.working]

    def list_all(self) -> list[ChannelIndexEntry]:
        """List all channels including non-working."""
        return self._load_all_entries()

    # ------------------------------------------------------------------
    # Stream testing
    # ------------------------------------------------------------------

    @staticmethod
    def _test_stream_url(
        url: str,
        timeout: float = 8.0,
        extra_headers: dict[str, str] | None = None,
    ) -> bool:
        """Probe a stream URL — returns True if reachable AND content is valid.

        For HLS streams (.m3u8) this actually downloads the first bytes and
        verifies the content starts with #EXTM3U — not just the HTTP status.

        Uses ``urllib.request`` which respects ``socket.setdefaulttimeout()``
        reliably — unlike httpx which can hang under high concurrency.
        """
        headers: dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if extra_headers:
            headers.update(extra_headers)
        try:
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            try:
                req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if not (200 <= resp.status < 400):
                        return False
                    # For HLS streams, validate actual playlist content
                    if url.endswith(".m3u8") or "/playlist" in url:
                        body = resp.read(500).decode("utf-8", errors="replace")
                        if not body.startswith("#EXTM3U"):
                            return False
                    return True
            except urllib.error.HTTPError as e:
                # HTTPError still has status code info (e.g. 403, 404)
                return False
            except (urllib.error.URLError, OSError):
                return False
            finally:
                socket.setdefaulttimeout(old_timeout)
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
        pending_extra_headers: dict[str, str] = {}  # from preceding #EXTVLCOPT lines

        for line in lines:
            if line.startswith("#EXTVLCOPT"):
                # Parse http-referrer and http-user-agent directives
                vlcopt = line[len("#EXTVLCOPT:"):].strip()
                if vlcopt.startswith("http-referrer="):
                    pending_extra_headers["Referer"] = vlcopt[len("http-referrer="):]
                elif vlcopt.startswith("http-user-agent="):
                    pending_extra_headers["User-Agent"] = vlcopt[len("http-user-agent="):]
                continue
            if line.startswith("#EXTHTTP"):
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

            # Build extra headers from both #EXTINF attrs and #EXTVLCOPT lines
            extra_headers: dict[str, str] = {}
            http_ref = pending_attrs.get("http-referrer")
            if http_ref and http_ref != "None":
                extra_headers["Referer"] = http_ref
            http_ua = pending_attrs.get("http-user-agent")
            if http_ua and http_ua != "None":
                extra_headers["User-Agent"] = http_ua
            # #EXTVLCOPT values override #EXTINF attributes
            extra_headers.update(pending_extra_headers)

            entries.append(
                ChannelIndexEntry(
                    tvg_id=tvg_id,
                    name=pending_attrs.get("name") or self._name_from_url(line),
                    stream_url=line,
                    group_title=pending_attrs.get("group-title") or "Ungrouped",
                    logo_url=pending_attrs.get("tvg-logo"),
                    source_playlist=playlist_name,
                    source_playlist_id=playlist_id,
                    extra_headers=extra_headers,
                )
            )
            pending_attrs = None
            pending_extra_headers = {}

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
        """Write ``index.json`` + ``manifest.json``, then sync to frontend."""
        self.channels_dir.mkdir(parents=True, exist_ok=True)
        self._frontend_dir.mkdir(parents=True, exist_ok=True)

        # index.json
        index_data = {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "channels": [e.to_dict() for e in entries],
        }
        self._index_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # manifest.json
        manifest_data = {
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
        }
        self._manifest_path.write_text(
            json.dumps(manifest_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Sync to frontend
        self._sync_to_frontend()

    def _sync_to_frontend(self) -> None:
        """Copy index + manifest to frontend/public/channels/."""
        for filename in ("index.json", "manifest.json"):
            source = self.channels_dir / filename
            if source.exists():
                target = self._frontend_dir / filename
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    def _backup_current_index(self) -> Path | None:
        """Copy current index.json → backup.json.

        Returns the backup path, or None if nothing to back up.
        """
        if not self._index_path.exists():
            return None
        shutil.copy2(self._index_path, self._backup_path)
        return self._backup_path

    def _load_all_entries(self) -> list[ChannelIndexEntry]:
        """Load all entries from the aggregate index.json."""
        if not self._index_path.exists():
            return []
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
            return [ChannelIndexEntry.from_dict(ch) for ch in data.get("channels", [])]
        except (OSError, json.JSONDecodeError, KeyError):
            return []
