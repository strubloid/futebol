from pathlib import Path

from futebol.app.application import Application
from futebol.config.settings import Settings
from futebol.domain.enums.source_type import SourceType
from futebol.infrastructure.http.http_client import HttpResponse

VALID_M3U = (
    "#EXTM3U\n"
    "#EXTINF:-1 group-title=\"Esporte\",CazéTV Futebol\n"
    "https://example.org/live.m3u8\n"
)


class FakeHttpClient:
    def __init__(self, responses: dict[str, HttpResponse]) -> None:
        self.responses = responses

    def get_text(self, url: str) -> HttpResponse:
        return self.responses[url]


def make_app(tmp_path: Path, http_client: FakeHttpClient | None = None) -> Application:
    return Application(settings=Settings(data_dir=tmp_path / ".futebol"), http_client=http_client)


def test_add_source_folder_imports_all_m3u_files(tmp_path: Path) -> None:
    playlist_dir = tmp_path / "playlists"
    nested_dir = playlist_dir / "nested"
    nested_dir.mkdir(parents=True)
    (playlist_dir / "one.m3u").write_text(VALID_M3U, encoding="utf-8")
    (nested_dir / "two.m3u8").write_text(VALID_M3U, encoding="utf-8")
    (playlist_dir / "notes.txt").write_text(VALID_M3U, encoding="utf-8")

    imported = make_app(tmp_path).add_source_folder(playlist_dir)

    assert imported == 2
    sources = make_app(tmp_path)._source_repository.list()
    assert {Path(source.url).name for source in sources} == {"one.m3u", "two.m3u8"}
    assert all(source.source_type == SourceType.USER_PROVIDED for source in sources)


def test_download_source_list_saves_valid_m3u_files_and_adds_them(tmp_path: Path) -> None:
    url_list = tmp_path / "m3u-urls.txt"
    url_list.write_text(
        "# user-provided legal/public playlist URLs\n"
        "https://legal.example.org/sports.m3u\n"
        "https://legal.example.org/not-m3u.txt\n"
        "https://pirate.example.org/panel/list.m3u\n",
        encoding="utf-8",
    )
    download_dir = tmp_path / "downloaded-m3u"
    http_client = FakeHttpClient(
        {
            "https://legal.example.org/sports.m3u": HttpResponse(
                url="https://legal.example.org/sports.m3u",
                status_code=200,
                text=VALID_M3U,
                content_type="audio/x-mpegurl",
            ),
            "https://legal.example.org/not-m3u.txt": HttpResponse(
                url="https://legal.example.org/not-m3u.txt",
                status_code=200,
                text="not a playlist",
                content_type="text/plain",
            ),
        }
    )

    result = make_app(tmp_path, http_client=http_client).download_source_list(
        url_list, download_dir
    )

    assert result.downloaded == 1
    assert result.skipped == 2
    assert (download_dir / "sports.m3u").read_text(encoding="utf-8") == VALID_M3U
    sources = make_app(tmp_path)._source_repository.list()
    assert [Path(source.url).name for source in sources] == ["sports.m3u"]
