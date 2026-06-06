from __future__ import annotations

from dataclasses import dataclass, replace

from futebol.domain.enums.stream_status import StreamStatus


@dataclass(frozen=True, slots=True)
class Stream:
    url: str
    status: StreamStatus = StreamStatus.UNCHECKED
    status_code: int | None = None
    content_type: str | None = None
    error: str | None = None

    def with_status(
        self,
        status: StreamStatus,
        *,
        status_code: int | None = None,
        content_type: str | None = None,
        error: str | None = None,
    ) -> Stream:
        return replace(
            self,
            status=status,
            status_code=status_code,
            content_type=content_type,
            error=error,
        )
