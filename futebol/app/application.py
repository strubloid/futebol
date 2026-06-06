import shutil
from dataclasses import dataclass
from pathlib import Path

from futebol.config.settings import Settings
from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.channel import Channel
from futebol.domain.models.search_result import SearchResult
from futebol.filters.base_filter import BaseFilter
from futebol.filters.brazilian_portuguese_filter import BrazilianPortugueseFilter
from futebol.filters.football_filter import FootballFilter
from futebol.filters.worldcup_filter import WorldCupFilter
from futebol.infrastructure.http.http_client import TextHttpClient
from futebol.output.json_exporter import JsonExporter
from futebol.output.m3u_exporter import M3uExporter
from futebol.repositories.channel_repository import ChannelRepository
from futebol.repositories.source_repository import SourceRepository
from futebol.services.channel_filter_service import ChannelFilterService
from futebol.services.playlist_download_service import (
    PlaylistDownloadService,
    PlaylistDownloadSummary,
)
from futebol.services.playlist_loader_service import PlaylistLoaderService
from futebol.services.playlist_parser_service import PlaylistParserService
from futebol.services.stream_validator_service import StreamValidatorService
from futebol.validators.legal_source_validator import LegalSourceValidator
from futebol.validators.m3u_format_validator import M3uFormatValidator


@dataclass(frozen=True)
class LocalPlaylistSearchSummary:
    found: int
    copied: int
    added: int


