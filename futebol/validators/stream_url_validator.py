from futebol.validators.url_validator import UrlValidator


class StreamUrlValidator:
    def __init__(self, url_validator: UrlValidator | None = None) -> None:
        self._url_validator = url_validator or UrlValidator()

    def is_valid(self, url: str) -> bool:
        if not self._url_validator.is_valid(url):
            return False
        lowered = url.lower()
        return (
            lowered.endswith((".m3u8", ".m3u"))
            or "m3u8" in lowered
            or "playlist" in lowered
            or "live" in lowered
        )
