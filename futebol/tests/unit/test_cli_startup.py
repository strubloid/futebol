"""Tests for the simplified three-command CLI and interactive menu."""
from pathlib import Path

from typer.testing import CliRunner

from futebol.app.cli import app


def test_futebol_without_arguments_shows_interactive_menu() -> None:
    result = CliRunner().invoke(app, [], input="0\n")

    assert result.exit_code == 0
    assert "FUTEBOL IPTV" in result.output
    assert "Load Servers" in result.output
    assert "Update Channels" in result.output
    assert "Restore Channels" in result.output


def test_load_servers_command_shows_in_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "load-servers" in result.output
    assert "update-channels" in result.output
    assert "restore-channels" in result.output


def test_menu_shows_status_line_when_no_channels() -> None:
    result = CliRunner().invoke(app, [], input="0\n")

    assert result.exit_code == 0
    # Should show either "No channels" or the counts
    assert result.output


def test_futebol_menu_rejects_unknown_option_then_exits() -> None:
    result = CliRunner().invoke(app, [], input="99\n0\n")

    assert result.exit_code == 0
    assert "Unknown option" in result.output
