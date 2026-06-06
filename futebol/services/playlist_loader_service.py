from pathlib import Path

from futebol.infrastructure.http.http_client import HttpClient
from futebol.validators.url_validator import UrlValidator


class PlaylistLoaderService:
    def __init__(
        self, http_client: HttpClient | None = None, url_validator: UrlValidator | None = None
    ) -> None:
        self._http_client = http_client or HttpClient()
        self._url_validator = url_validator or UrlValidator()

    def load(self, source: str) -> str:
        if self._url_validator.is_valid(source):
            return self._http_client.get_text(source).text
        return Path(source).read_text(encoding="utf-8")
