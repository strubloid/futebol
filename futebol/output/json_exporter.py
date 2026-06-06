import json

from futebol.domain.models.channel import Channel


class JsonExporter:
    def export(self, channels: list[Channel]) -> str:
        return json.dumps(
            [self._to_dict(channel) for channel in channels], indent=2, ensure_ascii=False
        )

    def _to_dict(self, channel: Channel) -> dict[str, object]:
        return {
            "name": channel.name,
            "source_type": channel.source_type.value,
            "source_url": channel.source_url,
            "group_title": channel.group_title,
            "language": channel.language,
            "region": channel.region,
            "include_in_playlist": channel.include_in_playlist,
            "rejection_reason": channel.rejection_reason,
            "stream": {
                "url": channel.stream.url,
                "status": channel.stream.status.value,
                "status_code": channel.stream.status_code,
                "content_type": channel.stream.content_type,
                "error": channel.stream.error,
            },
        }
