"""JSON конфиги и fallback предупреждений."""

from __future__ import annotations

from typing import Dict

from infrastructure.config.json_store import JsonStore


def _default_warnings() -> Dict:
    return {}


def _default_warnings_config() -> Dict:
    return {
        "punishments": {
            "3": "mute_1h",
            "5": "mute_12h",
            "7": "kick",
            "10": "ban",
        }
    }


class WarningsStore:
    """Хранилище предупреждений в JSON."""

    def __init__(self, path: str = "warnings.json") -> None:
        self._store = JsonStore(path, _default_warnings)

    def load(self) -> Dict:
        return self._store.load()

    def save(self, data: Dict) -> None:
        self._store.save(data)


class WarningsConfigStore:
    """Хранилище конфигурации предупреждений в JSON."""

    def __init__(self, path: str = "warnings_config.json") -> None:
        self._store = JsonStore(path, _default_warnings_config)

    def load(self) -> Dict:
        return self._store.load()

    def save(self, data: Dict) -> None:
        self._store.save(data)
