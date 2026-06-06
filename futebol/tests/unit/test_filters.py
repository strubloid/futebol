from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.channel import Channel
from futebol.domain.models.stream import Stream
from futebol.filters.brazilian_portuguese_filter import BrazilianPortugueseFilter
from futebol.filters.football_filter import FootballFilter
from futebol.filters.worldcup_filter import WorldCupFilter
from futebol.services.football_detector_service import FootballDetectorService


def make_channel(name: str, group: str = "") -> Channel:
    return Channel(
        name=name,
        stream=Stream(url="https://example.org/live.m3u8"),
        group_title=group,
        source_type=SourceType.USER_PROVIDED,
    )


def test_football_detector_identifies_brazilian_worldcup_terms() -> None:
    detector = FootballDetectorService()

    assert detector.is_football_related("CazéTV Copa do Mundo Brasil")
    assert detector.is_football_related("seleção brasileira ao vivo")
    assert not detector.is_football_related("Cooking Channel")


def test_filters_football_channels() -> None:
    result = FootballFilter(FootballDetectorService()).apply(
        [make_channel("CazéTV Futebol"), make_channel("Movies")]
    )

    assert [channel.name for channel in result] == ["CazéTV Futebol"]


def test_detects_brazilian_portuguese_sources() -> None:
    result = BrazilianPortugueseFilter().apply(
        [make_channel("Brasil esporte pt-BR"), make_channel("ESPN English")]
    )

    assert [channel.name for channel in result] == ["Brasil esporte pt-BR"]


def test_worldcup_filter_matches_copa_terms() -> None:
    result = WorldCupFilter().apply(
        [make_channel("Copa do Mundo FIFA"), make_channel("Brasileirão")]
    )

    assert [channel.name for channel in result] == ["Copa do Mundo FIFA"]
