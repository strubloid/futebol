"""Simplified CLI — three commands only.

   * ``load-servers`` — parse M3U sources, test streams, merge into index
   * ``update-channels`` — re-test all streams, keep only working
   * ``restore-channels`` — restore index from backup
"""

from __future__ import annotations

import typer

from futebol.app.application import Application

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
