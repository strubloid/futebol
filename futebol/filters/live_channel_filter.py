from futebol.domain.enums.stream_status import StreamStatus
from futebol.domain.models.channel import Channel
from futebol.filters.base_filter import BaseFilter


class LiveChannelFilter(BaseFilter):
    def apply(self, channels: list[Channel]) -> list[Channel]:
        return [
            channel
            for channel in channels
            if channel.stream.status in {StreamStatus.ALIVE, StreamStatus.UNCHECKED}
        ]
