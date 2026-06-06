from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EpgProgram:
    channel_id: str
    title: str
    start: datetime | None = None
    stop: datetime | None = None
    description: str | None = None
    language: str | None = None
