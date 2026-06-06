from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from futebol.domain.enums.source_type import SourceType
from futebol.infrastructure.http.http_client import HttpClient, TextHttpClient
from futebol.validators.legal_source_validator import LegalSourceValidator
from futebol.validators.m3u_format_validator import M3uFormatValidator
from futebol.validators.url_validator import UrlValidator


@dataclass(frozen=True, slots=True)
class PlaylistDownloadSummary:
    downloaded: int = 0
    skipped: int = 0
    downloaded_paths: tuple[Path, ...] = ()


class PlaylistDownloadService:
    def __init__(
        self,
        http_client: TextHttpClient | None = None,
        url_validator: UrlValidator | None = None,
        m3u_validator: M3uFormatValidator | None = None,
        legal_validator: LegalSourceValidator | None = None,
    ) -> None:
        self._http_client = http_client or HttpClient()
        self._url_validator = url_validator or UrlValidator()
        self._m3u_validator = m3u_validator or M3uFormatValidator()
        self._legal_validator = legal_validator or LegalSourceValidator()

    def download_from_list(self, url_list: Path, output_dir: Path) -> PlaylistDownloadSummary:
        return self.download_from_urls(self._read_urls(url_list), output_dir)

    def download_from_urls(
        self, urls: list[str], output_dir: Path
    ) -> PlaylistDownloadSummary:
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        skipped = 0
        downloaded_paths: list[Path] = []
        for url in urls:
            if not self._url_validator.is_valid(url):
                skipped += 1
                continue
            if self._legal_validator.classify_url(url) == SourceType.BLOCKED_REJECTED:
                skipped += 1
                continue
            response = self._http_client.get_text(url)
            if response.status_code >= 400 or not self._m3u_validator.is_valid(response.text):
                skipped += 1
                continue
            output_path = self._unique_output_path(output_dir, url)
            output_path.write_text(response.text, encoding="utf-8")
            downloaded_paths.append(output_path)
            downloaded += 1
        return PlaylistDownloadSummary(
            downloaded=downloaded,
            skipped=skipped,
            downloaded_paths=tuple(downloaded_paths),
        )

    def _read_urls(self, url_list: Path) -> list[str]:
        urls: list[str] = []
        for raw_line in url_list.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or not self._url_validator.is_valid(line):
                continue
            urls.append(line)
        return urls

    def _unique_output_path(self, output_dir: Path, url: str) -> Path:
        parsed_path = urlparse(url).path
        name = Path(parsed_path).name or "playlist.m3u"
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", name)
        if not safe_name.endswith((".m3u", ".m3u8")):
            safe_name = f"{safe_name}.m3u"
        candidate = output_dir / safe_name
        if not candidate.exists():
            return candidate
        stem = candidate.stem
        suffix = candidate.suffix
        index = 2
        while True:
            indexed = output_dir / f"{stem}-{index}{suffix}"
            if not indexed.exists():
                return indexed
            index += 1
