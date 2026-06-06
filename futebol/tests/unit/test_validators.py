from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.search_result import SearchResult
from futebol.validators.legal_source_validator import LegalSourceValidator
from futebol.validators.m3u_format_validator import M3uFormatValidator
from futebol.validators.url_validator import UrlValidator


def test_url_validator_accepts_http_urls_and_rejects_bad_schemes() -> None:
    validator = UrlValidator()

    assert validator.is_valid("https://example.org/playlist.m3u8")
    assert not validator.is_valid("ftp://example.org/playlist.m3u")
    assert not validator.is_valid("not a url")


def test_m3u_format_validator_requires_extm3u_and_extinf() -> None:
    validator = M3uFormatValidator()

    assert validator.is_valid("#EXTM3U\n#EXTINF:-1,Name\nhttps://example.org/live.m3u8")
    assert not validator.is_valid("https://example.org/live.m3u8")


def test_legal_validator_blocks_unknown_from_auto_include() -> None:
    validator = LegalSourceValidator()

    official = SearchResult(
        title="CazéTV", url="https://www.fifa.com/example", source_type=SourceType.OFFICIAL
    )
    unknown = SearchResult(
        title="Mystery", url="https://unknown.example/live.m3u8", source_type=SourceType.UNKNOWN
    )

    assert validator.can_auto_include(official)
    assert not validator.can_auto_include(unknown)
