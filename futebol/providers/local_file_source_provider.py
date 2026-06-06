from pathlib import Path

from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.search_result import SearchResult
from futebol.providers.base_source_provider import BaseSourceProvider


class LocalFileSourceProvider(BaseSourceProvider):
    def __init__(self, paths: list[Path]) -> None:
        self._paths = paths

    def sources(self) -> list[SearchResult]:
        return [
            SearchResult(
                title=path.name,
                url=str(path),
                source_type=SourceType.USER_PROVIDED,
                legitimacy_note="Local file provided by user",
            )
            for path in self._paths
        ]
