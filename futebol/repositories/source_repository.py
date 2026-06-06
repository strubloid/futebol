from __future__ import annotations

import builtins
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from futebol.domain.enums.source_type import SourceType
from futebol.domain.models.search_result import SearchResult


class SourceRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def add(self, source: SearchResult) -> None:
        sources = self.list()
        if source.url not in {item.url for item in sources}:
            sources.append(source)
        self.save(sources)

    def list(self) -> list[SearchResult]:
        if not self._path.exists():
            return []
        raw_data: Any = json.loads(self._path.read_text(encoding="utf-8"))
        data = cast(list[dict[str, Any]], raw_data)
        return [
            SearchResult(
                title=str(item["title"]),
                url=str(item["url"]),
                source_type=SourceType(str(item["source_type"])),
                description=self._optional_str(item.get("description")),
                legitimacy_note=self._optional_str(item.get("legitimacy_note")),
                language=self._optional_str(item.get("language")),
                region=self._optional_str(item.get("region")),
            )
            for item in data
        ]

    def save(self, sources: builtins.list[SearchResult]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(source) | {"source_type": source.source_type.value} for source in sources]
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _optional_str(self, value: object) -> str | None:
        return value if isinstance(value, str) else None
