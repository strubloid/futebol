import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from futebol.config.settings import Settings
from futebol.domain.enums.source_type import SourceType
from futebol.domain.enums.stream_status import StreamStatus
from futebol.domain.models.channel import Channel
from futebol.domain.models.stream import Stream
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
from futebol.services.channel_index_service import ChannelIndexEntry, ChannelIndexService
from futebol.services.channel_sync_service import ChannelSyncService, CleanSummary, SyncSummary
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

    # ------------------------------------------------------------------
    # Channel index — single-source-of-truth channels/index.json
    # ------------------------------------------------------------------

    def channels_load_and_test(self) -> tuple[int, int]:
        """Parse M3U files from ``m3u/``, test every stream, write index.

        This is the **single** sync method — always tests streams,
        never preserves stale ``working`` flags.

        After writing ``channels/index.json`` + ``channels/manifest.json``,
        automatically syncs to the frontend public directory.

        Returns:
            ``(total_entries, working_entries)``
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        m3u_dir = project_root / "m3u"
        channels_dir = project_root / "channels"
        service = ChannelIndexService(m3u_dir, channels_dir)

        total, working = service.load_and_test(
            concurrency=20,
            timeout=self.settings.stream_timeout_seconds,
        )

        # Sync aggregate files to frontend
        self._sync_index_to_frontend(project_root)
        return total, working

    def channel_set_working(self, tvg_id: str, working: bool) -> ChannelIndexEntry | None:
        """Toggle working status for a channel in the aggregate index."""
        project_root = Path(__file__).resolve().parent.parent.parent
        channels_dir = project_root / "channels"
        service = ChannelIndexService(project_root / "m3u", channels_dir)
        if not service.set_working(tvg_id, working):
            return None
        self._sync_index_to_frontend(project_root)
        return next(
            (e for e in service.list_all() if e.tvg_id == tvg_id),
            None,
        )

    def channel_list(self, all_flag: bool = False) -> list[ChannelIndexEntry]:
        """List indexed channels."""
        project_root = Path(__file__).resolve().parent.parent.parent
        channels_dir = project_root / "channels"
        service = ChannelIndexService(project_root / "m3u", channels_dir)
        return service.list_all() if all_flag else service.list_working()

    def channel_set_playlist(
        self, tvg_id: str, playlist_name: str, playlist_id: str | None = None
    ) -> ChannelIndexEntry | None:
        """Change the playlist assignment for a channel in the aggregate index."""
        entries = self._get_all_index_entries()
        found = None
        for entry in entries:
            if entry.tvg_id == tvg_id:
                entry.source_playlist = playlist_name
                entry.source_playlist_id = playlist_id or playlist_name
                found = entry
                break
        if found is None:
            return None
        self._write_index(entries)
        self._sync_index_to_frontend(Path(__file__).resolve().parent.parent.parent)
        return found

    # ------------------------------------------------------------------
    # Sync to app internal channels.json (for legacy pipeline compat)
    # ------------------------------------------------------------------

    def channels_sync_to_app(self) -> int:
        """Push the curated channels/ index into .futebol/channels.json.

        Converts each ChannelIndexEntry into a Channel domain object so the
        app's filter/validate/export pipeline uses the same curated data.
        Returns the number of channels written.
        """
        entries = self._get_all_index_entries()

        channels: list[Channel] = []
        for entry in entries:
            channels.append(
                Channel(
                    name=entry.name,
                    tvg_id=entry.tvg_id,
                    tvg_logo=entry.logo_url,
                    group_title=entry.group_title,
                    source_url="channels/index.json",
                    source_type=SourceType.USER_PROVIDED,
                    stream=Stream(url=entry.stream_url, status=StreamStatus.UNCHECKED),
                    include_in_playlist=entry.working,
                )
            )

        self._channel_repository.save(channels)
        return len(channels)

    def channels_update_sync(self) -> SyncSummary:
        """Backup and sync channels/ index into .futebol/channels.json."""
        project_root = Path(__file__).resolve().parent.parent.parent
        channels_dir = project_root / "channels"
        m3u_dir = project_root / "m3u"
        index_service = ChannelIndexService(m3u_dir, channels_dir)
        sync_service = ChannelSyncService(
            channel_index_service=index_service,
            channel_repository=self._channel_repository,
            settings=self.settings,
        )
        return sync_service.update_channels()

    def channels_restore(self) -> int:
        """Restore .futebol/channels.json from backup file."""
        project_root = Path(__file__).resolve().parent.parent.parent
        channels_dir = project_root / "channels"
        m3u_dir = project_root / "m3u"
        index_service = ChannelIndexService(m3u_dir, channels_dir)
        sync_service = ChannelSyncService(
            channel_index_service=index_service,
            channel_repository=self._channel_repository,
            settings=self.settings,
        )
        return sync_service.restore_channels()

    def channels_clean_broken(self) -> CleanSummary:
        """Remove all non-working channels from channels/index.json and channels.json.

        This removes broken entries from the aggregate index and from
        ``.futebol/channels.json``.  No individual per-channel files exist
        to delete.
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        channels_dir = project_root / "channels"
        m3u_dir = project_root / "m3u"
        index_service = ChannelIndexService(m3u_dir, channels_dir)
        sync_service = ChannelSyncService(
            channel_index_service=index_service,
            channel_repository=self._channel_repository,
            settings=self.settings,
        )
        result = sync_service.clean_broken()
        self._sync_index_to_frontend(project_root)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_index_to_frontend(self, project_root: Path) -> None:
        """Copy ``channels/index.json`` and ``channels/manifest.json`` to frontend.

        Individual per-channel files are no longer created, so this only
        copies the aggregate files.
        """
        channels_dir = project_root / "channels"
        frontend_public = project_root / "frontend" / "public" / "channels"
        frontend_public.mkdir(parents=True, exist_ok=True)

        for filename in ("index.json", "manifest.json"):
            source = channels_dir / filename
            if source.exists():
                target = frontend_public / filename
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    def _get_all_index_entries(self) -> list[ChannelIndexEntry]:
        """Load all entries from the aggregate index."""
        project_root = Path(__file__).resolve().parent.parent.parent
        channels_dir = project_root / "channels"
        service = ChannelIndexService(project_root / "m3u", channels_dir)
        return service.list_all()

    def _write_index(self, entries: list[ChannelIndexEntry]) -> None:
        """Write entries directly to channels/index.json + manifest.json."""
        project_root = Path(__file__).resolve().parent.parent.parent
        channels_dir = project_root / "channels"
        service = ChannelIndexService(project_root / "m3u", channels_dir)
        service._write_index(entries)

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
