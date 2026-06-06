from futebol.domain.models.search_result import SearchResult
from futebol.providers.base_source_provider import BaseSourceProvider
from futebol.services.broadcaster_search_service import BroadcasterSearchService


class OfficialBroadcasterProvider(BaseSourceProvider):
    def __init__(self, search_service: BroadcasterSearchService | None = None) -> None:
        self._search_service = search_service or BroadcasterSearchService()

    def sources(self) -> list[SearchResult]:
        return self._search_service.official_worldcup_brazil_sources()
