"""Three-option interactive menu.

   1. Load Servers  — parse M3Us, test streams, merge into index
   2. Update Channels — re-test all, keep only working
   3. Restore Channels — restore from backup
   0. Exit
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.text import Text

from futebol.app.application import Application

# ---------------------------------------------------------------------------
_console = Console()


def _header(title: str, subtitle: str = "") -> None:
    _console.print()
    label = Text(title, style="bold yellow")
    if subtitle:
        label.append(Text(f"\n{subtitle}", style="dim white"))
    _console.print(Panel(label, border_style="yellow", padding=(1, 2)))


def _status_line(app: Application) -> str:
    entries = app.channel_list(all_flag=True)
    total = len(entries)
    working = sum(1 for e in entries if e.working)
    if total == 0:
        return "📡  No channels loaded yet"
    return f"📡  [green]{working}[/] / {total} working"


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------


def run_main_menu() -> None:
    app = Application()

    while True:
        _header("⚽  FUTEBOL IPTV")
        _console.print()
        _console.print("  [bold yellow]1[/]  [white]📥  Load Servers[/]")
        _console.print(
            "       [dim]Parse M3U playlists, test streams, merge into index[/]"
        )
        _console.print()
        _console.print("  [bold yellow]2[/]  [white]🔄  Update Channels[/]")
        _console.print("       [dim]Re-test all streams, keep only working[/]")
        _console.print()
        _console.print("  [bold yellow]3[/]  [white]⏪  Restore Channels[/]")
        _console.print(
            "       [dim]Restore index from channels/backup.json[/]"
        )
        _console.print()
        _console.print("  [bold yellow]0[/]  [white]🚪  Exit[/]")
        _console.print()
        _console.print(
            Panel(
                Text(_status_line(app), style="dim white"),
                border_style="dim",
                padding=(0, 1),
            )
        )
        _console.print()

        choice = Prompt.ask(
            "[bold yellow]Pick an action[/]", default="0"
        ).strip()

        if choice == "0":
            _console.print("\n[dim]Bye! ⚽[/]")
            return
        if choice == "1":
            _run_load_servers(app)
        elif choice == "2":
            _run_update_channels(app)
        elif choice == "3":
            _run_restore_channels(app)
        else:
            _console.print("[red]Unknown option. Pick 1, 2, 3, or 0.[/]")


# ---------------------------------------------------------------------------
# 1. Load Servers
# ---------------------------------------------------------------------------


def _run_load_servers(app: Application) -> None:
    _header("📥  Load Servers", "Parsing M3U playlists & testing each stream")

    _console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=_console,
    ) as progress:
        task = progress.add_task(
            "[yellow]Scanning M3U files & testing streams...[/]", total=None
        )
        result = app.load_servers()
        progress.update(task, completed=1, total=1)

    _console.print()
    _console.print(f"   ✅  Load complete — [bold]{result.total}[/] channel(s)")
    if result.working:
        _console.print(f"       [green]{result.working} working[/]")
    if result.new_working:
        _console.print(f"       [cyan]+{result.new_working} new[/] working channel(s) added")
    if result.updated_urls:
        _console.print(f"       [yellow]{result.updated_urls} URL(s)[/] updated with new streams")
    if result.backup_path:
        _console.print(f"       💾  Backup at {result.backup_path}")
    _console.print()


# ---------------------------------------------------------------------------
# 2. Update Channels
# ---------------------------------------------------------------------------


def _run_update_channels(app: Application) -> None:
    _header("🔄  Update Channels", "Re-testing all streams, removing broken")

    entries = app.channel_list(all_flag=True)
    if not entries:
        _console.print("[yellow]No channels loaded yet. Load Servers first.[/]")
        return

    _console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=_console,
    ) as progress:
        task = progress.add_task(
            "[yellow]Testing all channels...[/]", total=None
        )
        result = app.update_channels()
        progress.update(task, completed=1, total=1)

    _console.print()
    if result.removed > 0:
        _console.print(f"   🗑️  Removed [red]{result.removed}[/] broken channel(s)")
    else:
        _console.print("   ✅  All channels working — nothing removed")
    _console.print(
        f"       [green]{result.after}[/] working channel(s) remain"
        f" (was [dim]{result.before}[/])"
    )
    if result.backup_path:
        _console.print(f"       💾  Backup at {result.backup_path}")
    _console.print()


# ---------------------------------------------------------------------------
# 3. Restore Channels
# ---------------------------------------------------------------------------


def _run_restore_channels(app: Application) -> None:
    _header("⏪  Restore Channels")

    if not (Path(__file__).resolve().parent.parent.parent / "channels" / "backup.json").exists():
        _console.print("[red]No backup found at channels/backup.json[/]")
        return

    restored = app.restore_channels()
    if restored > 0:
        _console.print(f"   ✅  Restored [bold]{restored}[/] channel(s) from backup")
        _console.print("       Synced to frontend")
    else:
        _console.print("[yellow]Backup exists but is empty or corrupted.[/]")
    _console.print()
