"""Контракты (Protocols) для application слоя."""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, Tuple, Union


class LevelsRepositoryContract(Protocol):
    async def get_user_level_xp(
        self, user_id: int, guild_id: int
    ) -> Optional[Dict[str, int]]:
        ...

    async def create_user(
        self,
        user_id: int,
        guild_id: int,
        xp: int,
        level: int,
        last_message_time: Optional[str],
    ) -> None:
        ...

    async def update_user(
        self,
        user_id: int,
        guild_id: int,
        xp: int,
        level: int,
        last_message_time: Optional[str],
    ) -> None:
        ...

    async def ensure_last_message_time_column(self) -> bool:
        ...

    async def get_leaderboard(
        self, guild_id: int, limit: int
    ) -> List[Dict[str, int]]:
        ...

    async def migrate_from_json(self, data: Dict) -> None:
        ...


class TicketsRepositoryContract(Protocol):
    async def create_ticket(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        topic: str,
        created_at: Optional[str] = None,
    ) -> None:
        ...

    async def close_ticket(self, channel_id: int, closed_at: Optional[str] = None) -> None:
        ...

    async def get_ticket(self, channel_id: int) -> Optional[Dict[str, str]]:
        ...


class WarningsRepositoryContract(Protocol):
    async def add_warning(
        self,
        guild_id: int,
        user_id: int,
        reason: str,
        issued_by: int,
        issued_at: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> None:
        ...

    async def list_warnings(
        self, guild_id: int, user_id: int
    ) -> List[Dict[str, str]]:
        ...

    async def delete_warning(self, warning_id: int) -> None:
        ...

    async def clear_user_warnings(self, guild_id: int, user_id: int) -> None:
        ...

    async def cleanup_expired(self, days: int = 30) -> None:
        ...

    async def migrate_from_json(self, data: Dict) -> None:
        ...


class LevelingServiceContract(Protocol):
    async def process_message(self, message) -> Tuple[bool, Optional[int]]:
        ...

    async def add_experience(self, member) -> Tuple[bool, Optional[int]]:
        ...

    async def get_level_xp(
        self,
        user_id: Union[str, int],
        guild_id: Union[str, int],
    ) -> Tuple[int, int]:
        ...

    async def get_leaderboard(
        self,
        guild_id: Union[str, int],
        limit: int = 10,
    ) -> List[Dict[str, Union[str, int]]]:
        ...

    async def migrate_to_db(self) -> None:
        ...


class AutomodServiceContract(Protocol):
    config: Dict

    def load_config(self) -> Dict:
        ...

    def save_config(self) -> None:
        ...

    async def check_message(self, message) -> bool:
        ...


class TicketsServiceContract(Protocol):
    tickets_config: Dict

    def load_config(self) -> Dict:
        ...

    def save_config(self) -> None:
        ...


class WarningsServiceContract(Protocol):
    warnings: Dict
    config: Dict

    def load_warnings(self) -> Dict:
        ...

    def load_config(self) -> Dict:
        ...

    def save_warnings(self) -> None:
        ...

    async def migrate_to_db(self) -> None:
        ...

    async def cleanup_expired_warnings(self, db) -> None:
        ...


class LoggingServiceContract(Protocol):
    async def log_message_delete(self, message) -> None:
        ...

    async def log_message_edit(self, before, after) -> None:
        ...

    async def log_member_join(self, member) -> None:
        ...

    async def log_member_remove(self, member) -> None:
        ...

    async def log_member_update(self, before, after) -> None:
        ...

    async def log_voice_state_update(self, member, before, after) -> None:
        ...

    async def log_ban(self, guild, user) -> None:
        ...

    async def log_unban(self, guild, user) -> None:
        ...
