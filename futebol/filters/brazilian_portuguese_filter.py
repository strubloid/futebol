from futebol.domain.models.channel import Channel
from futebol.filters.base_filter import BaseFilter
from futebol.services.football_detector_service import FootballDetectorService


class BrazilianPortugueseFilter(BaseFilter):
    TERMS: tuple[str, ...] = (
        "pt-br",
        "portuguese",
        "portugues",
        "português",
        "brasil",
        "brazil",
        "globo",
        "ge",
        "cazetv",
        "cazétv",
        "sportv",
    )

    def __init__(self) -> None:
        self._normalizer = FootballDetectorService()

    def apply(self, channels: list[Channel]) -> list[Channel]:
        return [channel for channel in channels if self.matches(channel)]

    def matches(self, channel: Channel) -> bool:
        text = self._normalizer.normalize(channel.searchable_text())
        return any(self._normalizer.normalize(term) in text for term in self.TERMS)
