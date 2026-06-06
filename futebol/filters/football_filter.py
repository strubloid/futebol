from futebol.domain.models.channel import Channel
from futebol.filters.base_filter import BaseFilter
from futebol.services.football_detector_service import FootballDetectorService


class FootballFilter(BaseFilter):
    def __init__(self, detector: FootballDetectorService | None = None) -> None:
        self._detector = detector or FootballDetectorService()

    def apply(self, channels: list[Channel]) -> list[Channel]:
        return [
            channel
            for channel in channels
            if self._detector.is_football_related(channel.searchable_text())
        ]
