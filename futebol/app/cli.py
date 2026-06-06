from pathlib import Path
from typing import Annotated

import typer

from futebol.app.application import Application
from futebol.output.console_reporter import ConsoleReporter

app = typer.Typer(help="Legal IPTV discovery and playlist management for football coverage.")
sources_app = typer.Typer(help="Manage legal/user-provided playlist sources.")
app.add_typer(sources_app, name="sources")


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


@app.command()
def scan() -> None:
    channels = Application().scan()
    ConsoleReporter().render(channels)


@app.command("filter")
def filter_command(
    category: Annotated[str, typer.Option()] = "football",
    language: Annotated[str | None, typer.Option()] = None,
) -> None:
    channels = Application().filter_channels(category=category, language=language)
    ConsoleReporter().render(channels)


@app.command("validate-streams")
def validate_streams() -> None:
    channels = Application().validate_streams()
    ConsoleReporter().render(channels)


@app.command()
def export(
    format: Annotated[str, typer.Option()] = "m3u",
    output: Annotated[Path, typer.Option()] = Path("futebol-worldcup.m3u"),
) -> None:
    Application().export(format, output)
    typer.echo(f"Exported {format} to {output}")


@app.command()
def report() -> None:
    ConsoleReporter().render(Application().channels())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
