"""Simplified application — three operations only.

   1. ``load_servers()`` — parse M3U sources, test streams, merge into index
   2. ``update_channels()`` — re-test all streams, keep only working ones
   3. ``restore_channels()`` — restore index from ``backup.json``
"""

from __future__ import annotations

from pathlib import Path

from futebol.config.settings import Settings
from futebol.services.channel_index_service import (
    ChannelIndexService,
    LoadServersResult,
    UpdateChannelsResult,
)


class Application:
    """Provides the three user-facing operations.

    All work directly on ``channels/index.json`` — the single source of
    truth for both the backend and the Angular frontend.
    """

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        project_root = Path(__file__).resolve().parent.parent.parent
        self._m3u_dir = project_root / "m3u"
        self._channels_dir = project_root / "channels"
        self._index_service = ChannelIndexService(self._m3u_dir, self._channels_dir)

    # ------------------------------------------------------------------
    # 1. Load Servers
    # ------------------------------------------------------------------

    def load_servers(
        self,
        concurrency: int = 20,
        timeout: float | None = None,
    ) -> LoadServersResult:
        """Parse M3U files in ``m3u/``, test streams, merge into index.

        * New channels only added if the stream is working.
        * Existing channels with a changed URL are re-tested and only
          updated if the new URL works.
        * Existing channels with the same URL are kept as-is.
        * Working new channels are appended at the end of the list.
        """
        timeout = timeout if timeout is not None else self.settings.stream_timeout_seconds
        return self._index_service.load_servers(
            concurrency=concurrency,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # 2. Update Channels
    # ------------------------------------------------------------------

    def update_channels(
        self,
        concurrency: int = 20,
        timeout: float | None = None,
    ) -> UpdateChannelsResult:
        """Re-test every channel's stream; remove non-working ones."""
        timeout = timeout if timeout is not None else self.settings.stream_timeout_seconds
        return self._index_service.update_channels(
            concurrency=concurrency,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # 3. Restore Channels
    # ------------------------------------------------------------------

    def restore_channels(self) -> int:
        """Restore ``channels/index.json`` from ``channels/backup.json``."""
        return self._index_service.restore_channels()

    # ------------------------------------------------------------------
    # Query helpers (for status displays)
    # ------------------------------------------------------------------

    def channel_list(self, all_flag: bool = False):
        """List channels from the aggregate index.

        Args:
            all_flag: if True, include non-working channels.
        """
        return (
            self._index_service.list_all()
            if all_flag
            else self._index_service.list_working()
        )
