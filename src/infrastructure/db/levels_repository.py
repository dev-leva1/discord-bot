"""Репозиторий уровней (SQLite)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from database.db import Database

from application.contracts import LevelsRepositoryContract


class LevelsRepository(LevelsRepositoryContract):
    """Доступ к данным уровней в БД."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_user_level_xp(
        self, user_id: int, guild_id: int
    ) -> Optional[Dict[str, int]]:
        return await self._db.fetch_one(
            "SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )

    async def create_user(
        self,
        user_id: int,
        guild_id: int,
        xp: int,
        level: int,
        last_message_time: Optional[str],
    ) -> None:
        await self._db.execute(
            "INSERT INTO levels (user_id, guild_id, xp, level, last_message_time) VALUES (?, ?, ?, ?, ?)",
            (user_id, guild_id, xp, level, last_message_time),
        )

    async def update_user(
        self,
        user_id: int,
        guild_id: int,
        xp: int,
        level: int,
        last_message_time: Optional[str],
    ) -> None:
        await self._db.execute(
            "UPDATE levels SET xp = ?, level = ?, last_message_time = ? WHERE user_id = ? AND guild_id = ?",
            (xp, level, last_message_time, user_id, guild_id),
        )

    async def ensure_last_message_time_column(self) -> bool:
        table_info = await self._db.fetch_all("PRAGMA table_info(levels)")
        columns = [col["name"] for col in table_info]
        if "last_message_time" not in columns:
            await self._db.execute(
                "ALTER TABLE levels ADD COLUMN last_message_time TIMESTAMP"
            )
            return True
        return False

    async def get_leaderboard(
        self, guild_id: int, limit: int
    ) -> List[Dict[str, int]]:
        leaderboard_data = await self._db.fetch_all(
            "SELECT user_id, xp, level FROM levels WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?",
            (guild_id, limit),
        )
        return [
            {
                "user_id": str(row["user_id"]),
                "xp": row["xp"],
                "level": row["level"],
            }
            for row in leaderboard_data
        ]

    async def migrate_from_json(self, data: Dict) -> None:
        await self.ensure_last_message_time_column()
        for guild_id, guild_data in data.items():
            for user_id, user_data in guild_data.items():
                existing = await self._db.fetch_one(
                    "SELECT user_id FROM levels WHERE user_id = ? AND guild_id = ?",
                    (int(user_id), int(guild_id)),
                )
                if existing:
                    continue
                current_time = datetime.now().isoformat()
                await self.create_user(
                    int(user_id),
                    int(guild_id),
                    user_data["xp"],
                    user_data["level"],
                    current_time,
                )
