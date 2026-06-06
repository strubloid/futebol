from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.search_result import SearchResult


class BroadcasterSearchService:
    def official_worldcup_brazil_sources(self) -> list[SearchResult]:
        return [
            SearchResult(
                title="FIFA World Cup 26 Brazil media rights: CazéTV",
                url="https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/caze-tv-brazil-media-rights",
                source_type=SourceType.OFFICIAL,
                description=(
                    "Official FIFA article confirming CazéTV agreement for Brazil coverage "
                    "metadata. This is not a direct stream URL."
                ),
                legitimacy_note=(
                    "Official broadcaster metadata only; app must not infer or scrape "
                    "playable URLs."
                ),
                language="pt-BR",
                region="Brazil",
            ),
            SearchResult(
                title="CazéTV official YouTube channel",
                url="https://www.youtube.com/@CazeTV",
                source_type=SourceType.OFFICIAL,
                description=(
                    "Official broadcaster page for user research and legal app/link "
                    "discovery. No scraping or paywall bypass."
                ),
                legitimacy_note=(
                    "Official page; playable streams must be user-provided or explicit "
                    "public live URLs."
                ),
                language="pt-BR",
                region="Brazil",
            ),
        ]
