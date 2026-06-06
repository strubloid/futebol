from __future__ import annotations

from dataclasses import dataclass, field, replace

from futebol.domain.enums.channel_category import ChannelCategory
from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.stream import Stream


@dataclass(frozen=True, slots=True)
class Channel:
    name: str
    stream: Stream
    tvg_id: str | None = None
    tvg_name: str | None = None
    tvg_logo: str | None = None
    group_title: str | None = None
    source_url: str | None = None
    source_type: SourceType = SourceType.UNKNOWN
    categories: tuple[ChannelCategory, ...] = field(default_factory=tuple)
    language: str | None = None
    region: str | None = None
    include_in_playlist: bool = False
    rejection_reason: str | None = None

    def with_stream(self, stream: Stream) -> Channel:
        return replace(self, stream=stream)

    def with_include_status(self, include: bool, reason: str | None = None) -> Channel:
        return replace(self, include_in_playlist=include, rejection_reason=reason)

    def searchable_text(self) -> str:
        fields = [
            self.name,
            self.tvg_name or "",
            self.group_title or "",
            self.language or "",
            self.region or "",
        ]
        return " ".join(fields).lower()
