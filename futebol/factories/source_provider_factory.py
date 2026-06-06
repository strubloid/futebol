from pathlib import Path

from futebol.providers.base_source_provider import BaseSourceProvider
from futebol.providers.local_file_source_provider import LocalFileSourceProvider
from futebol.providers.official_broadcaster_provider import OfficialBroadcasterProvider
from futebol.providers.url_source_provider import UrlSourceProvider


class SourceProviderFactory:
    def local_files(self, paths: list[Path]) -> BaseSourceProvider:
        return LocalFileSourceProvider(paths)

    def urls(self, urls: list[str]) -> BaseSourceProvider:
        return UrlSourceProvider(urls)

    def official_broadcasters(self) -> BaseSourceProvider:
        return OfficialBroadcasterProvider()
