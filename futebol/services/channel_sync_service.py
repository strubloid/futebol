"""Bridge between the curated channels/ index and .futebol/channels.json.

Handles backup, deduplicated updates, restore from backup, and cleanup
of non-working channels from the aggregate index (no individual files).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from futebol.config.settings import Settings
from futebol.domain.enums.source_type import SourceType
from futebol.domain.enums.stream_status import StreamStatus
from futebol.domain.models.channel import Channel
from futebol.domain.models.stream import Stream
from futebol.repositories.channel_repository import ChannelRepository
from futebol.services.channel_index_service import (
    ChannelIndexEntry,
    ChannelIndexService,
)


@dataclass
class SyncSummary:
    total_in_index: int
    updated: int
    added: int
    backup_path: str | None = None


@dataclass
class CleanSummary:
    removed: int
    remaining: int


class ChannelSyncService:
    """Bridge between channels/index.json (curated) and .futebol/channels.json.

    Responsibilities:
    - Backup ``.futebol/channels.json`` to ``.futebol/channels_backup.json``
    - Sync the ``channels/`` index into ``channels.json`` with dedup by tvg_id
    - Restore ``channels.json`` from a backup
    - Remove all ``working: false`` channels from the aggregate index
    """

    def __init__(
        self,
        channel_index_service: ChannelIndexService,
        channel_repository: ChannelRepository,
        settings: Settings | None = None,
    ) -> None:
        self._index_service = channel_index_service
        self._channel_repo = channel_repository
        self._settings = settings or Settings.from_env()
        self._data_dir: Path = self._settings.data_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_channels(self) -> SyncSummary:
        """Backup ``channels.json``, then merge channels/ index into it.

        *Never* creates duplicates — if a tvg_id already exists in
        ``channels.json``, the entry is **overwritten** (updated) with
        the value from the index, preserving the user's working flag.

        Returns a :class:`SyncSummary` with counts.
        """
        # 1. Backup current channels.json
        backup_path = self._backup_channels_json()

        # 2. Load index entries
        index_entries = self._index_service.list_all()

        # 3. Load current app channels keyed by tvg_id
        existing: dict[str, Channel] = {}
        for ch in self._channel_repo.list():
            key = ch.tvg_id or ch.name
            if key:
                existing[key] = ch

        # 4. Merge — dedup by tvg_id, overwrite existing
        updated_count = 0
        added_count = 0
        result: dict[str, Channel] = dict(existing)  # copy

        for entry in index_entries:
            channel = self._entry_to_channel(entry)
            key = channel.tvg_id or channel.name
            if not key:
                continue
            if key in result:
                updated_count += 1
            else:
                added_count += 1
            result[key] = channel

        # 5. Save
        self._channel_repo.save(list(result.values()))

        return SyncSummary(
            total_in_index=len(index_entries),
            updated=updated_count,
            added=added_count,
            backup_path=str(backup_path) if backup_path else None,
        )

    def restore_channels(self) -> int:
        """Restore ``channels.json`` from ``channels_backup.json``.

        Returns the number of channels restored, or 0 if no backup exists.
        """
        backup = self._data_dir / "channels_backup.json"
        if not backup.exists():
            return 0

        backup_repo = ChannelRepository(backup)
        channels = backup_repo.list()
        self._channel_repo.save(channels)
        return len(channels)

    def clean_broken(self) -> CleanSummary:
        """Remove all ``working: false`` channels from the index.

        1. Reads the aggregate index and filters out non-working entries.
        2. Rewrites the aggregate index without them.
        3. Removes those channels from ``.futebol/channels.json``.

        No individual per-channel files exist to delete.
        Returns counts of removed vs remaining.
        """
        all_entries = self._index_service.list_all()
        broken = [e for e in all_entries if not e.working]
        healthy = [e for e in all_entries if e.working]

        if not broken:
            return CleanSummary(removed=0, remaining=len(healthy))

        # Rewrite the aggregate index without broken entries
        self._index_service._write_index(healthy)

        # Remove broken channels from channels.json
        app_channels = self._channel_repo.list()
        tvg_ids_to_keep = {e.tvg_id for e in healthy}
        healthy_app = [
            ch
            for ch in app_channels
            if (ch.tvg_id or ch.name) in tvg_ids_to_keep
            if (ch.tvg_id or ch.name)
        ]
        self._channel_repo.save(healthy_app)

        return CleanSummary(removed=len(broken), remaining=len(healthy))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _backup_channels_json(self) -> Path | None:
        """Copy ``.futebol/channels.json`` -> ``.futebol/channels_backup.json``.

        Returns the backup path, or None if no source file exists.
        """
        source = self._data_dir / "channels.json"
        if not source.exists():
            return None
        backup = self._data_dir / "channels_backup.json"
        shutil.copy2(source, backup)
        return backup

    @staticmethod
    def _entry_to_channel(entry: ChannelIndexEntry) -> Channel:
        """Convert a ``ChannelIndexEntry`` to a ``Channel`` domain object."""
        return Channel(
            name=entry.name,
            tvg_id=entry.tvg_id,
            tvg_logo=entry.logo_url,
            group_title=entry.group_title,
            source_url="channels/index.json",
            source_type=SourceType.USER_PROVIDED,
            stream=Stream(url=entry.stream_url, status=StreamStatus.UNCHECKED),
            include_in_playlist=entry.working,
        )
