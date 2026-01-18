"""JSON конфиг тикетов."""

from __future__ import annotations

from typing import Dict

from infrastructure.config.json_store import JsonStore


def _default_tickets() -> Dict:
    return {
        "ticket_category": None,
        "support_role": None,
        "ticket_counter": 0,
    }


class TicketsConfigStore:
    """Хранилище конфигурации тикетов в JSON."""

    def __init__(self, path: str = "tickets_config.json") -> None:
        self._store = JsonStore(path, _default_tickets)

    def load(self) -> Dict:
        return self._store.load()

    def save(self, data: Dict) -> None:
        self._store.save(data)
