"""Simplified CLI — three commands only.

   * ``load-servers`` — parse M3U sources, test streams, merge into index
   * ``update-channels`` — re-test all streams, keep only working
   * ``restore-channels`` — restore index from backup
"""

from __future__ import annotations

import typer
from pathlib import Path

from futebol.app.application import Application
from futebol.services.epg_scraper_service import EpgScraperService
from futebol.services.channel_index_service import ChannelIndexService

app = typer.Typer(
    name="futebol",
    help="⚽ IPTV channel manager — load servers, curate channels.",
    invoke_without_command=True,
)


@app.callback()
def interactive_start(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _run_interactive_menu()
        raise typer.Exit()


# ---------------------------------------------------------------------------


@app.command("load-servers")
def load_servers() -> None:
    """Parse M3U sources, test streams, merge into channel index."""
    result = Application().load_servers()
    typer.echo("")
    typer.echo(f"   ✅  Load complete — {result.total} channel(s)")
    typer.echo(f"       [green]{result.working} working[/]" if result.working else "")
    if result.new_working:
        typer.echo(f"       [cyan]+{result.new_working} new[/] working channel(s) added")
    if result.updated_urls:
        typer.echo(f"       [yellow]{result.updated_urls} URL(s)[/] updated with new working streams")
    if result.backup_path:
        typer.echo(f"       💾  Previous index backed up to {result.backup_path}")


@app.command("update-channels")
def update_channels() -> None:
    """Re-test all streams; keep only working channels."""
    result = Application().update_channels()
    typer.echo("")
    if result.removed > 0:
        typer.echo(f"   🗑️  Removed [red]{result.removed}[/] broken channel(s)")
    else:
        typer.echo("   ✅  All channels are working — nothing removed")
    typer.echo(
        f"       [green]{result.after}[/] working channel(s) remain"
        f" (was {result.before})"
    )
    if result.backup_path:
        typer.echo(f"       💾  Previous index backed up to {result.backup_path}")


@app.command("restore-channels")
def restore_channels() -> None:
    """Restore channel index from channels/backup.json."""
    restored = Application().restore_channels()
    if restored > 0:
        typer.echo(f"   ✅  Restored [bold]{restored}[/] channel(s) from backup")
        typer.echo("       Synced to frontend")
    else:
        typer.echo("   [red]No backup found at channels/backup.json[/]")


@app.command("epg-scrape")
def epg_scrape(
    tvg_ids: list[str] | None = typer.Option(
        None,
        "--channel",
        "-c",
        help="Specific tvg-id(s) to scrape (e.g. RedeGlobo.br). "
        "If omitted, scrapes all channels in the index.",
    ),
    concurrency: int = typer.Option(
        5, "--concurrency", help="Parallel HTTP requests (1-20)"
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path. "
        "Defaults to frontend/public/epg/guide.json",
    ),
) -> None:
    """Scrape TV programme guide (EPG) data from public sources."""
    # Resolve paths
    project_root = Path(__file__).resolve().parent.parent.parent
    channels_dir = project_root / "channels"
    output_path = (
        output
        or project_root / "frontend" / "public" / "epg" / "guide.json"
    )

    # Load channel index
    index_service = ChannelIndexService(
        project_root / "m3u", channels_dir
    )
    entries = index_service.list_all()

    if not entries:
        typer.echo("   [yellow]No channels in index. Run 'load-servers' first.[/]")
        raise typer.Exit(code=1)

    # Filter by tvg-ids if provided
    if tvg_ids:
        entries = [e for e in entries if e.tvg_id in tvg_ids]

    if not entries:
        typer.echo("   [yellow]No matching channels found.[/]")
        raise typer.Exit(code=1)

    # Build input lists
    tvg_id_list = [e.tvg_id for e in entries]
    name_list = [e.name for e in entries]

    typer.echo(
        f"   📺  Scraping EPG for [bold]{len(entries)}[/] channel(s)…"
    )

    scraper = EpgScraperService(
        channels_dir=channels_dir,
        output_dir=output_path.parent,
    )
    guide = scraper.scrape_all(
        tvg_ids=tvg_id_list,
        channel_names=name_list,
        concurrency=min(max(concurrency, 1), 20),
    )
    out = scraper.write_guide(guide)

    chan_count = len(guide.channels)
    prog_count = len(guide.programs)
    typer.echo("")
    typer.echo(f"   ✅  EPG scraped — [bold]{chan_count}[/] channel(s)")
    typer.echo(f"       [green]{prog_count}[/] programme(s) found")
    typer.echo(f"       💾  Written to {out}")


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------


def _run_interactive_menu() -> None:
    from futebol.ui.menu import run_main_menu

    run_main_menu()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
