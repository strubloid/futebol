from abc import ABC, abstractmethod

from futebol.domain.models.search_result import SearchResult


class BaseSourceProvider(ABC):
    @abstractmethod
    def sources(self) -> list[SearchResult]:
        raise NotImplementedError
