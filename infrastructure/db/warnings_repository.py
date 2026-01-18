"""Репозиторий предупреждений (SQLite)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from database.db import Database


class WarningsRepository:
    """Доступ к данным предупреждений в БД."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def add_warning(
        self,
        guild_id: int,
        user_id: int,
        reason: str,
        issued_by: int,
        issued_at: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> None:
        await self._db.execute(
            "INSERT INTO warnings (user_id, guild_id, reason, issued_by, issued_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                guild_id,
                reason,
                issued_by,
                issued_at or datetime.utcnow().isoformat(),
                expires_at,
            ),
        )

    async def list_warnings(
        self, guild_id: int, user_id: int
    ) -> List[Dict[str, str]]:
        return await self._db.fetch_all(
            "SELECT id, reason, issued_by, issued_at FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY issued_at ASC",
            (guild_id, user_id),
        )

    async def delete_warning(self, warning_id: int) -> None:
        await self._db.execute("DELETE FROM warnings WHERE id = ?", (warning_id,))

    async def clear_user_warnings(self, guild_id: int, user_id: int) -> None:
        await self._db.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )

    async def cleanup_expired(self, days: int = 30) -> None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        await self._db.execute(
            "DELETE FROM warnings WHERE issued_at < ?",
            (cutoff.isoformat(),),
        )

    async def migrate_from_json(self, data: Dict) -> None:
        for guild_id, guild_data in data.items():
            for user_id, warnings in guild_data.items():
                for warning in warnings:
                    await self.add_warning(
                        int(guild_id),
                        int(user_id),
                        warning.get("reason", ""),
                        int(warning.get("moderator", 0)),
                        warning.get("timestamp"),
                        None,
                    )
