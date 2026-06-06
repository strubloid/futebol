from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path = Path(".futebol")
    stream_timeout_seconds: float = 8.0
    allow_unknown_sources: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(os.getenv("FUTEBOL_DATA_DIR", ".futebol")),
            stream_timeout_seconds=float(os.getenv("FUTEBOL_STREAM_TIMEOUT_SECONDS", "8")),
            allow_unknown_sources=os.getenv("FUTEBOL_ALLOW_UNKNOWN_SOURCES", "false").lower()
            == "true",
        )
