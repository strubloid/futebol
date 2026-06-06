from futebol.config.settings import Settings
from futebol.infrastructure.http.http_client import HttpClient
from futebol.services.playlist_loader_service import PlaylistLoaderService


class PlaylistLoaderFactory:
    def create(self, settings: Settings) -> PlaylistLoaderService:
        return PlaylistLoaderService(http_client=HttpClient(settings.stream_timeout_seconds))
