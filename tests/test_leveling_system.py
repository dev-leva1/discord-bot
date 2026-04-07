"""Тесты для системы уровней."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from leveling_system import LevelingSystem
from infrastructure.config import LevelsStore


class TestLevelingSystemCalculations:
    """Тесты расчетов XP и уровней."""

    @pytest.fixture
    def leveling_system(self):
        """Фикстура для создания системы уровней."""
        bot = MagicMock()
        repository = MagicMock()
        store = MagicMock(spec=LevelsStore)
        store.load.return_value = {}

        system = LevelingSystem(bot, repository, store)
        system.use_db = False  # Отключаем БД для unit тестов
        return system

    def test_xp_for_level_1(self, leveling_system):
        """Тест расчета XP для уровня 1."""
        xp = leveling_system.get_xp_for_level(1)
        assert xp == 155  # 5*(1^2) + 50*1 + 100

    def test_xp_for_level_5(self, leveling_system):
        """Тест расчета XP для уровня 5."""
        xp = leveling_system.get_xp_for_level(5)
        assert xp == 475  # 5*(5^2) + 50*5 + 100

    def test_xp_for_level_10(self, leveling_system):
        """Тест расчета XP для уровня 10."""
        xp = leveling_system.get_xp_for_level(10)
        assert xp == 1100  # 5*(10^2) + 50*10 + 100

    def test_xp_for_level_0(self, leveling_system):
        """Тест расчета XP для уровня 0."""
        xp = leveling_system.get_xp_for_level(0)
        assert xp == 100

    def test_level_for_zero_xp(self, leveling_system):
        """Тест определения уровня при 0 XP."""
        level = leveling_system.get_level_for_xp(0)
        assert level == 0

    def test_level_for_small_xp(self, leveling_system):
        """Тест определения уровня при малом XP."""
        level = leveling_system.get_level_for_xp(50)
        assert level == 0  # Недостаточно для уровня 1

    def test_level_for_exact_threshold(self, leveling_system):
        """Тест определения уровня при точном пороге."""
        xp_for_level_1 = leveling_system.get_xp_for_level(0)
        level = leveling_system.get_level_for_xp(xp_for_level_1)
        assert level == 1

    def test_level_for_high_xp(self, leveling_system):
        """Тест определения уровня при большом XP."""
        # Рассчитываем XP для достижения уровня 5
        total_xp = sum(leveling_system.get_xp_for_level(i) for i in range(5))
        level = leveling_system.get_level_for_xp(total_xp)
        assert level == 5

    def test_xp_progression_is_increasing(self, leveling_system):
        """Тест что XP для каждого уровня увеличивается."""
        for level in range(1, 20):
            xp_current = leveling_system.get_xp_for_level(level)
            xp_previous = leveling_system.get_xp_for_level(level - 1)
            assert xp_current > xp_previous


class TestLevelingSystemCooldowns:
    """Тесты системы кулдаунов."""

    @pytest.fixture
    def leveling_system(self):
        """Фикстура для создания системы уровней."""
        bot = MagicMock()
        repository = MagicMock()
        store = MagicMock(spec=LevelsStore)
        store.load.return_value = {}

        system = LevelingSystem(bot, repository, store)
        system.use_db = False
        return system

    def test_cooldown_cleanup_not_triggered_early(self, leveling_system):
        """Тест что очистка не срабатывает раньше времени."""
        # Добавляем кулдауны
        leveling_system.xp_cooldowns["user_1"] = datetime.now()
        leveling_system.xp_cooldowns["user_2"] = datetime.now()

        # Вызываем очистку сразу
        leveling_system._cleanup_old_cooldowns()

        # Кулдауны не должны быть удалены
        assert len(leveling_system.xp_cooldowns) == 2

    def test_cooldown_cleanup_removes_old_entries(self, leveling_system):
        """Тест что очистка удаляет старые записи."""
        # Добавляем старые кулдауны
        old_time = datetime.now() - timedelta(minutes=5)
        leveling_system.xp_cooldowns["user_1"] = old_time
        leveling_system.xp_cooldowns["user_2"] = old_time

        # Устанавливаем время последней очистки в прошлое
        leveling_system._last_cooldown_cleanup = datetime.now() - timedelta(minutes=6)

        # Вызываем очистку
        leveling_system._cleanup_old_cooldowns()

        # Старые кулдауны должны быть удалены
        assert len(leveling_system.xp_cooldowns) == 0

    def test_cooldown_cleanup_keeps_recent_entries(self, leveling_system):
        """Тест что очистка сохраняет свежие записи."""
        # Добавляем свежий кулдаун
        leveling_system.xp_cooldowns["user_1"] = datetime.now()

        # Устанавливаем время последней очистки в прошлое
        leveling_system._last_cooldown_cleanup = datetime.now() - timedelta(minutes=6)

        # Вызываем очистку
        leveling_system._cleanup_old_cooldowns()

        # Свежий кулдаун должен остаться
        assert len(leveling_system.xp_cooldowns) == 1

    def test_cooldown_cleanup_mixed_entries(self, leveling_system):
        """Тест очистки со смешанными записями."""
        now = datetime.now()
        old_time = now - timedelta(minutes=5)

        leveling_system.xp_cooldowns["user_old_1"] = old_time
        leveling_system.xp_cooldowns["user_old_2"] = old_time
        leveling_system.xp_cooldowns["user_new_1"] = now
        leveling_system.xp_cooldowns["user_new_2"] = now

        leveling_system._last_cooldown_cleanup = now - timedelta(minutes=6)

        leveling_system._cleanup_old_cooldowns()

        # Должны остаться только свежие
        assert len(leveling_system.xp_cooldowns) == 2
        assert "user_new_1" in leveling_system.xp_cooldowns
        assert "user_new_2" in leveling_system.xp_cooldowns


class TestLevelingSystemMessageProcessing:
    """Тесты обработки сообщений."""

    @pytest.fixture
    def leveling_system(self):
        """Фикстура для создания системы уровней."""
        bot = MagicMock()
        repository = MagicMock()
        repository.get_user = AsyncMock(return_value=None)
        repository.get_user_level_xp = AsyncMock(return_value=None)
        repository.create_user = AsyncMock()
        repository.update_user = AsyncMock()
        repository.ensure_last_message_time_column = AsyncMock()

        store = MagicMock(spec=LevelsStore)
        store.load.return_value = {}

        system = LevelingSystem(bot, repository, store)
        system.use_db = True
        system._schema_checked = True  # Пропускаем проверку схемы
        return system

    @pytest.mark.asyncio
    async def test_process_message_from_bot(self, leveling_system):
        """Тест что сообщения от ботов игнорируются."""
        message = MagicMock(spec=discord.Message)
        message.author.bot = True
        message.guild = MagicMock()

        leveled_up, new_level = await leveling_system.process_message(message)

        assert leveled_up is False
        assert new_level is None

    @pytest.mark.asyncio
    async def test_process_message_no_guild(self, leveling_system):
        """Тест что DM сообщения игнорируются."""
        message = MagicMock(spec=discord.Message)
        message.author.bot = False
        message.guild = None

        leveled_up, new_level = await leveling_system.process_message(message)

        assert leveled_up is False
        assert new_level is None

    @pytest.mark.asyncio
    async def test_process_message_on_cooldown(self, leveling_system):
        """Тест что сообщения на кулдауне не дают XP."""
        message = MagicMock(spec=discord.Message)
        message.author.bot = False
        message.author.id = 123456
        message.guild = MagicMock()
        message.guild.id = 789012

        # Устанавливаем кулдаун
        cooldown_key = f"{message.author.id}_{message.guild.id}"
        leveling_system.xp_cooldowns[cooldown_key] = datetime.now()

        leveled_up, new_level = await leveling_system.process_message(message)

        assert leveled_up is False
        assert new_level is None

    @pytest.mark.asyncio
    async def test_process_message_creates_new_user(self, leveling_system):
        """Тест создания нового пользователя."""
        # Создаем правильные моки для Member
        guild = MagicMock()
        guild.id = 789012

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 123456
        author.guild = guild

        message = MagicMock(spec=discord.Message)
        message.author = author
        message.guild = guild

        leveling_system.repository.get_user_level_xp = AsyncMock(return_value=None)
        leveling_system.repository.create_user = AsyncMock()

        await leveling_system.process_message(message)

        leveling_system.repository.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_awards_xp(self, leveling_system):
        """Тест начисления XP."""
        # Создаем правильные моки для Member
        guild = MagicMock()
        guild.id = 789012

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 123456
        author.guild = guild

        message = MagicMock(spec=discord.Message)
        message.author = author
        message.guild = guild

        existing_user = {
            "user_id": 123456,
            "guild_id": 789012,
            "xp": 50,
            "level": 0
        }

        leveling_system.repository.get_user_level_xp = AsyncMock(return_value=existing_user)
        leveling_system.repository.update_user = AsyncMock()

        await leveling_system.process_message(message)

        # Проверяем что update был вызван
        leveling_system.repository.update_user.assert_called_once()
        # Проверяем что XP увеличился (3-й аргумент - current_xp)
        call_args = leveling_system.repository.update_user.call_args[0]
        assert call_args[2] > 50  # XP должен увеличиться (50 + 15-25)


class TestLevelingSystemDataManagement:
    """Тесты управления данными."""

    @pytest.fixture
    def leveling_system(self):
        """Фикстура для создания системы уровней."""
        bot = MagicMock()
        repository = MagicMock()
        store = MagicMock(spec=LevelsStore)
        store.load.return_value = {"test": "data"}

        system = LevelingSystem(bot, repository, store)
        return system

    def test_load_data(self, leveling_system):
        """Тест загрузки данных."""
        assert leveling_system.data == {"test": "data"}

    def test_save_data_when_not_using_db(self, leveling_system):
        """Тест сохранения данных когда БД не используется."""
        leveling_system.use_db = False
        leveling_system.data = {"new": "data"}

        leveling_system.save_data()

        leveling_system.store.save.assert_called_once_with({"new": "data"})

    def test_save_data_when_using_db(self, leveling_system):
        """Тест что данные не сохраняются в файл при использовании БД."""
        leveling_system.use_db = True
        leveling_system.data = {"new": "data"}

        leveling_system.save_data()

        # save не должен быть вызван
        leveling_system.store.save.assert_not_called()
