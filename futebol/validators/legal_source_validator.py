from urllib.parse import urlparse

from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.search_result import SearchResult


class LegalSourceValidator:
    _blocked_terms = ("xtream", "stalker", "panel", "premium-iptv", "pirate", "warez")
    _official_hosts = (
        "fifa.com",
        "youtube.com",
        "youtu.be",
        "cazetv.com.br",
        "globo.com",
        "ge.globo.com",
    )

    def classify_url(self, url: str, declared_type: SourceType | None = None) -> SourceType:
        lowered = url.lower()
        if any(term in lowered for term in self._blocked_terms):
            return SourceType.BLOCKED_REJECTED
        if declared_type is not None:
            return declared_type
        host = urlparse(url).netloc.lower()
        if any(
            host == official or host.endswith(f".{official}") for official in self._official_hosts
        ):
            return SourceType.OFFICIAL
        return SourceType.UNKNOWN

    def can_auto_include(self, result: SearchResult) -> bool:
        return result.source_type in {
            SourceType.OFFICIAL,
            SourceType.PUBLIC_LEGAL,
            SourceType.USER_PROVIDED,
        }
