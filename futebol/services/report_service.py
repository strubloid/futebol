from collections import Counter
from dataclasses import dataclass

from futebol.domain.models.channel import Channel


@dataclass(frozen=True, slots=True)
class ReportSummary:
    total: int
    included: int
    rejected: int
    by_source_type: dict[str, int]
    by_status: dict[str, int]


class ReportService:
    def summarize(self, channels: list[Channel]) -> ReportSummary:
        return ReportSummary(
            total=len(channels),
            included=sum(1 for channel in channels if channel.include_in_playlist),
            rejected=sum(1 for channel in channels if not channel.include_in_playlist),
            by_source_type=dict(Counter(str(channel.source_type.value) for channel in channels)),
            by_status=dict(Counter(str(channel.stream.status.value) for channel in channels)),
        )
