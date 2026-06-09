"""Scrapes TV programme data from public web sources and writes a
static JSON guide file for the Angular frontend.

Data sources (tried in order per channel):
  1. iptv-org JSON guides  — https://iptv-org.github.io/api/guides/{id}.json
  2. Web scraping          — meuguia.tv, tvguide.com-style pages
  3. XMLTV fallback        — generic public XMLTV files

Output: frontend/public/epg/guide.json
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from futebol.config.settings import Settings
from futebol.infrastructure.http.http_client import HttpClient, HttpResponse

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class EpgProgram:
    id: str = ""
    channel: str = ""          # xmltv_id matching the channel's tvgId
    title: str = ""
    start: str = ""             # ISO 8601
    stop: str = ""              # ISO 8601
    description: str = ""
    category: str = ""
    image: str = ""
    isLive: bool = False
    isNew: bool = False


@dataclass
class EpgChannel:
    id: str          # xmltv_id
    name: str = ""
    logo: str = ""


@dataclass
class EpgGuide:
    generated: str = ""                      # ISO timestamp
    channels: list[EpgChannel] = field(default_factory=list)
    programs: list[EpgProgram] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated": self.generated,
            "channels": [asdict(c) for c in self.channels],
            "programs": [asdict(p) for p in self.programs],
        }


# ---------------------------------------------------------------------------
# Source adapters
# ---------------------------------------------------------------------------

IPTV_ORG_GUIDES_BASE = "https://iptv-org.github.io/api/guides"
IPTV_ORG_CHANNELS_URL = "https://iptv-org.github.io/api/channels.json"


class IptvOrgAdapter:
    """Fetches channel metadata + programme data from iptv-org JSON API."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._channels_cache: list[dict] | None = None

    def fetch_channels(self) -> list[dict]:
        if self._channels_cache is None:
            resp = self._http.get_text(IPTV_ORG_CHANNELS_URL)
            self._channels_cache = json.loads(resp.text)
        return self._channels_cache

    def fetch_guide(self, xmltv_id: str) -> dict | None:
        url = f"{IPTV_ORG_GUIDES_BASE}/{xmltv_id}.json"
        resp = self._http.get_text(url)
        if resp.status_code == 200:
            return json.loads(resp.text)
        return None

    def find_channel_by_tvg_id(self, tvg_id: str) -> dict | None:
        channels = self.fetch_channels()
        for ch in channels:
            if ch.get("xmltv_id") == tvg_id:
                return ch
        return None

    def find_channel_by_name(self, name: str) -> dict | None:
        channels = self.fetch_channels()
        name_lower = name.lower()
        for ch in channels:
            if ch.get("name", "").lower() == name_lower:
                return ch
        return None


class MeuguiaScraper:
    """Scrapes programme data from meuguia.tv HTML pages."""

    BASE_URL = "https://meuguia.tv/guia"

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def fetch_programs(self, channel_slug: str) -> list[EpgProgram]:
        """channel_slug: URL-friendly channel name (e.g. 'Globo', 'SBT')."""
        url = f"{self.BASE_URL}/{channel_slug}"
        resp = self._http.get_text(url)
        if resp.status_code != 200:
            return []
        return self._parse_html(resp.text, channel_slug)

    def _parse_html(self, html: str, channel_id: str) -> list[EpgProgram]:
        programs: list[EpgProgram] = []
        # Look for JSON-LD structured data first
        scripts = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        for script in scripts:
            try:
                data = json.loads(script)
                if isinstance(data, list):
                    data = data[0] if data else {}
                if data.get("@type") == "TVProgram":
                    programs.append(self._ld_to_program(data, channel_id))
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: parse time + title patterns from HTML
        if not programs:
            programs = self._parse_html_timing(html, channel_id)

        return programs

    def _ld_to_program(self, ld: dict, channel_id: str) -> EpgProgram:
        start = datetime.fromisoformat(ld["startDate"]) if "startDate" in ld else datetime.now()
        end = datetime.fromisoformat(ld["endDate"]) if "endDate" in ld else start + timedelta(hours=1)
        now = datetime.now(timezone.utc)
        return EpgProgram(
            id=f"{channel_id}-{start.isoformat()}",
            channel=channel_id,
            title=ld.get("name", ""),
            description=ld.get("description", ""),
            start=start.isoformat(),
            stop=end.isoformat(),
            isLive=(start <= now <= end),
        )

    def _parse_html_timing(self, html: str, channel_id: str) -> list[EpgProgram]:
        """Fallback: extract time/title pairs from plain HTML."""
        programs: list[EpgProgram] = []
        # Match patterns like "14:30" followed by a title element
        pattern = re.compile(
            r'<time[^>]*datetime=["\']([^"\']+)["\'][^>]*>.*?</time>'
            r'|<span[^>]*class=["\'][^"\']*hora[^"\']*["\'][^>]*>(\d{2}:\d{2})</span>'
            r'.*?<[^>]*(?:title|name)=["\']([^"\']+)["\']',
            re.DOTALL | re.IGNORECASE,
        )
        matches = re.findall(pattern, html)
        for m in matches:
            time_str = m[0] or m[1]
            title = m[2].strip()
            if title and len(title) > 1:
                try:
                    # Try to parse as full datetime first
                    dt = datetime.fromisoformat(time_str)
                except ValueError:
                    # Treat as just a time — use today's date
                    parts = time_str.split(":")
                    dt = datetime.now().replace(
                        hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0
                    )
                programs.append(
                    EpgProgram(
                        id=f"{channel_id}-{dt.isoformat()}",
                        channel=channel_id,
                        title=title,
                        start=dt.isoformat(),
                        stop=(dt + timedelta(hours=1)).isoformat(),
                    )
                )
        return programs


