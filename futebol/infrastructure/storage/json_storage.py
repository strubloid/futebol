import json
from pathlib import Path
from typing import Any


class JsonStorage:
    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> Any:
        if not self._path.exists():
            return None
        return json.loads(self._path.read_text(encoding="utf-8"))

    def write(self, data: Any) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
