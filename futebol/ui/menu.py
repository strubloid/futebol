"""Fancy interactive terminal menu for Futebol IPTV.

Uses Rich for styling — panels, colours, spinners, and progress bars
to make the CLI feel polished and approachable.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

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
from rich.table import Table
from rich.text import Text

from futebol.app.application import Application
from futebol.services.channel_index_service import ChannelIndexService
from futebol.services.channel_sync_service import ChannelSyncService

# ---------------------------------------------------------------------------
# Console singleton — consistent look throughout
# ---------------------------------------------------------------------------
_console = Console()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _header(title: str, subtitle: str = "") -> None:
    """Render a top-of-screen header panel."""
    _console.print()
    label = Text(title, style="bold yellow")
    if subtitle:
        label.append(Text(f"\n{subtitle}", style="dim white"))
    _console.print(
        Panel(
            label,
            border_style="yellow",
            padding=(1, 2),
        )
    )


def _footer(stats: str = "") -> None:
    """Render a status bar at the bottom of the screen."""
    if stats:
        _console.print(
            Panel(
                Text(stats, style="dim white"),
                border_style="dim",
                padding=(0, 1),
            )
        )


def _status_line(app: Application) -> str:
    """Build the one-line status footer showing channel counts."""
    entries = app.channel_list(all_flag=True)
    total = len(entries)
    working = sum(1 for e in entries if e.working)
    broken = total - working

    if total == 0:
        return "📡  No channels loaded yet"

    working_str = f"[green]{working}[/green]"
    broken_str = f"[red]{broken}[/red]" if broken else "[dim]0[/dim]"
    return f"📡  Working:  {working_str} / {total}   ❌  Broken:  {broken_str}"


def _confirm_dangerous(prompt_text: str, default: bool = False) -> bool:
    """Ask for confirmation with a red-styled prompt."""
    return Confirm.ask(f"[bold red]{prompt_text}[/]", default=default)


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def run_main_menu() -> None:
    """Entry point — shows the main loop until the user exits."""
    app = Application()

    while True:
        _header("⚽  FUTEBOL IPTV", "Channel Curation System")
        _console.print()
        _console.print("  [bold yellow]1[/]  [white]📥  Load Servers[/]")
        _console.print(
            "       [dim]Import M3U playlists & test stream health[/]"
        )
        _console.print()
        _console.print("  [bold yellow]2[/]  [white]🔄  Update Channels[/]")
        _console.print(
            "       [dim]Sync curated channels → app  (auto-backup)[/]"
        )
        _console.print()
        _console.print("  [bold yellow]3[/]  [white]⏪  Restore Channels[/]")
        _console.print(
            "       [dim]Restore channels.json from last backup[/]"
        )
        _console.print()
        _console.print("  [bold yellow]4[/]  [white]🧹  Clean Broken[/]")
        _console.print("       [dim]Remove all non-working channels[/]")
        _console.print()
        _console.print("  [bold yellow]5[/]  [white]⚡  Do It All[/]")
        _console.print(
            "       [dim]Load → Update → Clean in one shot[/]"
        )
        _console.print()
        _console.print("  [bold yellow]6[/]  [white]📊  Show Status[/]")
        _console.print(
            "       [dim]Quick overview of all channels[/]"
        )
        _console.print()
        _console.print("  [bold yellow]0[/]  [white]🚪  Exit[/]")
        _console.print()
        _footer(_status_line(app))

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
        elif choice == "4":
            _run_clean_broken(app)
        elif choice == "5":
            _run_do_it_all(app)
        elif choice == "6":
            _run_show_status(app)
        else:
            _console.print("[red]Unknown option. Pick a number from the menu.[/]")


# ---------------------------------------------------------------------------
# 1. Load Servers  (submenu)
# ---------------------------------------------------------------------------

def _run_load_servers(app: Application) -> None:
    while True:
        _header("📥  Load Servers", "Import M3U playlists & test each stream")
        _console.print()
        _console.print("  [bold yellow]1[/]  [white]📄  Load from file[/]")
        _console.print("       [dim]Import a single .m3u/.m3u8 file[/]")
        _console.print()
        _console.print("  [bold yellow]2[/]  [white]📁  Load from folder[/]")
        _console.print("       [dim]Import all .m3u files in a directory[/]")
        _console.print()
        _console.print("  [bold yellow]3[/]  [white]🌐  Download from URL[/]")
        _console.print("       [dim]Fetch a remote M3U playlist[/]")
        _console.print()
        _console.print(
            "  [bold yellow]4[/]  [white]🏆  Sports playlists[/]"
        )
        _console.print(
            "       [dim]Download public sports & Brazil playlists[/]"
        )
        _console.print()
        _console.print("  [bold yellow]0[/]  [white]🔙  Back to main menu[/]")
        _console.print()

        choice = Prompt.ask(
            "[bold yellow]Pick a source option[/]", default="0"
        ).strip()

        if choice == "0":
            return
        if choice == "1":
            _load_from_file(app)
        elif choice == "2":
            _load_from_folder(app)
        elif choice == "3":
            _load_from_url(app)
        elif choice == "4":
            _load_public_sports(app)
        else:
            _console.print("[red]Unknown option.[/]")


def _load_and_test(app: Application) -> None:
    """Parse M3U files from ``m3u/``, test streams, build channel index."""
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
            "[yellow]Testing streams...[/]", total=None
        )

        total, working = app.channels_load_and_test()

        progress.update(task, completed=1, total=1)

    _console.print()
    broken = total - working
    parts = [f"[bold]{total}[/] channel(s)"]
    if working:
        parts.append(f"[green]{working} working[/]")
    if broken:
        parts.append(f"[red]{broken} broken[/]")
    _console.print(f"   ✅  Load complete — {', '.join(parts)}")

    # Sync to frontend
    app.channels_regenerate()
    _console.print("   📋  Frontend synced.")


def _load_from_file(app: Application) -> None:
    path_str = Prompt.ask("[bold]Path to .m3u file[/]")
    path = Path(path_str.strip())
    if not path.exists():
        _console.print(f"[red]File not found:[/] {path}")
        return

    # Copy file into m3u/ so the parser can find it
    m3u_root = Path(__file__).resolve().parent.parent.parent / "m3u"
    m3u_root.mkdir(parents=True, exist_ok=True)
    dest = m3u_root / path.name
    shutil.copy2(path, dest)
    app.add_source_file(path)
    _console.print(f"   📥  Copied {path.name} to m3u/ folder")
    _load_and_test(app)


def _load_from_folder(app: Application) -> None:
    folder_str = Prompt.ask(
        "[bold]Path to M3U folder[/]", default="m3u"
    )
    folder = Path(folder_str.strip())
    if not folder.exists() or not folder.is_dir():
        _console.print(f"[red]Folder not found:[/] {folder}")
        return

    # Copy all M3U files into m3u/ for the parser
    m3u_root = Path(__file__).resolve().parent.parent.parent / "m3u"
    m3u_root.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in folder.iterdir():
        if f.suffix.lower() in (".m3u", ".m3u8") and f.is_file():
            dest = m3u_root / f.name
            if not dest.exists() or dest.stat().st_mtime < f.stat().st_mtime:
                shutil.copy2(f, dest)
                copied += 1
    added = app.add_source_folder(folder)
    _console.print(
        f"   📁  Copied {copied} file(s), added {added} source(s)"
    )
    _load_and_test(app)


def _load_from_url(app: Application) -> None:
    url = Prompt.ask("[bold]M3U/M3U8 URL[/]").strip()
    app.download_source_url(url, Path("m3u"))
    _console.print(f"   🌐  Downloaded playlist from URL")
    _load_and_test(app)


def _load_public_sports(app: Application) -> None:
    _console.print("   🏆  Downloading public sports & Brazil playlists...")
    summary = app.download_public_playlists(Path("m3u"))
    _console.print(
        f"   📥  {summary.downloaded} downloaded, {summary.skipped} skipped"
    )
    _load_and_test(app)


# ---------------------------------------------------------------------------
# 2. Update Channels
# ---------------------------------------------------------------------------

def _run_update_channels(app: Application) -> None:
    _header("🔄  Update Channels", "Syncing curated channels → app")

    entries = app.channel_list(all_flag=True)
    if not entries:
        _console.print("[yellow]No channels in index yet. Load Servers first.[/]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=_console,
    ) as progress:
        progress.add_task("[yellow]Backing up & syncing...[/]", total=None)
        summary = app.channels_update_sync()

    _console.print()
    _console.print(f"   ✅  Channels synced to .futebol/channels.json")
    _console.print(
        f"   📊  {summary.total_in_index} total in index  "
        f"|  [green]{summary.updated} updated[/]  "
        f"|  [cyan]{summary.added} new[/]"
    )
    if summary.backup_path:
        _console.print(f"   💾  Backup saved → {summary.backup_path}")
    _console.print()


# ---------------------------------------------------------------------------
# 3. Restore Channels
# ---------------------------------------------------------------------------

def _run_restore_channels(app: Application) -> None:
    _header("⏪  Restore Channels")

    backup = app.data_dir / "channels_backup.json"
    if not backup.exists():
        _console.print("[red]No backup found at .futebol/channels_backup.json[/]")
        return

    restored = app.channels_restore()
    if restored > 0:
        _console.print(f"   ✅  Restored [bold]{restored}[/] channel(s) from backup")
    else:
        _console.print("[yellow]Backup exists but is empty or corrupted.[/]")


# ---------------------------------------------------------------------------
# 4. Clean Broken
# ---------------------------------------------------------------------------

def _run_clean_broken(app: Application) -> None:
    _header("🧹  Clean Broken")

    entries = app.channel_list(all_flag=True)
    broken = [e for e in entries if not e.working]

    if not broken:
        _console.print("[green]No broken channels to clean. Everything is working![/]")
        return

    # Show the broken channels
    _console.print(f"[red]{len(broken)}[/] non-working channel(s) found:")
    for entry in broken[:10]:
        _console.print(f"   ✗  [dim]{entry.tvg_id}[/] — {entry.name}")
    if len(broken) > 10:
        _console.print(f"   [dim]... and {len(broken) - 10} more[/]")

    if not _confirm_dangerous(f"Delete {len(broken)} channel(s) permanently?"):
        _console.print("[yellow]Cancelled.[/]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=_console,
    ) as progress:
        progress.add_task("[yellow]Removing broken channels...[/]", total=None)
        result = app.channels_clean_broken()

    _console.print()
    _console.print(
        f"   🗑️  Removed [red]{result.removed}[/] broken channel(s)"
    )
    _console.print(f"   ✅  [green]{result.remaining}[/] working channel(s) remain")


# ---------------------------------------------------------------------------
# 6. Show Status
# ---------------------------------------------------------------------------

def _run_show_status(app: Application) -> None:
    """Render a rich table of all channels grouped by playlist."""
    _header("📊  Show Status")

    entries = app.channel_list(all_flag=True)
    if not entries:
        _console.print("[yellow]No channels loaded yet.[/]")
        return

    total = len(entries)
    working = sum(1 for e in entries if e.working)
    broken = total - working

    # Group by playlist
    groups: dict[str, list[tuple[str, str, bool]]] = {}
    for e in entries:
        pl = e.source_playlist or "Unknown"
        groups.setdefault(pl, []).append((e.tvg_id, e.name, e.working))

    _console.print()
    _console.print(f"   [bold]{total}[/] channels  |  "
                    f"[green]{working} working[/]  |  "
                    f"[red]{broken} broken[/]")
    _console.print()

    for playlist_name in sorted(groups):
        group = groups[playlist_name]
        w = sum(1 for _, _, ok in group if ok)
        b = len(group) - w
        label = f"  [bold yellow]{playlist_name}[/]  "
        label += f"[dim]({len(group)} ch · {w} ✓ · {b} ✗)[/]"
        _console.print(label)

        # Show first entries (limit to 8 per group for readability)
        for tvg_id, name, is_working in sorted(group, key=lambda x: (-x[2], x[1]))[:8]:
            icon = "[green]✓[/]" if is_working else "[red]✗[/]"
            _console.print(f"    {icon} [dim]{tvg_id}[/] — {name}")
        if len(group) > 8:
            _console.print(f"    [dim]... and {len(group) - 8} more[/]")
        _console.print()


# ---------------------------------------------------------------------------
# 5. Do It All
# ---------------------------------------------------------------------------

def _run_do_it_all(app: Application) -> None:
    _header("⚡  Do It All", "Load Servers → Update Channels → Clean Broken")

    # ---- 1. Load Servers (from m3u/ folder) ----
    _console.print("\n[bold]Step 1/3:[/] Loading servers from m3u/ folder...")
    m3u_dir = Path("m3u")
    if m3u_dir.exists() and any(m3u_dir.glob("*.m3u*")):
        added = app.add_source_folder(m3u_dir)
        _console.print(f"   📁  {added} source(s) loaded")
        total, working = app.channels_load_and_test()
        broken = total - working
        _console.print(
            f"   ✅  {total} channels — "
            f"[green]{working} working[/], "
            f"[red]{broken} broken[/]"
        )
        app.channels_regenerate()
    else:
        _console.print("[yellow]   No M3U files found in m3u/ — skipping load[/]")

    # ---- 2. Update Channels ----
    _console.print("\n[bold]Step 2/3:[/] Syncing curated channels → app...")
    summary = app.channels_update_sync()
    _console.print(
        f"   ✅  {summary.total_in_index} channels synced "
        f"| [green]{summary.updated} updated[/]"
        f" | [cyan]{summary.added} new[/]"
    )

    # ---- 3. Clean Broken ----
    _console.print("\n[bold]Step 3/3:[/] Cleaning broken channels...")
    result = app.channels_clean_broken()
    if result.removed > 0:
        _console.print(f"   🗑️  Removed [red]{result.removed}[/] broken channel(s)")
    else:
        _console.print(f"   ✅  No broken channels to clean")

    _console.print()
    _console.print("[bold green]⚡  Do It All complete![/]")
