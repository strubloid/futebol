from futebol.domain.enums.source_type import SourceType
from futebol.domain.enums.stream_status import StreamStatus
from futebol.domain.models.channel import Channel
from futebol.domain.models.stream import Stream
from futebol.output.json_exporter import JsonExporter
from futebol.output.m3u_exporter import M3uExporter


def test_stream_status_handling_marks_alive_from_success() -> None:
    stream = Stream(url="https://example.org/live.m3u8")

    updated = stream.with_status(StreamStatus.ALIVE, status_code=200)

    assert updated.status == StreamStatus.ALIVE
    assert updated.status_code == 200


def test_m3u_exporter_outputs_only_included_alive_channels() -> None:
    alive = Channel(
        name="CazéTV",
        stream=Stream(url="https://example.org/live.m3u8", status=StreamStatus.ALIVE),
        source_type=SourceType.OFFICIAL,
        include_in_playlist=True,
    )
    unknown = Channel(
        name="Unknown",
        stream=Stream(url="https://unknown.example/live.m3u8", status=StreamStatus.ALIVE),
        source_type=SourceType.UNKNOWN,
        include_in_playlist=False,
    )

    output = M3uExporter().export([alive, unknown])

    assert output.startswith("#EXTM3U")
    assert "CazéTV" in output
    assert "Unknown" not in output


def test_json_exporter_reports_included_and_rejected_channels() -> None:
    channel = Channel(
        name="Unknown",
        stream=Stream(url="https://unknown.example/live.m3u8"),
        source_type=SourceType.UNKNOWN,
        include_in_playlist=False,
        rejection_reason="unknown source",
    )

    output = JsonExporter().export([channel])

    assert '"rejection_reason": "unknown source"' in output
    assert '"include_in_playlist": false' in output
