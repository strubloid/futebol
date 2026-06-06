from rich.console import Console
from rich.table import Table

from futebol.domain.models.channel import Channel
from futebol.services.report_service import ReportService


class ConsoleReporter:
    def __init__(
        self, console: Console | None = None, report_service: ReportService | None = None
    ) -> None:
        self._console = console or Console()
        self._report_service = report_service or ReportService()

    def render(self, channels: list[Channel]) -> None:
        summary = self._report_service.summarize(channels)
        self._console.print(
            f"Total: {summary.total} | Included: {summary.included} | Rejected: {summary.rejected}"
        )
        table = Table(title="Futebol IPTV report")
        table.add_column("Channel")
        table.add_column("Status")
        table.add_column("Source")
        table.add_column("Decision")
        for channel in channels:
            table.add_row(
                channel.name,
                channel.stream.status.value,
                channel.source_type.value,
                "included"
                if channel.include_in_playlist
                else channel.rejection_reason or "rejected",
            )
        self._console.print(table)
