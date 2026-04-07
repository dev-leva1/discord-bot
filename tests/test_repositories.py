"""Тесты для репозиториев базы данных."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import aiosqlite

from infrastructure.db.levels_repository import LevelsRepository
from infrastructure.db.warnings_repository import WarningsRepository
from infrastructure.db.tickets_repository import TicketsRepository


class TestLevelsRepository:
    """Тесты репозитория уровней."""

    @pytest.fixture
    async def repository(self):
        """Фикстура для создания репозитория с мок БД."""
        db = MagicMock()
        db.execute = AsyncMock()
        db.execute_many = AsyncMock()
        db.fetch_one = AsyncMock()
        db.fetch_all = AsyncMock()

        repo = LevelsRepository(db)
        return repo

    @pytest.mark.asyncio
    async def test_create_user(self, repository):
        """Тест создания пользователя."""
        await repository.create_user(
            user_id=123456,
            guild_id=789012,
            xp=100,
            level=1,
            last_message_time="2026-04-07T00:00:00"
        )

        repository._db.execute.assert_called_once()
        call_args = repository._db.execute.call_args[0]
        assert "INSERT INTO levels" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_user_level_xp(self, repository):
        """Тест получения данных пользователя."""
        repository._db.fetch_one = AsyncMock(return_value={
            "user_id": 123456,
            "guild_id": 789012,
            "xp": 100,
            "level": 1
        })

        result = await repository.get_user_level_xp(123456, 789012)

        assert result is not None
        assert result["xp"] == 100
        assert result["level"] == 1

    @pytest.mark.asyncio
    async def test_update_user(self, repository):
        """Тест обновления данных пользователя."""
        await repository.update_user(
            user_id=123456,
            guild_id=789012,
            xp=200,
            level=2,
            last_message_time="2026-04-07T01:00:00"
        )

        repository._db.execute.assert_called_once()
        call_args = repository._db.execute.call_args[0]
        assert "UPDATE levels" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, repository):
        """Тест получения таблицы лидеров."""
        repository._db.fetch_all = AsyncMock(return_value=[
            {"user_id": 1, "xp": 1000, "level": 10},
            {"user_id": 2, "xp": 800, "level": 8},
            {"user_id": 3, "xp": 600, "level": 6}
        ])

        result = await repository.get_leaderboard(789012, limit=10)

        assert len(result) == 3
        assert result[0]["xp"] == 1000
        repository._db.fetch_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_from_json_batching(self, repository):
        """Тест батчинга при миграции из JSON."""
        data = {
            "789012": {
                "123456": {"xp": 100, "level": 1},
                "234567": {"xp": 200, "level": 2},
                "345678": {"xp": 300, "level": 3}
            }
        }

        repository.ensure_last_message_time_column = AsyncMock()

        await repository.migrate_from_json(data)

        # Проверяем что был вызван execute_many (батчинг)
        repository._db.execute_many.assert_called_once()
        call_args = repository._db.execute_many.call_args[0]
        assert "INSERT OR IGNORE INTO levels" in call_args[0]
        # Проверяем что передано 3 записи
        assert len(call_args[1]) == 3

    @pytest.mark.asyncio
    async def test_ensure_last_message_time_column(self, repository):
        """Тест проверки наличия колонки last_message_time."""
        repository._db.fetch_all = AsyncMock(return_value=[
            {"name": "user_id"},
            {"name": "guild_id"},
            {"name": "xp"},
            {"name": "level"}
        ])

        await repository.ensure_last_message_time_column()

        # Должна быть попытка добавить колонку
        assert repository._db.execute.call_count >= 1


class TestWarningsRepository:
    """Тесты репозитория предупреждений."""

    @pytest.fixture
    async def repository(self):
        """Фикстура для создания репозитория с мок БД."""
        db = MagicMock()
        db.execute = AsyncMock()
        db.execute_many = AsyncMock()
        db.fetch_one = AsyncMock()
        db.fetch_all = AsyncMock()

        repo = WarningsRepository(db)
        return repo

    @pytest.mark.asyncio
    async def test_add_warning(self, repository):
        """Тест добавления предупреждения."""
        await repository.add_warning(
            guild_id=789012,
            user_id=123456,
            reason="Test warning",
            issued_by=111111,
            issued_at="2026-04-07T00:00:00",
            expires_at=None
        )

        repository._db.execute.assert_called_once()
        call_args = repository._db.execute.call_args[0]
        assert "INSERT INTO warnings" in call_args[0]

    @pytest.mark.asyncio
    async def test_list_warnings(self, repository):
        """Тест получения списка предупреждений."""
        repository._db.fetch_all = AsyncMock(return_value=[
            {
                "id": 1,
                "user_id": 123456,
                "guild_id": 789012,
                "reason": "Warning 1",
                "issued_by": 111111,
                "issued_at": "2026-04-07T00:00:00"
            },
            {
                "id": 2,
                "user_id": 123456,
                "guild_id": 789012,
                "reason": "Warning 2",
                "issued_by": 111111,
                "issued_at": "2026-04-07T01:00:00"
            }
        ])

        result = await repository.list_warnings(789012, 123456)

        assert len(result) == 2
        assert result[0]["reason"] == "Warning 1"
        repository._db.fetch_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_warning(self, repository):
        """Тест удаления предупреждения."""
        await repository.delete_warning(warning_id=1)

        repository._db.execute.assert_called_once()
        call_args = repository._db.execute.call_args[0]
        assert "DELETE FROM warnings" in call_args[0]

    @pytest.mark.asyncio
    async def test_clear_user_warnings(self, repository):
        """Тест очистки всех предупреждений пользователя."""
        await repository.clear_user_warnings(789012, 123456)

        repository._db.execute.assert_called_once()
        call_args = repository._db.execute.call_args[0]
        assert "DELETE FROM warnings" in call_args[0]

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, repository):
        """Тест очистки устаревших предупреждений."""
        await repository.cleanup_expired(days=30)

        repository._db.execute.assert_called_once()
        call_args = repository._db.execute.call_args[0]
        assert "DELETE FROM warnings" in call_args[0]
        assert "issued_at" in call_args[0]

    @pytest.mark.asyncio
    async def test_migrate_from_json_batching(self, repository):
        """Тест батчинга при миграции из JSON."""
        data = {
            "789012": {
                "123456": [
                    {
                        "reason": "Warning 1",
                        "moderator": 111111,
                        "timestamp": "2026-04-07T00:00:00"
                    },
                    {
                        "reason": "Warning 2",
                        "moderator": 111111,
                        "timestamp": "2026-04-07T01:00:00"
                    }
                ]
            }
        }

        await repository.migrate_from_json(data)

        # Проверяем что был вызван execute_many (батчинг)
        repository._db.execute_many.assert_called_once()
        call_args = repository._db.execute_many.call_args[0]
        assert "INSERT INTO warnings" in call_args[0]
        # Проверяем что передано 2 записи
        assert len(call_args[1]) == 2


class TestTicketsRepository:
    """Тесты репозитория тикетов."""

    @pytest.fixture
    async def repository(self):
        """Фикстура для создания репозитория с мок БД."""
        db = MagicMock()
        db.execute = AsyncMock()
        db.fetch_one = AsyncMock()
        db.fetch_all = AsyncMock()

        repo = TicketsRepository(db)
        return repo

    @pytest.mark.asyncio
    async def test_create_ticket(self, repository):
        """Тест создания тикета."""
        await repository.create_ticket(
            guild_id=789012,
            channel_id=111111,
            user_id=123456,
            topic="Test ticket",
            created_at="2026-04-07T00:00:00"
        )

        repository._db.execute.assert_called_once()
        call_args = repository._db.execute.call_args[0]
        assert "INSERT INTO tickets" in call_args[0]

    @pytest.mark.asyncio
    async def test_close_ticket(self, repository):
        """Тест закрытия тикета."""
        await repository.close_ticket(channel_id=111111)

        repository._db.execute.assert_called_once()
        call_args = repository._db.execute.call_args[0]
        assert "UPDATE tickets" in call_args[0]
        assert "closed_at" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_ticket(self, repository):
        """Тест получения тикета по каналу."""
        repository._db.fetch_one = AsyncMock(return_value={
            "id": 1,
            "guild_id": 789012,
            "channel_id": 111111,
            "user_id": 123456,
            "topic": "Test ticket",
            "created_at": "2026-04-07T00:00:00",
            "closed_at": None
        })

        result = await repository.get_ticket(111111)

        assert result is not None
        assert result["channel_id"] == 111111
        assert result["topic"] == "Test ticket"

    @pytest.mark.asyncio
    async def test_get_ticket_returns_none_when_not_found(self, repository):
        """Тест что get_ticket возвращает None если тикет не найден."""
        repository._db.fetch_one = AsyncMock(return_value=None)

        result = await repository.get_ticket(999999)

        assert result is None
        repository._db.fetch_one.assert_called_once()


class TestRepositoryErrorHandling:
    """Тесты обработки ошибок в репозиториях."""

    @pytest.mark.asyncio
    async def test_levels_repository_handles_db_error(self):
        """Тест обработки ошибок БД в LevelsRepository."""
        db = MagicMock()
        db.execute = AsyncMock(side_effect=Exception("DB Error"))

        repo = LevelsRepository(db)

        with pytest.raises(Exception):
            await repo.create_user(123456, 789012, 100, 1, "2026-04-07T00:00:00")

    @pytest.mark.asyncio
    async def test_warnings_repository_handles_db_error(self):
        """Тест обработки ошибок БД в WarningsRepository."""
        db = MagicMock()
        db.execute = AsyncMock(side_effect=Exception("DB Error"))

        repo = WarningsRepository(db)

        with pytest.raises(Exception):
            await repo.add_warning(789012, 123456, "Test", 111111, "2026-04-07T00:00:00", None)

    @pytest.mark.asyncio
    async def test_tickets_repository_handles_db_error(self):
        """Тест обработки ошибок БД в TicketsRepository."""
        db = MagicMock()
        db.execute = AsyncMock(side_effect=Exception("DB Error"))

        repo = TicketsRepository(db)

        with pytest.raises(Exception):
            await repo.create_ticket(789012, 111111, 123456, "Test", "2026-04-07T00:00:00")
