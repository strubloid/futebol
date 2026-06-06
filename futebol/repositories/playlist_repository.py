from pathlib import Path

from futebol.domain.models.playlist import Playlist
from futebol.services.playlist_parser_service import PlaylistParserService


class PlaylistRepository:
    def __init__(self, path: Path, parser: PlaylistParserService | None = None) -> None:
        self._path = path
        self._parser = parser or PlaylistParserService()

    def load(self) -> Playlist:
        return self._parser.parse(
            self._path.read_text(encoding="utf-8"), source_url=str(self._path)
        )
