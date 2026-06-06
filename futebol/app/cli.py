from pathlib import Path
from typing import Annotated

import typer

from futebol.app.application import Application
from futebol.output.console_reporter import ConsoleReporter

app = typer.Typer(
    name="futebol",
    help="Legal IPTV discovery and playlist management for football coverage.",
    invoke_without_command=True,
)
sources_app = typer.Typer(help="Manage legal/user-provided playlist sources.")
app.add_typer(sources_app, name="sources")


@app.callback()
def interactive_start(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        run_interactive_menu()
        raise typer.Exit()


def run_interactive_menu() -> None:
    while True:
        typer.echo()
        typer.echo("Futebol IPTV")
        typer.echo("============")
        typer.echo("1. Load M3U playlists")
        typer.echo("2. Scan configured sources")
        typer.echo("3. Filter football / Brazilian Portuguese channels")
        typer.echo("4. Validate streams")
        typer.echo("5. Export playlist")
        typer.echo("6. Show report")
        typer.echo("7. Run normal pipeline: scan -> filter -> validate -> export")
        typer.echo("0. Exit")
        choice = typer.prompt("Pick an action", default="0").strip()

        if choice == "0":
            typer.echo("Bye.")
            return
        if choice == "1":
            _menu_load_m3u()
        elif choice == "2":
            _render_scan()
        elif choice == "3":
            _render_filter()
        elif choice == "4":
            _render_validate_streams()
        elif choice == "5":
            _menu_export()
        elif choice == "6":
            _render_report()
        elif choice == "7":
            _menu_run_pipeline()
        else:
            typer.echo("Unknown option. Pick a number from the menu.")


def _menu_load_m3u() -> None:
    while True:
        typer.echo()
        typer.echo("Load M3U playlists")
        typer.echo("==================")
        typer.echo("1. Load from a file")
        typer.echo("2. Load from a folder")
        typer.echo("3. Download from an internet URL")
        typer.echo("4. Search sports playlists for me")
        typer.echo("0. Back")
        choice = typer.prompt("Pick a load action", default="0").strip()

        if choice == "0":
            return
        if choice == "1":
            _menu_add_file()
        elif choice == "2":
            _menu_add_folder()
        elif choice == "3":
            _menu_download_url()
        elif choice == "4":
            _menu_download_public_playlists()
        else:
            typer.echo("Unknown option. Pick a number from the load menu.")


def _menu_add_file() -> None:
    path = Path(typer.prompt("M3U file"))
    Application().add_source_file(path)
    typer.echo(f"Added source file: {path}")


def _menu_download_list() -> None:
    url_list = Path(typer.prompt("URL list file", default="m3u-urls.txt"))
    output_dir = Path(typer.prompt("Download folder", default="m3u"))
    summary = Application().download_source_list(url_list, output_dir)
    typer.echo(
        f"Downloaded {summary.downloaded} valid playlist(s) into {output_dir}; "
        f"skipped {summary.skipped}."
    )


def _menu_download_url() -> None:
    url = typer.prompt("M3U/M3U8 URL").strip()
    destination = Path("m3u")
    summary = Application().download_source_url(url, destination)
    typer.echo(
        f"Downloaded {summary.downloaded} playlist(s) into {destination}; "
        f"skipped {summary.skipped}."
    )


def _menu_add_folder() -> None:
    path = Path(typer.prompt("M3U folder", default="m3u"))
    imported = Application().add_source_folder(path)
    typer.echo(f"Added {imported} playlist source(s) from folder: {path}")


def _menu_download_public_playlists() -> None:
    destination = Path("m3u")
    summary = Application().download_public_playlists(destination)
    typer.echo(
        f"Downloaded {summary.downloaded} public playlist(s) into {destination}; "
        f"skipped {summary.skipped}."
    )


def _menu_search_local_playlists() -> None:
    search_root = Path(typer.prompt("Search folder", default="."))
    destination = Path(typer.prompt("Copy found playlists to", default="m3u"))
    summary = Application().search_and_add_local_playlists(search_root, destination)
    typer.echo(
        f"Found {summary.found} playlist file(s); copied {summary.copied} "
        f"into {destination}; added {summary.added} source(s)."
    )


def _render_scan() -> None:
    channels = Application().scan()
    ConsoleReporter().render(channels)


def _render_filter() -> None:
    channels = Application().filter_channels(category="football", language="pt-BR")
    ConsoleReporter().render(channels)


def _render_validate_streams() -> None:
    channels = Application().validate_streams()
    ConsoleReporter().render(channels)


def _menu_export() -> None:
    output = Path(typer.prompt("Output playlist", default="futebol-worldcup.m3u"))
    Application().export("m3u", output)
    typer.echo(f"Exported m3u to {output}")


def _render_report() -> None:
    ConsoleReporter().render(Application().channels())


def _menu_run_pipeline() -> None:
    output = Path(typer.prompt("Output playlist", default="futebol-worldcup.m3u"))
    typer.echo("Scanning sources...")
    ConsoleReporter().render(Application().scan())
    typer.echo("Filtering football / pt-BR channels...")
    ConsoleReporter().render(Application().filter_channels(category="football", language="pt-BR"))
    typer.echo("Validating streams...")
    ConsoleReporter().render(Application().validate_streams())
    Application().export("m3u", output)
    typer.echo(f"Exported m3u to {output}")


@sources_app.command("add")
def sources_add(
    url: Annotated[str | None, typer.Option(help="Legal/user-provided M3U/M3U8 URL")] = None,
) -> None:
    if url is None:
        raise typer.BadParameter("--url is required")
    Application().add_source_url(url)
    typer.echo(f"Added source URL: {url}")


@sources_app.command("add-file")
def sources_add_file(
    path: Annotated[Path, typer.Argument(help="Local M3U/M3U8 playlist file")],
) -> None:
    Application().add_source_file(path)
    typer.echo(f"Added source file: {path}")


@sources_app.command("add-folder")
def sources_add_folder(
    path: Annotated[Path, typer.Argument(help="Folder containing .m3u/.m3u8 playlist files")],
) -> None:
    imported = Application().add_source_folder(path)
    typer.echo(f"Added {imported} playlist source(s) from folder: {path}")


@sources_app.command("download-list")
def sources_download_list(
    url_list: Annotated[
        Path,
        typer.Argument(help="Text file with one legal/user-provided playlist URL per line"),
    ],
    output_dir: Annotated[
        Path, typer.Option(help="Folder where downloaded M3U/M3U8 files are saved")
    ] = Path("m3u"),
) -> None:
    summary = Application().download_source_list(url_list, output_dir)
    typer.echo(
        f"Downloaded {summary.downloaded} valid playlist(s) into {output_dir}; "
        f"skipped {summary.skipped}."
    )


@sources_app.command("download-url")
def sources_download_url(
    url: Annotated[str, typer.Argument(help="Legal/user-provided M3U/M3U8 URL to download")],
    output_dir: Annotated[
        Path, typer.Option(help="Folder where downloaded M3U/M3U8 file is saved")
    ] = Path("m3u"),
) -> None:
    summary = Application().download_source_url(url, output_dir)
    typer.echo(
        f"Downloaded {summary.downloaded} playlist(s) into {output_dir}; "
        f"skipped {summary.skipped}."
    )


@sources_app.command("search-local")
def sources_search_local(
    search_root: Annotated[
        Path,
        typer.Argument(help="Folder to recursively search for .m3u/.m3u8 files"),
    ] = Path("."),
    output_dir: Annotated[
        Path, typer.Option(help="Folder where found playlist files are copied")
    ] = Path("m3u"),
) -> None:
    summary = Application().search_and_add_local_playlists(search_root, output_dir)
    typer.echo(
        f"Found {summary.found} playlist file(s); copied {summary.copied} "
        f"into {output_dir}; added {summary.added} source(s)."
    )


@sources_app.command("download-public")
def sources_download_public(
    output_dir: Annotated[
        Path, typer.Option(help="Folder where public M3U/M3U8 files are saved")
    ] = Path("m3u"),
) -> None:
    summary = Application().download_public_playlists(output_dir)
    typer.echo(
        f"Downloaded {summary.downloaded} public playlist(s) into {output_dir}; "
        f"skipped {summary.skipped}."
    )


@app.command()
def scan() -> None:
    _render_scan()


@app.command("filter")
def filter_command(
    category: Annotated[str, typer.Option()] = "football",
    language: Annotated[str | None, typer.Option()] = None,
) -> None:
    channels = Application().filter_channels(category=category, language=language)
    ConsoleReporter().render(channels)


@app.command("validate-streams")
def validate_streams() -> None:
    _render_validate_streams()


@app.command()
def export(
    format: Annotated[str, typer.Option()] = "m3u",
    output: Annotated[Path, typer.Option()] = Path("futebol-worldcup.m3u"),
) -> None:
    Application().export(format, output)
    typer.echo(f"Exported {format} to {output}")


@app.command()
def report() -> None:
    _render_report()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