# ---------------------------------------------------------------------------
# Main scraper service
# ---------------------------------------------------------------------------

# Brazilian channel slugs for meuguia.tv
_BR_SLUGS: dict[str, str] = {
    "globo": "Globo",
    "sbt": "SBT",
    "record": "Record-TV",
    "band": "Band",
    "tv-cultura": "TV-Cultura",
    "redegloobas": "Rede-Bahia",
    "sptv": "SPTV",
    "cultura": "Cultura",
    "tv-brasil": "TV-Brasil",
}


class EpgScraperService:
    """Aggregates EPG data from multiple sources and writes guide.json."""

    def __init__(
        self,
        channels_dir: Path,
        output_dir: Path,
        settings: Settings | None = None,
    ) -> None:
        self._channels_dir = channels_dir
        self._output_dir = output_dir
        self._settings = settings or Settings.from_env()
        self._http = HttpClient(timeout_seconds=10.0)
        self._iptv = IptvOrgAdapter(self._http)
        self._meuguia = MeuguiaScraper(self._http)

    # ------------------------------------------------------------------ Public API

    def scrape_all(
        self,
        tvg_ids: list[str],
        channel_names: list[str],
        concurrency: int = 5,
        quiet: bool = False,
    ) -> EpgGuide:
        """Scrape EPG data for all given channels.

        Args:
            tvg_ids: List of tvg-id values from M3U files (e.g. "RedeGlobo.br")
            channel_names: Display names aligned with tvg_ids
            concurrency: Number of parallel HTTP requests
            quiet: Suppress progress output

        Returns:
            EpgGuide with channels + programmes found
        """
        guide = EpgGuide(
            generated=datetime.now(timezone.utc).isoformat(),
        )

        # Deduplicate by tvg_id
        seen: dict[str, tuple[str, str]] = {}
        for tvg_id, name in zip(tvg_ids, channel_names):
            key = self._normalize_id(tvg_id)
            if key not in seen:
                seen[key] = (tvg_id, name)

        results: list[tuple[str, str, str | None, str | None]] = []

        for normalized_id, (tvg_id, name) in seen.items():
            logo = self._fetch_logo(tvg_id, name)
            guide.channels.append(EpgChannel(id=tvg_id, name=name, logo=logo))

            programs = self._scrape_channel(normalized_id, tvg_id, name)
            for prog in programs:
                prog.channel = tvg_id
                guide.programs.append(prog)

            results.append((tvg_id, name, logo, str(len(programs))))

        return guide

    def write_guide(self, guide: EpgGuide) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._output_dir / "guide.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(guide.to_dict(), f, ensure_ascii=False, indent=2)
        return out_path

    # ------------------------------------------------------------------ Internals

    def _scrape_channel(
        self,
        normalized_id: str,
        tvg_id: str,
        name: str,
    ) -> list[EpgProgram]:
        """Try sources in order until data is found."""

        # 1. Try iptv-org JSON guide
        programs = self._scrape_iptv_org(tvg_id)
        if programs:
            return programs

        # 2. Try meuguia.tv via slug mapping
        slug = self._slug_from_name(name)
        if slug:
            programs = self._meuguia.fetch_programs(slug)
            if programs:
                return programs

        return []

    def _scrape_iptv_org(self, tvg_id: str) -> list[EpgProgram]:
        data = self._iptv.fetch_guide(tvg_id)
        if not data:
            return []
        return self._parse_iptv_guide(data, tvg_id)

    def _parse_iptv_guide(self, data: dict, tvg_id: str) -> list[EpgProgram]:
        programs: list[EpgProgram] = []
        now = datetime.now(timezone.utc)

        # iptv-org JSON guide format
        for item in data.get("programs", []):
            titles = item.get("titles", [])
            title = titles[0]["value"] if titles else "Unknown"
            descs = item.get("descriptions", [])
            desc = descs[0]["value"] if descs else ""
            imgs = item.get("images", [])
            image = imgs[0] if imgs else ""

            start_ms = item.get("start")
            stop_ms = item.get("stop")
            if not start_ms or not stop_ms:
                continue

            start = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
            stop = datetime.fromtimestamp(stop_ms / 1000, tz=timezone.utc)
            is_live = start <= now <= stop
            is_new = item.get("new", False)

            programs.append(
                EpgProgram(
                    id=f"{tvg_id}-{start_ms}",
                    channel=tvg_id,
                    title=title,
                    start=start.isoformat(),
                    stop=stop.isoformat(),
                    description=desc,
                    image=image,
                    isLive=is_live,
                    isNew=is_new,
                )
            )

        return programs

    def _fetch_logo(self, tvg_id: str, name: str) -> str:
        """Try to get channel logo from iptv-org channels list."""
        ch = self._iptv.find_channel_by_tvg_id(tvg_id)
        if ch:
            return ch.get("logo", "")
        # Fall back to name-based lookup
        ch = self._iptv.find_channel_by_name(name)
        if ch:
            return ch.get("logo", "")
        return ""

    @staticmethod
    def _normalize_id(tvg_id: str) -> str:
        """Strip feed suffix from tvg-id (e.g. 'RedeGlobo.br@SD' -> 'RedeGlobo.br')."""
        return tvg_id.split("@")[0].strip()

    @staticmethod
    def _slug_from_name(name: str) -> str:
        """Map a channel display name to a meuguia.tv URL slug."""
        name_lower = name.lower()
        for key, slug in _BR_SLUGS.items():
            if key in name_lower or slug.lower() in name_lower:
                return slug
        # Generic slugification
        slug = re.sub(r"[^a-z0-9]+", "-", name_lower).strip("-")
        return slug[:30]