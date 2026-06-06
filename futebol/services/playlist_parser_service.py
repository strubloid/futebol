import re

from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.channel import Channel
from futebol.domain.models.playlist import Playlist
from futebol.domain.models.stream import Stream


class PlaylistParserService:
    _attr_pattern = re.compile(r'([\w-]+)="([^"]*)"')

    def parse(
        self,
        content: str,
        *,
        source_url: str | None = None,
        source_type: SourceType = SourceType.USER_PROVIDED,
    ) -> Playlist:
        channels: list[Channel] = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        pending: dict[str, str | None] | None = None
        for line in lines:
            if line.startswith("#EXTINF"):
                pending = self._parse_extinf(line)
                continue
            if line.startswith("#"):
                continue
            if pending is not None:
                channels.append(
                    Channel(
                        name=pending.get("name") or line,
                        tvg_id=pending.get("tvg-id"),
                        tvg_name=pending.get("tvg-name"),
                        tvg_logo=pending.get("tvg-logo"),
                        group_title=pending.get("group-title"),
                        stream=Stream(url=line),
                        source_url=source_url,
                        source_type=source_type,
                    )
                )
                pending = None
        return Playlist(channels=channels, source_url=source_url)

    def _parse_extinf(self, line: str) -> dict[str, str | None]:
        attributes: dict[str, str | None] = {
            key: value for key, value in self._attr_pattern.findall(line)
        }
        attributes["name"] = line.rsplit(",", maxsplit=1)[-1].strip() if "," in line else None
        return attributes
