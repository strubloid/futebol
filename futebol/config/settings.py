from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    stream_timeout_seconds: float = 8.0
    allow_unknown_sources: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            stream_timeout_seconds=float(os.getenv("FUTEBOL_STREAM_TIMEOUT_SECONDS", "8")),
            allow_unknown_sources=os.getenv("FUTEBOL_ALLOW_UNKNOWN_SOURCES", "false").lower()
            == "true",
        )
