from pathlib import Path

from futebol.config.settings import Settings
from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.channel import Channel
from futebol.domain.models.search_result import SearchResult
from futebol.filters.base_filter import BaseFilter
from futebol.filters.brazilian_portuguese_filter import BrazilianPortugueseFilter
from futebol.filters.football_filter import FootballFilter
from futebol.filters.worldcup_filter import WorldCupFilter
from futebol.output.json_exporter import JsonExporter
from futebol.output.m3u_exporter import M3uExporter
from futebol.repositories.channel_repository import ChannelRepository
from futebol.repositories.source_repository import SourceRepository
from futebol.services.channel_filter_service import ChannelFilterService
from futebol.services.playlist_loader_service import PlaylistLoaderService
from futebol.services.playlist_parser_service import PlaylistParserService
from futebol.services.stream_validator_service import StreamValidatorService
from futebol.validators.legal_source_validator import LegalSourceValidator
from futebol.validators.m3u_format_validator import M3uFormatValidator


class Application:
    def __init__(
        self,
        settings: Settings | None = None,
        loader: PlaylistLoaderService | None = None,
        parser: PlaylistParserService | None = None,
        stream_validator: StreamValidatorService | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self._source_repository = SourceRepository(self.settings.data_dir / "sources.json")
        self._channel_repository = ChannelRepository(self.settings.data_dir / "channels.json")
        self._loader = loader or PlaylistLoaderService()
        self._parser = parser or PlaylistParserService()
        self._stream_validator = stream_validator or StreamValidatorService()
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
