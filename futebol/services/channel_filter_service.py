from futebol.domain.enums.source_type import SourceType
from futebol.domain.enums.stream_status import StreamStatus
from futebol.domain.models.channel import Channel
from futebol.filters.base_filter import BaseFilter


class ChannelFilterService:
    def apply_filters(self, channels: list[Channel], filters: list[BaseFilter]) -> list[Channel]:
        filtered = channels
        for channel_filter in filters:
            filtered = channel_filter.apply(filtered)
        return filtered

    def mark_playlist_inclusion(
        self, channels: list[Channel], *, allow_unknown: bool = False
    ) -> list[Channel]:
        marked: list[Channel] = []
        for channel in channels:
            if channel.source_type == SourceType.BLOCKED_REJECTED:
                marked.append(channel.with_include_status(False, "blocked or rejected source"))
            elif channel.source_type == SourceType.UNKNOWN and not allow_unknown:
                marked.append(channel.with_include_status(False, "unknown source legitimacy"))
            elif channel.stream.status in {StreamStatus.BROKEN, StreamStatus.UNREACHABLE}:
                marked.append(channel.with_include_status(False, "stream is unavailable"))
            else:
                marked.append(channel.with_include_status(True))
        return marked
