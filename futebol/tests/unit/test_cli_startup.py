from pathlib import Path

from typer.testing import CliRunner

import futebol.app.cli as cli
from futebol.app.cli import app


class FakeSearchSummary:
    found = 2
    copied = 2
    added = 2


class FakeDownloadSummary:
    downloaded = 2
    skipped = 0


class FakeApplication:
    file_path: Path | None = None
    folder_path: Path | None = None
    url: str | None = None
    url_destination: Path | None = None
    search_root: Path | None = None
    destination: Path | None = None
    public_destination: Path | None = None

    def add_source_file(self, path: Path) -> None:
        FakeApplication.file_path = path

    def add_source_folder(self, path: Path) -> int:
        FakeApplication.folder_path = path
        return 2

    def download_source_url(self, url: str, output_dir: Path) -> FakeDownloadSummary:
        FakeApplication.url = url
        FakeApplication.url_destination = output_dir
        return FakeDownloadSummary()

    def search_and_add_local_playlists(
        self, search_root: Path, destination_dir: Path
    ) -> FakeSearchSummary:
        FakeApplication.search_root = search_root
        FakeApplication.destination = destination_dir
        return FakeSearchSummary()

    def download_public_playlists(self, output_dir: Path) -> FakeDownloadSummary:
        FakeApplication.public_destination = output_dir
        return FakeDownloadSummary()


def test_futebol_without_arguments_shows_interactive_menu() -> None:
    result = CliRunner().invoke(app, [], input="0\n")

    assert result.exit_code == 0
    assert "Futebol IPTV" in result.output
    assert "1. Load M3U playlists" in result.output
    assert "2. Scan configured sources" in result.output
    assert "7. Run normal pipeline" in result.output
    assert "0. Exit" in result.output
    assert "Bye." in result.output


def test_load_m3u_menu_shows_all_loading_choices() -> None:
    result = CliRunner().invoke(app, [], input="1\n0\n0\n")

    assert result.exit_code == 0
    assert "Load M3U playlists" in result.output
    assert "1. Load from a file" in result.output
    assert "2. Load from a folder" in result.output
    assert "3. Download from an internet URL" in result.output
    assert "4. Search sports playlists for me" in result.output
    assert "0. Back" in result.output


def test_load_m3u_menu_loads_from_file(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "Application", FakeApplication)
    FakeApplication.file_path = None

    result = CliRunner().invoke(app, [], input="1\n1\nplaylist.m3u\n0\n0\n")

    assert result.exit_code == 0
    assert FakeApplication.file_path == Path("playlist.m3u")
    assert "Added source file: playlist.m3u" in result.output


def test_load_m3u_menu_loads_from_folder(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "Application", FakeApplication)
    FakeApplication.folder_path = None

    result = CliRunner().invoke(app, [], input="1\n2\nm3u\n0\n0\n")

    assert result.exit_code == 0
    assert FakeApplication.folder_path == Path("m3u")
    assert "Added 2 playlist source(s) from folder: m3u" in result.output


def test_load_m3u_menu_downloads_from_internet_url_to_m3u(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "Application", FakeApplication)
    FakeApplication.url = None
    FakeApplication.url_destination = None

    result = CliRunner().invoke(app, [], input="1\n3\nhttps://example.org/sports.m3u\n0\n0\n")

    assert result.exit_code == 0
    assert FakeApplication.url == "https://example.org/sports.m3u"
    assert FakeApplication.url_destination == Path("m3u")
    assert "Downloaded 2 playlist(s) into m3u; skipped 0." in result.output


def test_load_m3u_menu_searches_sports_playlists_for_me(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "Application", FakeApplication)
    FakeApplication.public_destination = None

    result = CliRunner().invoke(app, [], input="1\n4\n0\n0\n")

    assert result.exit_code == 0
    assert FakeApplication.public_destination == Path("m3u")
    assert "Downloaded 2 public playlist(s) into m3u; skipped 0." in result.output


def test_futebol_menu_rejects_unknown_option_then_exits() -> None:
    result = CliRunner().invoke(app, [], input="99\n0\n")

    assert result.exit_code == 0
    assert "Unknown option. Pick a number from the menu." in result.output
    assert "Bye." in result.output
