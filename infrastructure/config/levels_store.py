"""JSON fallback для уровней."""

from __future__ import annotations

from typing import Dict

from infrastructure.config.json_store import JsonStore


def _default_levels() -> Dict:
    return {}


class LevelsStore:
    """Хранилище уровней в JSON как fallback."""

    def __init__(self, path: str = "levels.json") -> None:
        self._store = JsonStore(path, _default_levels)

    def load(self) -> Dict:
        return self._store.load()

    def save(self, data: Dict) -> None:
        self._store.save(data)
