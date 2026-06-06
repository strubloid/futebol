from pathlib import Path
from typing import Annotated

import typer

from futebol.app.application import Application
from futebol.output.console_reporter import ConsoleReporter
from futebol.ui.menu import run_main_menu

app = typer.Typer(
    name="futebol",
    help="⚽ IPTV channel manager — load servers, curate channels, export playlists.",
    invoke_without_command=True,
)


@app.callback()
def interactive_start(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        run_main_menu()
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Interactive menu commands (kept for direct CLI access too)
# ---------------------------------------------------------------------------


@app.command()
def scan() -> None:
    """Scan configured sources and list all discovered channels."""
    ConsoleReporter().render(Application().scan())


@app.command("filter")
def filter_command(
    category: Annotated[str, typer.Option()] = "football",
    language: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Filter channels by category and/or language."""
    channels = Application().filter_channels(category=category, language=language)
    ConsoleReporter().render(channels)


@app.command("validate-streams")
def validate_streams() -> None:
    """Probe all channel stream URLs and mark alive/broken."""
    ConsoleReporter().render(Application().validate_streams())


@app.command()
def export(
    format: Annotated[str, typer.Option()] = "m3u",
    output: Annotated[Path, typer.Option()] = Path("futebol-worldcup.m3u"),
) -> None:
    """Export curated channels to a playlist file."""
    Application().export(format, output)
    typer.echo(f"Exported {format} to {output}")


@app.command()
def report() -> None:
    """Show a summary report of all channels."""
    ConsoleReporter().render(Application().channels())


# ---------------------------------------------------------------------------
# Source management
# ---------------------------------------------------------------------------

sources_app = typer.Typer(help="Manage playlist sources (add, download).")
app.add_typer(sources_app, name="sources")


@sources_app.command("add")
def sources_add(
    url: Annotated[str | None, typer.Option(help="M3U/M3U8 URL")] = None,
) -> None:
    if url is None:
        raise typer.BadParameter("--url is required")
    Application().add_source_url(url)
    typer.echo(f"Added source URL: {url}")


@sources_app.command("add-file")
def sources_add_file(
    path: Annotated[Path, typer.Argument(help="Local .m3u/.m3u8 file")],
) -> None:
    Application().add_source_file(path)
    typer.echo(f"Added source file: {path}")


@sources_app.command("add-folder")
def sources_add_folder(
    path: Annotated[Path, typer.Argument(help="Folder with .m3u files")],
) -> None:
    imported = Application().add_source_folder(path)
    typer.echo(f"Added {imported} playlist source(s) from folder: {path}")


@sources_app.command("download-url")
def sources_download_url(
    url: Annotated[str, typer.Argument(help="M3U/M3U8 URL to download")],
    output_dir: Annotated[Path, typer.Option(help="Save folder")] = Path("m3u"),
) -> None:
    summary = Application().download_source_url(url, output_dir)
    typer.echo(
        f"Downloaded {summary.downloaded} playlist(s) into {output_dir}; "
        f"skipped {summary.skipped}."
    )


@sources_app.command("download-public")
def sources_download_public(
    output_dir: Annotated[
        Path, typer.Option(help="Save folder")
    ] = Path("m3u"),
) -> None:
    summary = Application().download_public_playlists(output_dir)
    typer.echo(
        f"Downloaded {summary.downloaded} public playlist(s) into {output_dir}; "
        f"skipped {summary.skipped}."
    )


# ---------------------------------------------------------------------------
# Channel curation commands
# ---------------------------------------------------------------------------

channels_app = typer.Typer(help="Curate channels (working flags, sync).")
app.add_typer(channels_app, name="channels")


@channels_app.command("list")
def channels_list(
    show_all: Annotated[
        bool, typer.Option("--all", help="Show also non-working channels")
    ] = False,
) -> None:
    """List indexed channels and their working status."""
    entries = Application().channel_list(all_flag=show_all)
    if not entries:
        typer.echo("No channels indexed yet. Use 'futebol' menu → Load Servers.")
        return
    for entry in entries:
        status = "✓" if entry.working else "✗"
        typer.echo(f"  {status}  {entry.tvg_id} - {entry.name}")


@channels_app.command("working-on")
def channels_working_on(
    tvg_id: Annotated[str, typer.Argument(help="tvg-id of the channel")],
) -> None:
    """Mark a channel as working (visible in frontend)."""
    entry = Application().channel_set_working(tvg_id, True)
    if entry:
        typer.echo(f"Marked '{entry.name}' ({tvg_id}) as working.")
    else:
        typer.echo(f"Channel '{tvg_id}' not found.", err=True)
        raise typer.Exit(code=1)


@channels_app.command("working-off")
def channels_working_off(
    tvg_id: Annotated[str, typer.Argument(help="tvg-id of the channel")],
) -> None:
    """Mark a channel as NOT working (hidden from frontend)."""
    entry = Application().channel_set_working(tvg_id, False)
    if entry:
        typer.echo(f"Marked '{entry.name}' ({tvg_id}) as NOT working.")
    else:
        typer.echo(f"Channel '{tvg_id}' not found.", err=True)
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
