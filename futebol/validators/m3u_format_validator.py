class M3uFormatValidator:
    def is_valid(self, content: str) -> bool:
        stripped = content.lstrip("\ufeff\n\r ")
        return stripped.startswith("#EXTM3U") and "#EXTINF" in stripped
