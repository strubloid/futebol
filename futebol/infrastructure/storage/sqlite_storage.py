import sqlite3
from pathlib import Path


class SqliteStorage:
    def __init__(self, path: Path) -> None:
        self._path = path

    def connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._path)
