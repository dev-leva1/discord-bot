"""Тесты для системы предупреждений."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands

from warning_system import WarningSystem
from infrastructure.config import WarningsConfigStore, WarningsStore


class TestWarningSystemConfiguration:
    """Тесты конфигурации системы предупреждений."""

    @pytest.fixture
    def warning_system(self):
        """Фикстура для создания системы предупреждений."""
        bot = MagicMock()
        repository = MagicMock()
        store = MagicMock(spec=WarningsStore)
        config_store = MagicMock(spec=WarningsConfigStore)

        store.load.return_value = {}
        config_store.load.return_value = {
            "punishments": {
                "3": "mute_1h",
                "5": "mute_12h",
                "7": "kick",
                "10": "ban"
            }
        }

        system = WarningSystem(bot, repository, store, config_store)
        return system

    def test_load_warnings(self, warning_system):
        """Тест загрузки предупреждений."""
        assert warning_system.warnings == {}

    def test_load_config(self, warning_system):
        """Тест загрузки конфигурации."""
        assert "punishments" in warning_system.config
        assert warning_system.config["punishments"]["3"] == "mute_1h"

    def test_save_warnings(self, warning_system):
        """Тест сохранения предупреждений."""
        warning_system.warnings = {"123": {"456": []}}
        warning_system.save_warnings()

        warning_system.store.save.assert_called_once()


class TestWarningSystemGetUserWarnings:
    """Тесты получения предупреждений пользователя."""

    @pytest.fixture
    def warning_system(self):
        """Фикстура для создания системы предупреждений."""
        bot = MagicMock()
        repository = MagicMock()
        store = MagicMock(spec=WarningsStore)
        config_store = MagicMock(spec=WarningsConfigStore)

        store.load.return_value = {
            "789012": {
                "123456": [
                    {
                        "reason": "Test warning",
                        "moderator": 111111,
                        "timestamp": "2026-04-07T00:00:00"
                    }
                ]
            }
        }
        config_store.load.return_value = {"punishments": {}}

        system = WarningSystem(bot, repository, store, config_store)
        return system

    def test_get_existing_warnings(self, warning_system):
        """Тест получения существующих предупреждений."""
        warnings = warning_system.get_user_warnings(789012, 123456)

        assert len(warnings) == 1
        assert warnings[0]["reason"] == "Test warning"

    def test_get_warnings_creates_empty_list(self, warning_system):
        """Тест создания пустого списка для нового пользователя."""
        warnings = warning_system.get_user_warnings(789012, 999999)

        assert warnings == []
        assert "789012" in warning_system.warnings
        assert "999999" in warning_system.warnings["789012"]

    def test_get_warnings_creates_guild(self, warning_system):
        """Тест создания гильдии если не существует."""
        warnings = warning_system.get_user_warnings(999999, 123456)

        assert warnings == []
        assert "999999" in warning_system.warnings


class TestWarningSystemAddWarning:
    """Тесты добавления предупреждений."""

    @pytest.fixture
    def warning_system(self):
        """Фикстура для создания системы предупреждений."""
        bot = MagicMock()
        repository = MagicMock()
        repository.add_warning = AsyncMock()

        store = MagicMock(spec=WarningsStore)
        config_store = MagicMock(spec=WarningsConfigStore)

        store.load.return_value = {}
        config_store.load.return_value = {
            "punishments": {
                "3": "mute_1h",
                "5": "kick"
            }
        }

        system = WarningSystem(bot, repository, store, config_store)
        return system

    @pytest.mark.asyncio
    async def test_add_warning_to_bot(self, warning_system):
        """Тест что нельзя выдать предупреждение боту."""
        guild = MagicMock()
        guild.id = 789012

        member = MagicMock(spec=discord.Member)
        member.bot = True
        member.id = 123456
        member.guild = guild

        user = MagicMock()
        user.id = 111111
        user.top_role = MagicMock(position=10)

        ctx = MagicMock()
        ctx.guild = guild
        ctx.user = user
        ctx.send = AsyncMock()

        result = await warning_system.add_warning.callback(warning_system, ctx, member, "Test")

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "боту" in call_args

    @pytest.mark.asyncio
    async def test_add_warning_equal_role(self, warning_system):
        """Тест что нельзя выдать предупреждение с равной ролью."""
        guild = MagicMock()
        guild.id = 789012

        member = MagicMock(spec=discord.Member)
        member.bot = False
        member.id = 123456
        member.guild = guild
        member.top_role = MagicMock(position=10)

        user = MagicMock()
        user.id = 111111
        user.top_role = MagicMock(position=10)

        # Настройка сравнения ролей
        member.top_role.__ge__ = lambda self, other: self.position >= other.position
        user.top_role.__ge__ = lambda self, other: self.position >= other.position

        ctx = MagicMock()
        ctx.guild = guild
        ctx.user = user
        ctx.send = AsyncMock()

        result = await warning_system.add_warning.callback(warning_system, ctx, member, "Test")

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "выше или равной" in call_args

    @pytest.mark.asyncio
    async def test_add_warning_success(self, warning_system):
        """Тест успешного добавления предупреждения."""
        guild = MagicMock()
        guild.id = 789012
        guild.get_member = MagicMock(return_value=None)

        member = MagicMock(spec=discord.Member)
        member.bot = False
        member.id = 123456
        member.guild = guild
        member.mention = "<@123456>"
        member.top_role = MagicMock(position=5)

        user = MagicMock()
        user.id = 111111
        user.mention = "<@111111>"
        user.top_role = MagicMock(position=10)

        # Настройка сравнения ролей
        member.top_role.__ge__ = lambda self, other: self.position >= other.position
        user.top_role.__ge__ = lambda self, other: self.position >= other.position

        ctx = MagicMock()
        ctx.guild = guild
        ctx.user = user
        ctx.send = AsyncMock()

        await warning_system.add_warning.callback(warning_system, ctx, member, "Test reason")

        # Проверяем что предупреждение добавлено
        warnings = warning_system.get_user_warnings(789012, 123456)
        assert len(warnings) == 1
        assert warnings[0]["reason"] == "Test reason"
        assert warnings[0]["moderator"] == 111111

        # Проверяем что был вызван send
        ctx.send.assert_called()


class TestWarningSystemRemoveWarning:
    """Тесты удаления предупреждений."""

    @pytest.fixture
    def warning_system(self):
        """Фикстура для создания системы предупреждений."""
        bot = MagicMock()
        repository = MagicMock()
        repository.delete_warning = AsyncMock()
        repository.list_warnings = AsyncMock(return_value=[
            {"id": 1, "reason": "Warning 1"},
            {"id": 2, "reason": "Warning 2"}
        ])

        store = MagicMock(spec=WarningsStore)
        config_store = MagicMock(spec=WarningsConfigStore)

        store.load.return_value = {
            "789012": {
                "123456": [
                    {"reason": "Warning 1", "moderator": 111111, "timestamp": "2026-04-07T00:00:00"},
                    {"reason": "Warning 2", "moderator": 111111, "timestamp": "2026-04-07T01:00:00"}
                ]
            }
        }
        config_store.load.return_value = {"punishments": {}}

        system = WarningSystem(bot, repository, store, config_store)
        return system

    @pytest.mark.asyncio
    async def test_remove_warning_no_warnings(self, warning_system):
        """Тест удаления когда нет предупреждений."""
        guild = MagicMock()
        guild.id = 789012

        member = MagicMock(spec=discord.Member)
        member.id = 999999

        ctx = MagicMock()
        ctx.guild = guild
        ctx.send = AsyncMock()

        await warning_system.remove_warning.callback(warning_system, ctx, member, 1)

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "нет предупреждений" in call_args

    @pytest.mark.asyncio
    async def test_remove_warning_invalid_index(self, warning_system):
        """Тест удаления с неверным индексом."""
        guild = MagicMock()
        guild.id = 789012

        member = MagicMock(spec=discord.Member)
        member.id = 123456

        ctx = MagicMock()
        ctx.guild = guild
        ctx.send = AsyncMock()

        await warning_system.remove_warning.callback(warning_system, ctx, member, 10)

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "от 1 до" in call_args

    @pytest.mark.asyncio
    async def test_remove_warning_success(self, warning_system):
        """Тест успешного удаления предупреждения."""
        guild = MagicMock()
        guild.id = 789012

        member = MagicMock(spec=discord.Member)
        member.id = 123456
        member.mention = "<@123456>"

        ctx = MagicMock()
        ctx.guild = guild
        ctx.send = AsyncMock()

        initial_count = len(warning_system.get_user_warnings(789012, 123456))

        await warning_system.remove_warning.callback(warning_system, ctx, member, 1)

        # Проверяем что предупреждение удалено
        warnings = warning_system.get_user_warnings(789012, 123456)
        assert len(warnings) == initial_count - 1

        ctx.send.assert_called_once()


class TestWarningSystemCleanup:
    """Тесты очистки устаревших предупреждений."""

    @pytest.fixture
    def warning_system(self):
        """Фикстура для создания системы предупреждений."""
        bot = MagicMock()
        repository = MagicMock()
        repository.cleanup_expired = AsyncMock()

        store = MagicMock(spec=WarningsStore)
        config_store = MagicMock(spec=WarningsConfigStore)

        # Создаем предупреждения с разными датами
        old_date = "2026-03-01T00:00:00"
        recent_date = "2026-04-01T00:00:00"

        store.load.return_value = {
            "789012": {
                "123456": [
                    {"reason": "Old warning", "moderator": 111111, "timestamp": old_date},
                    {"reason": "Recent warning", "moderator": 111111, "timestamp": recent_date}
                ]
            }
        }
        config_store.load.return_value = {"punishments": {}}

        system = WarningSystem(bot, repository, store, config_store)
        return system

    @pytest.mark.asyncio
    async def test_cleanup_expired_warnings(self, warning_system):
        """Тест очистки устаревших предупреждений."""
        db = MagicMock()

        await warning_system.cleanup_expired_warnings(db)

        # Проверяем что был вызван cleanup в репозитории
        if warning_system.repository:
            warning_system.repository.cleanup_expired.assert_called_once_with(days=30)


class TestWarningSystemMigration:
    """Тесты миграции в БД."""

    @pytest.fixture
    def warning_system(self):
        """Фикстура для создания системы предупреждений."""
        bot = MagicMock()
        repository = MagicMock()
        repository.migrate_from_json = AsyncMock()

        store = MagicMock(spec=WarningsStore)
        config_store = MagicMock(spec=WarningsConfigStore)

        store.load.return_value = {
            "789012": {
                "123456": [
                    {"reason": "Warning 1", "moderator": 111111, "timestamp": "2026-04-07T00:00:00"}
                ]
            }
        }
        config_store.load.return_value = {"punishments": {}}

        system = WarningSystem(bot, repository, store, config_store)
        return system

    @pytest.mark.asyncio
    async def test_migrate_to_db(self, warning_system):
        """Тест миграции предупреждений в БД."""
        await warning_system.migrate_to_db()

        # Проверяем что был вызван migrate_from_json
        warning_system.repository.migrate_from_json.assert_called_once_with(
            warning_system.warnings
        )

    @pytest.mark.asyncio
    async def test_migrate_to_db_no_repository(self):
        """Тест миграции когда репозиторий не установлен."""
        bot = MagicMock()
        store = MagicMock(spec=WarningsStore)
        config_store = MagicMock(spec=WarningsConfigStore)

        store.load.return_value = {}
        config_store.load.return_value = {"punishments": {}}

        system = WarningSystem(bot, None, store, config_store)

        # Не должно быть ошибки
        await system.migrate_to_db()


class TestWarningSystemPunishments:
    """Тесты автоматических наказаний."""

    @pytest.fixture
    def warning_system(self):
        """Фикстура для создания системы предупреждений."""
        bot = MagicMock()
        repository = MagicMock()
        repository.add_warning = AsyncMock()

        store = MagicMock(spec=WarningsStore)
        config_store = MagicMock(spec=WarningsConfigStore)

        store.load.return_value = {}
        config_store.load.return_value = {
            "punishments": {
                "2": "mute_1h",
                "3": "kick"
            }
        }

        system = WarningSystem(bot, repository, store, config_store)
        return system

    @pytest.mark.asyncio
    async def test_punishment_mute_1h(self, warning_system):
        """Тест автоматического мута на 1 час."""
        guild = MagicMock()
        guild.id = 789012
        guild.get_member = MagicMock(return_value=None)

        member = MagicMock(spec=discord.Member)
        member.bot = False
        member.id = 123456
        member.guild = guild
        member.mention = "<@123456>"
        member.top_role = MagicMock(position=5)
        member.timeout = AsyncMock()

        user = MagicMock()
        user.id = 111111
        user.mention = "<@111111>"
        user.top_role = MagicMock(position=10)

        member.top_role.__ge__ = lambda self, other: self.position >= other.position
        user.top_role.__ge__ = lambda self, other: self.position >= other.position

        ctx = MagicMock()
        ctx.guild = guild
        ctx.user = user
        ctx.send = AsyncMock()
        ctx.followup = MagicMock()
        ctx.followup.send = AsyncMock()

        # Добавляем первое предупреждение
        await warning_system.add_warning.callback(warning_system, ctx, member, "Warning 1")

        # Добавляем второе предупреждение - должен сработать мут
        await warning_system.add_warning.callback(warning_system, ctx, member, "Warning 2")

        # Проверяем что был вызван timeout
        member.timeout.assert_called_once()
