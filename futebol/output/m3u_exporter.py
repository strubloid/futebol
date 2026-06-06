from futebol.domain.models.channel import Channel


class M3uExporter:
    def export(self, channels: list[Channel]) -> str:
        lines = ["#EXTM3U"]
        for channel in channels:
            if not channel.include_in_playlist:
                continue
            attrs: list[str] = []
            if channel.tvg_id:
                attrs.append(f'tvg-id="{channel.tvg_id}"')
            if channel.tvg_name:
                attrs.append(f'tvg-name="{channel.tvg_name}"')
            if channel.tvg_logo:
                attrs.append(f'tvg-logo="{channel.tvg_logo}"')
            if channel.group_title:
                attrs.append(f'group-title="{channel.group_title}"')
            suffix = f" {' '.join(attrs)}" if attrs else ""
            lines.append(f"#EXTINF:-1{suffix},{channel.name}")
            lines.append(channel.stream.url)
        return "\n".join(lines) + "\n"
