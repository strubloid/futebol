"""Tests for the simplified channel index service — load, update, restore."""

from __future__ import annotations

import json
from pathlib import Path

from futebol.services.channel_index_service import (
    ChannelIndexEntry,
    ChannelIndexService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_M3U = """#EXTM3U
#EXTINF:-1 tvg-id="sportv.br" tvg-logo="https://example.com/sportv.png" group-title="Esporte",SporTV
http://example.com/sportv.m3u8
#EXTINF:-1 tvg-id="cazetv.br" group-title="Entretenimento",CazéTV
http://example.com/cazetv.m3u8
"""

SAMPLE_M3U_2 = """#EXTM3U
#EXTINF:-1 tvg-id="sportv.br" tvg-logo="https://example.com/sportv.png" group-title="Esporte",SporTV
http://example.com/sportv-new.m3u8
#EXTINF:-1 tvg-id="espn.br" group-title="Esporte",ESPN
http://example.com/espn.m3u8
"""


def _make_service(tmp_path: Path) -> ChannelIndexService:
    m3u_dir = tmp_path / "m3u"
    channels_dir = tmp_path / "channels"
    m3u_dir.mkdir(parents=True)
    channels_dir.mkdir(parents=True)
    return ChannelIndexService(m3u_dir, channels_dir)


def _patch_test_stream(
    service: ChannelIndexService,
    *,
    working_urls: set[str] | None = None,
) -> None:
    """Replace the stream test with a mock that checks a known set.

    Pass ``working_urls`` to control which URLs return True.
    """
    working = working_urls or set()

    def mock_test(url: str, timeout: float = 8.0, extra_headers: dict | None = None) -> bool:  # noqa: ARG001
        return url in working

    service._test_stream_url = mock_test  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# 1. M3U Parsing
# ---------------------------------------------------------------------------


def test_parse_m3u_produces_correct_entries(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    (svc.m3u_dir / "br.m3u").write_text(SAMPLE_M3U, encoding="utf-8")

    entries = svc._parse_file(SAMPLE_M3U, "br", "br-m3u")

    assert len(entries) == 2
    assert entries[0].tvg_id == "sportv.br"
    assert entries[0].name == "SporTV"
    assert entries[0].stream_url == "http://example.com/sportv.m3u8"
    assert entries[0].group_title == "Esporte"
    assert entries[0].logo_url == "https://example.com/sportv.png"
    assert entries[0].source_playlist == "br"
    assert entries[0].working is True  # default

    assert entries[1].tvg_id == "cazetv.br"
    assert entries[1].name == "CazéTV"


def test_parse_m3u_generates_fallback_id_when_no_tvg_id(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    m3u_no_ids = (
        "#EXTM3U\n"
        '#EXTINF:-1 group-title="Geral",No ID Channel\n'
        "http://example.com/no-id.m3u8\n"
    )

    entries = svc._parse_file(m3u_no_ids, "br", "br-m3u")

    assert len(entries) == 1
    assert entries[0].tvg_id.startswith("ch-")
    assert entries[0].name == "No ID Channel"


# ---------------------------------------------------------------------------
# 2. Load Servers — merging logic
# ---------------------------------------------------------------------------


def test_load_servers_new_channel_only_added_if_working(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    (svc.m3u_dir / "br.m3u").write_text(SAMPLE_M3U, encoding="utf-8")

    # Only the first URL works
    _patch_test_stream(
        svc, working_urls={"http://example.com/sportv.m3u8"}
    )

    result = svc.load_servers(concurrency=2, timeout=3)

    # sportv should be added (working) but cazetv should NOT (broken)
    assert result.total == 1
    assert result.working == 1
    assert result.new_working == 1
    assert result.updated_urls == 0

    entries = svc.list_all()
    assert len(entries) == 1
    assert entries[0].tvg_id == "sportv.br"
    assert entries[0].working is True


def test_load_servers_existing_same_url_preserved(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    (svc.m3u_dir / "br.m3u").write_text(SAMPLE_M3U, encoding="utf-8")

    # Pre-populate with an existing entry
    existing_entry = ChannelIndexEntry(
        tvg_id="sportv.br",
        name="SporTV",
        stream_url="http://example.com/sportv.m3u8",
        group_title="Esporte",
        logo_url=None,
        source_playlist="br",
        source_playlist_id="br-m3u",
        working=True,
    )
    svc._write_index([existing_entry])

    # Both URLs work
    _patch_test_stream(
        svc,
        working_urls={
            "http://example.com/sportv.m3u8",
            "http://example.com/cazetv.m3u8",
        },
    )

    result = svc.load_servers(concurrency=2, timeout=3)

    # sportv already exists with same URL → kept as-is (still found from exercise)
    # cazetv is new and working → added
    assert result.total == 2
    assert result.working == 2
    assert result.new_working == 1  # only cazetv is new
    assert result.updated_urls == 0


def test_load_servers_changed_url_only_updated_if_new_works(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    (svc.m3u_dir / "br.m3u").write_text(SAMPLE_M3U_2, encoding="utf-8")

    # Pre-populate with sportv at OLD URL
    old_entry = ChannelIndexEntry(
        tvg_id="sportv.br",
        name="SporTV",
        stream_url="http://example.com/sportv.m3u8",
        group_title="Esporte",
        logo_url=None,
        source_playlist="br",
        source_playlist_id="br-m3u",
        working=True,
    )
    svc._write_index([old_entry])

    # sportv new URL works, espn is new and works
    _patch_test_stream(
        svc,
        working_urls={
            "http://example.com/sportv-new.m3u8",
            "http://example.com/espn.m3u8",
        },
    )

    result = svc.load_servers(concurrency=2, timeout=3)

    assert result.updated_urls == 1  # sportv URL updated
    assert result.new_working == 1  # espn is new
    assert result.total == 2
    assert result.working == 2

    entries = svc.list_all()
    sportv = next(e for e in entries if e.tvg_id == "sportv.br")
    assert sportv.stream_url == "http://example.com/sportv-new.m3u8"
    assert sportv.working is True


def test_load_servers_changed_url_rejected_if_new_broken(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    (svc.m3u_dir / "br.m3u").write_text(SAMPLE_M3U_2, encoding="utf-8")

    # Pre-populate with sportv at OLD URL
    old_entry = ChannelIndexEntry(
        tvg_id="sportv.br",
        name="SporTV",
        stream_url="http://example.com/sportv.m3u8",
        group_title="Esporte",
        logo_url=None,
        source_playlist="br",
        source_playlist_id="br-m3u",
        working=True,
    )
    svc._write_index([old_entry])

    # sportv NEW URL is broken, espn works
    _patch_test_stream(
        svc,
        working_urls={
            "http://example.com/espn.m3u8",
        },
    )

    result = svc.load_servers(concurrency=2, timeout=3)

    # sportv should KEEP old URL since the new one is broken
    # espn is new and working
    assert result.updated_urls == 0  # NOT updated — new URL was broken
    assert result.new_working == 1

    entries = svc.list_all()
    sportv = next(e for e in entries if e.tvg_id == "sportv.br")
    assert sportv.stream_url == "http://example.com/sportv.m3u8"  # old URL kept
    assert sportv.working is True


def test_load_servers_new_working_channels_appended_at_end(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    (svc.m3u_dir / "br.m3u").write_text(SAMPLE_M3U_2, encoding="utf-8")

    # Pre-populate with one existing channel
    old_entry = ChannelIndexEntry(
        tvg_id="sportv.br",
        name="SporTV",
        stream_url="http://example.com/sportv.m3u8",
        group_title="Esporte",
        logo_url=None,
        source_playlist="br",
        source_playlist_id="br-m3u",
        working=True,
    )
    svc._write_index([old_entry])

    # espn new URL works
    _patch_test_stream(
        svc,
        working_urls={
            "http://example.com/espn.m3u8",
            "http://example.com/sportv-new.m3u8",
        },
    )

    result = svc.load_servers(concurrency=2, timeout=3)

    entries = svc.list_all()
    # sportv should still be FIRST (preserved order), espn SECOND (new)
    assert entries[0].tvg_id == "sportv.br"
    assert entries[0].stream_url == "http://example.com/sportv-new.m3u8"  # updated
    assert entries[1].tvg_id == "espn.br"  # new, appended

    assert result.total == 2


# ---------------------------------------------------------------------------
# 3. Update Channels — re-test all, keep only working
# ---------------------------------------------------------------------------


def test_update_channels_removes_broken_keeps_working(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)

    entries = [
        ChannelIndexEntry(
            tvg_id="a.br", name="A", stream_url="http://example.com/a.m3u8",
            group_title="G", source_playlist="br", source_playlist_id="br-m3u",
            logo_url=None, working=True,
        ),
        ChannelIndexEntry(
            tvg_id="b.br", name="B", stream_url="http://example.com/b.m3u8",
            group_title="G", source_playlist="br", source_playlist_id="br-m3u",
            logo_url=None, working=True,
        ),
        ChannelIndexEntry(
            tvg_id="c.br", name="C", stream_url="http://example.com/c.m3u8",
            group_title="G", source_playlist="br", source_playlist_id="br-m3u",
            logo_url=None, working=True,
        ),
    ]
    svc._write_index(entries)

    # Only A and C work (B is broken)
    _patch_test_stream(
        svc,
        working_urls={
            "http://example.com/a.m3u8",
            "http://example.com/c.m3u8",
        },
    )

    result = svc.update_channels(concurrency=2, timeout=3)

    assert result.before == 3
    assert result.after == 2
    assert result.removed == 1

    remaining = svc.list_all()
    assert len(remaining) == 2
    assert {e.tvg_id for e in remaining} == {"a.br", "c.br"}
    assert all(e.working for e in remaining)


# ---------------------------------------------------------------------------
# 4. Restore Channels
# ---------------------------------------------------------------------------


def test_restore_channels_restores_backup(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)

    working = [
        ChannelIndexEntry(
            tvg_id="keep.br", name="Keep",
            stream_url="http://example.com/keep.m3u8",
            group_title="G", source_playlist="br", source_playlist_id="br-m3u",
            logo_url=None, working=True,
        ),
    ]
    svc._write_index(working)

    # Now update (remove all) via cleanup
    _patch_test_stream(svc, working_urls=set())
    svc.update_channels(concurrency=2, timeout=3)

    # Confirm index is empty
    assert len(svc.list_all()) == 0

    # Restore from backup (backup was created by update_channels)
    restored = svc.restore_channels()

    assert restored == 1
    entries = svc.list_all()
    assert len(entries) == 1
    assert entries[0].tvg_id == "keep.br"


def test_restore_channels_no_backup_returns_zero(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)

    restored = svc.restore_channels()

    assert restored == 0


# ---------------------------------------------------------------------------
# 5. Manifest
# ---------------------------------------------------------------------------


def test_manifest_is_written_with_correct_counts(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    (svc.m3u_dir / "br.m3u").write_text(SAMPLE_M3U, encoding="utf-8")

    _patch_test_stream(
        svc,
        working_urls={"http://example.com/sportv.m3u8"},
    )

    svc.load_servers(concurrency=2, timeout=3)

    manifest_path = svc.channels_dir / "manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["totalChannels"] >= 1
    assert manifest["workingChannels"] >= 1
    assert "playlists" in manifest
