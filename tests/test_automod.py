"""Тесты для системы автомодерации."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from automod import AutoMod
from infrastructure.config import AutomodConfigStore


class TestAutoModConfiguration:
    """Тесты конфигурации автомодерации."""

    @pytest.fixture
    def automod(self):
        """Фикстура для создания системы автомодерации."""
        bot = MagicMock()
        store = MagicMock(spec=AutomodConfigStore)
        store.load.return_value = {
            "banned_words": ["badword1", "badword2"],
            "spam_threshold": 5,
            "spam_interval": 5,
            "max_mentions": 5,
            "max_warnings": 3,
            "mute_duration": "1h"
        }

        system = AutoMod(bot, store)
        return system

    def test_load_config(self, automod):
        """Тест загрузки конфигурации."""
        assert "banned_words" in automod.config
        assert "spam_threshold" in automod.config
        assert automod.config["spam_threshold"] == 5

    def test_save_config(self, automod):
        """Тест сохранения конфигурации."""
        automod.config["spam_threshold"] = 10
        automod.save_config()

        automod.store.save.assert_called_once_with(automod.config)

    def test_default_config_values(self, automod):
        """Тест значений конфигурации по умолчанию."""
        assert automod.config["max_warnings"] == 3
        assert automod.config["mute_duration"] == "1h"
        assert isinstance(automod.config["banned_words"], list)


class TestAutoModBannedWords:
    """Тесты фильтра запрещенных слов."""

    @pytest.fixture
    def automod(self):
        """Фикстура для создания системы автомодерации."""
        bot = MagicMock()
        store = MagicMock(spec=AutomodConfigStore)
        store.load.return_value = {
            "banned_words": ["badword", "offensive"],
            "spam_threshold": 5,
            "spam_interval": 5,
            "max_mentions": 5,
            "max_warnings": 3,
            "mute_duration": "1h"
        }

        system = AutoMod(bot, store)
        return system

    @pytest.mark.asyncio
    async def test_message_with_banned_word(self, automod):
        """Тест сообщения с запрещенным словом."""
        guild = MagicMock()
        guild.id = 123456

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 789012
        author.mention = "<@789012>"

        message = MagicMock(spec=discord.Message)
        message.content = "This contains badword in it"
        message.author = author
        message.guild = guild
        message.delete = AsyncMock()

        automod.add_warning = AsyncMock()

        result = await automod.check_message(message)

        assert result is False
        message.delete.assert_called_once()
        automod.add_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_without_banned_word(self, automod):
        """Тест сообщения без запрещенных слов."""
        guild = MagicMock()
        guild.id = 123456

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 789012

        message = MagicMock(spec=discord.Message)
        message.content = "This is a clean message"
        message.author = author
        message.guild = guild
        message.mentions = []

        result = await automod.check_message(message)

        assert result is True

    @pytest.mark.asyncio
    async def test_case_insensitive_banned_word(self, automod):
        """Тест регистронезависимости запрещенных слов."""
        guild = MagicMock()
        guild.id = 123456

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 789012
        author.mention = "<@789012>"

        message = MagicMock(spec=discord.Message)
        message.content = "This contains BADWORD in caps"
        message.author = author
        message.guild = guild
        message.delete = AsyncMock()

        automod.add_warning = AsyncMock()

        result = await automod.check_message(message)

        assert result is False
        message.delete.assert_called_once()


class TestAutoModSpamDetection:
    """Тесты анти-спам системы."""

    @pytest.fixture
    def automod(self):
        """Фикстура для создания системы автомодерации."""
        bot = MagicMock()
        store = MagicMock(spec=AutomodConfigStore)
        store.load.return_value = {
            "banned_words": [],
            "spam_threshold": 3,
            "spam_interval": 5,
            "max_mentions": 5,
            "max_warnings": 3,
            "mute_duration": "1h"
        }

        system = AutoMod(bot, store)
        return system

    @pytest.mark.asyncio
    async def test_spam_detection_triggers(self, automod):
        """Тест срабатывания анти-спама."""
        guild = MagicMock()
        guild.id = 123456

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 789012
        author.mention = "<@789012>"

        channel = MagicMock()
        channel.purge = AsyncMock()

        message = MagicMock(spec=discord.Message)
        message.content = "spam message"
        message.author = author
        message.guild = guild
        message.channel = channel
        message.mentions = []

        automod.add_warning = AsyncMock()

        # Отправляем 4 сообщения быстро (порог = 3)
        for _ in range(4):
            result = await automod.check_message(message)

        # Последнее сообщение должно быть заблокировано
        assert result is False
        channel.purge.assert_called_once()
        automod.add_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_spam_counter_resets_after_interval(self, automod):
        """Тест сброса счетчика спама после интервала."""
        guild = MagicMock()
        guild.id = 123456

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 789012

        message = MagicMock(spec=discord.Message)
        message.content = "message"
        message.author = author
        message.guild = guild
        message.mentions = []

        # Отправляем 2 сообщения
        await automod.check_message(message)
        await automod.check_message(message)

        user_key = f"{author.id}_{guild.id}"
        assert len(automod.spam_counter[user_key]) == 2

        # Имитируем прошедшее время
        old_time = datetime.now() - timedelta(seconds=10)
        automod.spam_counter[user_key] = [old_time, old_time]

        # Отправляем новое сообщение
        await automod.check_message(message)

        # Старые сообщения должны быть удалены
        assert len(automod.spam_counter[user_key]) == 1


class TestAutoModMentions:
    """Тесты защиты от массовых упоминаний."""

    @pytest.fixture
    def automod(self):
        """Фикстура для создания системы автомодерации."""
        bot = MagicMock()
        store = MagicMock(spec=AutomodConfigStore)
        store.load.return_value = {
            "banned_words": [],
            "spam_threshold": 5,
            "spam_interval": 5,
            "max_mentions": 3,
            "max_warnings": 3,
            "mute_duration": "1h"
        }

        system = AutoMod(bot, store)
        return system

    @pytest.mark.asyncio
    async def test_too_many_mentions(self, automod):
        """Тест блокировки массовых упоминаний."""
        guild = MagicMock()
        guild.id = 123456

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 789012
        author.mention = "<@789012>"

        # Создаем 4 упоминания (порог = 3)
        mentions = [MagicMock() for _ in range(4)]

        message = MagicMock(spec=discord.Message)
        message.content = "spam mentions"
        message.author = author
        message.guild = guild
        message.mentions = mentions
        message.delete = AsyncMock()

        automod.add_warning = AsyncMock()

        result = await automod.check_message(message)

        assert result is False
        message.delete.assert_called_once()
        automod.add_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_acceptable_mentions(self, automod):
        """Тест допустимого количества упоминаний."""
        guild = MagicMock()
        guild.id = 123456

        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.id = 789012

        # Создаем 2 упоминания (порог = 3)
        mentions = [MagicMock() for _ in range(2)]

        message = MagicMock(spec=discord.Message)
        message.content = "normal mentions"
        message.author = author
        message.guild = guild
        message.mentions = mentions

        result = await automod.check_message(message)

        assert result is True


class TestAutoModWarnings:
    """Тесты системы предупреждений."""

    @pytest.fixture
    def automod(self):
        """Фикстура для создания системы автомодерации."""
        bot = MagicMock()
        store = MagicMock(spec=AutomodConfigStore)
        store.load.return_value = {
            "banned_words": [],
            "spam_threshold": 5,
            "spam_interval": 5,
            "max_mentions": 5,
            "max_warnings": 3,
            "mute_duration": "1h"
        }

        system = AutoMod(bot, store)
        return system

    @pytest.mark.asyncio
    async def test_add_warning_increments_counter(self, automod):
        """Тест увеличения счетчика предупреждений."""
        guild = MagicMock()
        guild.id = 123456

        member = MagicMock(spec=discord.Member)
        member.id = 789012
        member.mention = "<@789012>"
        member.guild = guild
        member.send = AsyncMock()

        await automod.add_warning(member, "Test reason")

        user_key = f"{member.id}_{guild.id}"
        assert automod.warning_counter[user_key] == 1

    @pytest.mark.asyncio
    async def test_max_warnings_triggers_mute(self, automod):
        """Тест автоматического мута при достижении лимита."""
        guild = MagicMock()
        guild.id = 123456

        member = MagicMock(spec=discord.Member)
        member.id = 789012
        member.mention = "<@789012>"
        member.guild = guild
        member.send = AsyncMock()
        member.timeout = AsyncMock()

        user_key = f"{member.id}_{guild.id}"
        automod.warning_counter[user_key] = 2  # Уже 2 предупреждения

        await automod.add_warning(member, "Third warning")

        # Должен быть вызван мут
        member.timeout.assert_called_once()
        # Счетчик должен сброситься
        assert automod.warning_counter[user_key] == 0


class TestAutoModCleanup:
    """Тесты очистки памяти."""

    @pytest.fixture
    def automod(self):
        """Фикстура для создания системы автомодерации."""
        bot = MagicMock()
        store = MagicMock(spec=AutomodConfigStore)
        store.load.return_value = {
            "banned_words": [],
            "spam_threshold": 5,
            "spam_interval": 5,
            "max_mentions": 5,
            "max_warnings": 3,
            "mute_duration": "1h"
        }

        system = AutoMod(bot, store)
        return system

    def test_cleanup_not_triggered_early(self, automod):
        """Тест что очистка не срабатывает раньше времени."""
        automod.spam_counter["user_1"] = [datetime.now()]
        automod.warning_counter["user_1"] = 1

        automod._cleanup_old_entries()

        # Данные не должны быть удалены
        assert len(automod.spam_counter) == 1
        assert len(automod.warning_counter) == 1

    def test_cleanup_removes_old_spam_entries(self, automod):
        """Тест удаления старых записей спама."""
        old_time = datetime.now() - timedelta(minutes=10)
        automod.spam_counter["user_1"] = [old_time, old_time]

        # Устанавливаем время последней очистки в прошлое
        automod._last_cleanup = datetime.now() - timedelta(minutes=6)

        automod._cleanup_old_entries()

        # Старые записи должны быть удалены
        assert "user_1" not in automod.spam_counter

    def test_cleanup_keeps_recent_spam_entries(self, automod):
        """Тест сохранения свежих записей спама."""
        recent_time = datetime.now()
        automod.spam_counter["user_1"] = [recent_time]

        automod._last_cleanup = datetime.now() - timedelta(minutes=6)

        automod._cleanup_old_entries()

        # Свежие записи должны остаться
        assert "user_1" in automod.spam_counter

    def test_cleanup_clears_warnings_after_hour(self, automod):
        """Тест очистки предупреждений после часа."""
        automod.warning_counter["user_1"] = 2
        automod.warning_counter["user_2"] = 1

        # Устанавливаем время последней очистки более часа назад
        automod._last_cleanup = datetime.now() - timedelta(hours=2)

        automod._cleanup_old_entries()

        # Все предупреждения должны быть очищены
        assert len(automod.warning_counter) == 0


class TestAutoModBotMessages:
    """Тесты игнорирования сообщений от ботов."""

    @pytest.fixture
    def automod(self):
        """Фикстура для создания системы автомодерации."""
        bot = MagicMock()
        store = MagicMock(spec=AutomodConfigStore)
        store.load.return_value = {
            "banned_words": ["badword"],
            "spam_threshold": 5,
            "spam_interval": 5,
            "max_mentions": 5,
            "max_warnings": 3,
            "mute_duration": "1h"
        }

        system = AutoMod(bot, store)
        return system

    @pytest.mark.asyncio
    async def test_bot_messages_ignored(self, automod):
        """Тест что сообщения от ботов игнорируются."""
        guild = MagicMock()
        guild.id = 123456

        author = MagicMock()
        author.bot = True

        message = MagicMock(spec=discord.Message)
        message.content = "badword"
        message.author = author
        message.guild = guild

        result = await automod.check_message(message)

        assert result is True

    @pytest.mark.asyncio
    async def test_dm_messages_ignored(self, automod):
        """Тест что DM сообщения игнорируются."""
        author = MagicMock()
        author.bot = False

        message = MagicMock(spec=discord.Message)
        message.content = "badword"
        message.author = author
        message.guild = None

        result = await automod.check_message(message)

        assert result is True
