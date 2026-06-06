from typer.testing import CliRunner

from futebol.app.cli import app


def test_futebol_without_arguments_shows_interactive_menu() -> None:
    result = CliRunner().invoke(app, [], input="0\n")

    assert result.exit_code == 0
    assert "Futebol IPTV" in result.output
    assert "1. Download M3U URLs from a text file and add them" in result.output
    assert "2. Add all .m3u/.m3u8 files from a folder" in result.output
    assert "3. Scan configured sources" in result.output
    assert "8. Run normal pipeline" in result.output
    assert "0. Exit" in result.output
    assert "Bye." in result.output


def test_futebol_menu_rejects_unknown_option_then_exits() -> None:
    result = CliRunner().invoke(app, [], input="99\n0\n")

    assert result.exit_code == 0
    assert "Unknown option. Pick a number from the menu." in result.output
    assert "Bye." in result.output