class Application:
    def __init__(
        self,
        settings: Settings | None = None,
        loader: PlaylistLoaderService | None = None,
        parser: PlaylistParserService | None = None,
        stream_validator: StreamValidatorService | None = None,
        http_client: TextHttpClient | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self._source_repository = SourceRepository(self.settings.data_dir / "sources.json")
        self._channel_repository = ChannelRepository(self.settings.data_dir / "channels.json")
        self._loader = loader or PlaylistLoaderService(http_client=http_client)
        self._parser = parser or PlaylistParserService()
        self._stream_validator = stream_validator or StreamValidatorService()
        self._download_service = PlaylistDownloadService(http_client=http_client)
        self._m3u_validator = M3uFormatValidator()
        self._legal_validator = LegalSourceValidator()
        self._filter_service = ChannelFilterService()

    def add_source_url(self, url: str) -> None:
        source_type = self._legal_validator.classify_url(url, SourceType.USER_PROVIDED)
        self._source_repository.add(
            SearchResult(
                title=url,
                url=url,
                source_type=source_type,
                legitimacy_note="User-provided playlist URL",
            )
        )

    def add_source_file(self, path: Path) -> None:
        self._source_repository.add(
            SearchResult(
                title=path.name,
                url=str(path),
                source_type=SourceType.USER_PROVIDED,
                legitimacy_note="User-provided local playlist file",
            )
        )

    def add_source_folder(self, path: Path) -> int:
        before = {source.url for source in self._source_repository.list()}
        self._add_source_files(self._playlist_files(path))
        after = {source.url for source in self._source_repository.list()}
        return len(after - before)

    def download_source_list(self, url_list: Path, output_dir: Path) -> PlaylistDownloadSummary:
        summary = self._download_service.download_from_list(url_list, output_dir)
        self._add_source_files(summary.downloaded_paths)
        return summary

    def download_source_url(self, url: str, output_dir: Path) -> PlaylistDownloadSummary:
        summary = self._download_service.download_from_urls([url], output_dir)
        self._add_source_files(summary.downloaded_paths)
        return summary

    def download_public_playlists(self, output_dir: Path) -> PlaylistDownloadSummary:
        public_playlist_urls = [
            "https://iptv-org.github.io/iptv/categories/sports.m3u",
            "https://iptv-org.github.io/iptv/countries/br.m3u",
        ]
        summary = self._download_service.download_from_urls(
            public_playlist_urls, output_dir
        )
        self._add_source_files(summary.downloaded_paths)
        return summary

    def search_and_add_local_playlists(
        self, search_root: Path, destination_dir: Path
    ) -> LocalPlaylistSearchSummary:
        found_files = [
            playlist_path
            for playlist_path in self._playlist_files(search_root)
            if not self._is_inside(playlist_path, destination_dir)
        ]
        destination_dir.mkdir(parents=True, exist_ok=True)
        copied_paths: list[Path] = []
        for playlist_path in found_files:
            target = self._unique_destination(destination_dir, playlist_path.name)
            shutil.copy2(playlist_path, target)
            copied_paths.append(target)
        before = {source.url for source in self._source_repository.list()}
        self._add_source_files(copied_paths)
        after = {source.url for source in self._source_repository.list()}
        return LocalPlaylistSearchSummary(
            found=len(found_files), copied=len(copied_paths), added=len(after - before)
        )

    def scan(self) -> list[Channel]:
        channels: list[Channel] = []
        for source in self._source_repository.list():
            if source.source_type == SourceType.BLOCKED_REJECTED:
                continue
            content = self._loader.load(source.url)
            if not self._m3u_validator.is_valid(content):
                continue
            playlist = self._parser.parse(
                content, source_url=source.url, source_type=source.source_type
            )
            channels.extend(playlist.channels)
        marked = self._filter_service.mark_playlist_inclusion(
            channels, allow_unknown=self.settings.allow_unknown_sources
        )
        self._channel_repository.save(marked)
        return marked

    def filter_channels(
        self, category: str = "football", language: str | None = None
    ) -> list[Channel]:
        filters: list[BaseFilter] = []
        if category == "football":
            filters.append(FootballFilter())
        if category in {"worldcup", "world-cup"}:
            filters.append(WorldCupFilter())
        if language in {"pt-BR", "pt_BR", "br", "portuguese"}:
            filters.append(BrazilianPortugueseFilter())
        channels = self._filter_service.apply_filters(self._channel_repository.list(), filters)
        marked = self._filter_service.mark_playlist_inclusion(
            channels, allow_unknown=self.settings.allow_unknown_sources
        )
        self._channel_repository.save(marked)
        return marked

    def validate_streams(self) -> list[Channel]:
        validated = [
            channel.with_stream(self._stream_validator.validate(channel.stream))
            for channel in self._channel_repository.list()
        ]
        marked = self._filter_service.mark_playlist_inclusion(
            validated, allow_unknown=self.settings.allow_unknown_sources
        )
        self._channel_repository.save(marked)
        return marked

    def export(self, export_format: str, output: Path) -> None:
        channels = self._channel_repository.list()
        text = (
            M3uExporter().export(channels)
            if export_format == "m3u"
            else JsonExporter().export(channels)
        )
        output.write_text(text, encoding="utf-8")

    def channels(self) -> list[Channel]:
        return self._channel_repository.list()

    def _playlist_files(self, path: Path) -> list[Path]:
        if not path.exists() or not path.is_dir():
            return []
        return sorted(
            playlist_path
            for playlist_path in path.rglob("*")
            if playlist_path.is_file()
            and playlist_path.suffix.lower() in {".m3u", ".m3u8"}
        )

    def _add_source_files(self, playlist_paths: tuple[Path, ...] | list[Path]) -> None:
        for playlist_path in playlist_paths:
            if self._is_valid_playlist_file(playlist_path):
                self.add_source_file(playlist_path)

    def _is_valid_playlist_file(self, playlist_path: Path) -> bool:
        try:
            content = playlist_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
        return self._m3u_validator.is_valid(content)

    def _is_inside(self, path: Path, folder: Path) -> bool:
        try:
            path.resolve().relative_to(folder.resolve())
        except ValueError:
            return False
        return True

    def _unique_destination(self, folder: Path, filename: str) -> Path:
        target = folder / filename
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        index = 2
        while True:
            candidate = folder / f"{stem}-{index}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1
