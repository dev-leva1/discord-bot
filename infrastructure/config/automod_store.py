"""JSON конфиг автомодерации."""

from __future__ import annotations

from typing import Dict

from infrastructure.config.json_store import JsonStore


def _default_automod() -> Dict:
    return {
        "banned_words": [],
        "spam_threshold": 5,
        "spam_interval": 5,
        "max_mentions": 3,
        "max_warnings": 3,
        "mute_duration": "1h",
    }


class AutomodConfigStore:
    """Хранилище конфигурации автомодерации в JSON."""

    def __init__(self, path: str = "automod_config.json") -> None:
        self._store = JsonStore(path, _default_automod)

    def load(self) -> Dict:
        return self._store.load()

    def save(self, data: Dict) -> None:
        self._store.save(data)
