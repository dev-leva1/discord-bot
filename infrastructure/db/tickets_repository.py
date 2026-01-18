"""Репозиторий тикетов (SQLite)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from database.db import Database


class TicketsRepository:
    """Доступ к данным тикетов в БД."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def create_ticket(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        topic: str,
        created_at: Optional[str] = None,
    ) -> None:
        await self._db.execute(
            "INSERT INTO tickets (guild_id, channel_id, user_id, created_at, topic) VALUES (?, ?, ?, ?, ?)",
            (
                guild_id,
                channel_id,
                user_id,
                created_at or datetime.utcnow().isoformat(),
                topic,
            ),
        )

    async def close_ticket(self, channel_id: int, closed_at: Optional[str] = None) -> None:
        await self._db.execute(
            "UPDATE tickets SET closed_at = ? WHERE channel_id = ?",
            (closed_at or datetime.utcnow().isoformat(), channel_id),
        )

    async def get_ticket(self, channel_id: int) -> Optional[Dict[str, str]]:
        return await self._db.fetch_one(
            "SELECT id, guild_id, channel_id, user_id, created_at, closed_at, topic FROM tickets WHERE channel_id = ?",
            (channel_id,),
        )
