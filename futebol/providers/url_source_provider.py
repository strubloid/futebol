from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.search_result import SearchResult
from futebol.providers.base_source_provider import BaseSourceProvider


class UrlSourceProvider(BaseSourceProvider):
    def __init__(self, urls: list[str], source_type: SourceType = SourceType.USER_PROVIDED) -> None:
        self._urls = urls
        self._source_type = source_type

    def sources(self) -> list[SearchResult]:
        return [
            SearchResult(
                title=url,
                url=url,
                source_type=self._source_type,
                legitimacy_note="User-provided URL; user is responsible for rights",
            )
            for url in self._urls
        ]
