import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from futebol.domain.enums.source_type import SourceType
from futebol.domain.enums.stream_status import StreamStatus
from futebol.domain.models.channel import Channel
from futebol.domain.models.stream import Stream


class ChannelRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, channels: list[Channel]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                [self._to_dict(channel) for channel in channels], indent=2, ensure_ascii=False
            ),
            encoding="utf-8",
        )

    def list(self) -> list[Channel]:
        if not self._path.exists():
            return []
        raw_data: Any = json.loads(self._path.read_text(encoding="utf-8"))
        data = cast(list[dict[str, object]], raw_data)
        return [self._from_dict(item) for item in data]

    def _to_dict(self, channel: Channel) -> dict[str, object]:
        return {
            "name": channel.name,
            "tvg_id": channel.tvg_id,
            "tvg_name": channel.tvg_name,
            "tvg_logo": channel.tvg_logo,
            "group_title": channel.group_title,
            "source_url": channel.source_url,
            "source_type": channel.source_type.value,
            "language": channel.language,
            "region": channel.region,
            "include_in_playlist": channel.include_in_playlist,
            "rejection_reason": channel.rejection_reason,
            "stream": asdict(channel.stream) | {"status": channel.stream.status.value},
        }

    def _from_dict(self, item: dict[str, object]) -> Channel:
        stream_data = item["stream"]
        if not isinstance(stream_data, dict):
            raise ValueError("invalid stream data")
        return Channel(
            name=str(item["name"]),
            stream=Stream(
                url=str(stream_data["url"]),
                status=StreamStatus(str(stream_data.get("status", "unchecked"))),
                status_code=stream_data.get("status_code")
                if isinstance(stream_data.get("status_code"), int)
                else None,
                content_type=self._optional_str(stream_data.get("content_type")),
                error=self._optional_str(stream_data.get("error")),
            ),
            tvg_id=self._optional_str(item.get("tvg_id")),
            tvg_name=self._optional_str(item.get("tvg_name")),
            tvg_logo=self._optional_str(item.get("tvg_logo")),
            group_title=self._optional_str(item.get("group_title")),
            source_url=self._optional_str(item.get("source_url")),
            source_type=SourceType(str(item.get("source_type", "unknown"))),
            language=self._optional_str(item.get("language")),
            region=self._optional_str(item.get("region")),
            include_in_playlist=bool(item.get("include_in_playlist", False)),
            rejection_reason=self._optional_str(item.get("rejection_reason")),
        )

    def _optional_str(self, value: object) -> str | None:
        return value if isinstance(value, str) else None
