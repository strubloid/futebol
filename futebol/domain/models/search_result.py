from dataclasses import dataclass

from futebol.domain.enums.source_type import SourceType


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    source_type: SourceType
    description: str | None = None
    legitimacy_note: str | None = None
    language: str | None = None
    region: str | None = None
