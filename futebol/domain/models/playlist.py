from dataclasses import dataclass, field

from futebol.domain.models.channel import Channel


@dataclass(frozen=True, slots=True)
class Playlist:
    channels: list[Channel] = field(default_factory=list)
    source_url: str | None = None
    name: str = "legal IPTV playlist"
