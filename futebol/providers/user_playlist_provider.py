from futebol.domain.models.search_result import SearchResult
from futebol.providers.base_source_provider import BaseSourceProvider


class UserPlaylistProvider(BaseSourceProvider):
    def __init__(self, sources: list[SearchResult]) -> None:
        self._sources = sources

    def sources(self) -> list[SearchResult]:
        return self._sources
