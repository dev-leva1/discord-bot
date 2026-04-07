"""Тесты для обработчиков событий Discord."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from cogs.events import Events


class TestEventsInitialization:
    """Тесты инициализации Events."""

    @pytest.fixture
    def events_cog(self):
        """Фикстура для создания Events cog."""
        bot = MagicMock()
        return Events(bot)

    def test_events_initialization(self, events_cog):
        """Тест инициализации Events."""
        assert events_cog.bot is not None


class TestEventsOnReady:
    """Тесты события on_ready."""

    @pytest.fixture
    def events_cog(self):
        """Фикстура для создания Events cog."""
        bot = MagicMock()
        bot.user = MagicMock()
        bot.user.__str__ = MagicMock(return_value="TestBot")
        return Events(bot)

    @pytest.mark.asyncio
    async def test_on_ready_logs_message(self, events_cog):
        """Тест логирования при готовности бота."""
        with patch('cogs.events.logger') as mock_logger:
            events_cog.print_commands = AsyncMock()

            await events_cog.on_ready()

            mock_logger.info.assert_called_once()
            events_cog.print_commands.assert_called_once()

    @pytest.mark.asyncio
    async def test_print_commands(self, events_cog):
        """Тест вывода списка команд."""
        with patch('builtins.print') as mock_print:
            await events_cog.print_commands()

            # Проверяем что print был вызван
            assert mock_print.call_count > 0


class TestEventsMessageEvents:
    """Тесты событий сообщений."""

    @pytest.fixture
    def events_cog(self):
        """Фикстура для создания Events cog."""
        bot = MagicMock()
        bot.logging = MagicMock()
        bot.logging.log_message_delete = AsyncMock()
        bot.logging.log_message_edit = AsyncMock()
        return Events(bot)

    @pytest.mark.asyncio
    async def test_on_message_delete(self, events_cog):
        """Тест обработки удаления сообщения."""
        message = MagicMock(spec=discord.Message)

        await events_cog.on_message_delete(message)

        events_cog.bot.logging.log_message_delete.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_on_message_edit(self, events_cog):
        """Тест обработки редактирования сообщения."""
        before = MagicMock(spec=discord.Message)
        after = MagicMock(spec=discord.Message)

        await events_cog.on_message_edit(before, after)

        events_cog.bot.logging.log_message_edit.assert_called_once_with(before, after)


class TestEventsMemberEvents:
    """Тесты событий участников."""

    @pytest.fixture
    def events_cog(self):
        """Фикстура для создания Events cog."""
        bot = MagicMock()
        bot.logging = MagicMock()
        bot.logging.log_member_join = AsyncMock()
        bot.logging.log_member_remove = AsyncMock()
        bot.logging.log_member_update = AsyncMock()
        bot.welcome = MagicMock()
        bot.welcome.send_welcome = AsyncMock()
        return Events(bot)

    @pytest.mark.asyncio
    async def test_on_member_join(self, events_cog):
        """Тест обработки присоединения участника."""
        member = MagicMock(spec=discord.Member)

        await events_cog.on_member_join(member)

        events_cog.bot.logging.log_member_join.assert_called_once_with(member)
        events_cog.bot.welcome.send_welcome.assert_called_once_with(member)

    @pytest.mark.asyncio
    async def test_on_member_remove(self, events_cog):
        """Тест обработки выхода участника."""
        member = MagicMock(spec=discord.Member)

        await events_cog.on_member_remove(member)

        events_cog.bot.logging.log_member_remove.assert_called_once_with(member)

    @pytest.mark.asyncio
    async def test_on_member_update(self, events_cog):
        """Тест обработки обновления участника."""
        before = MagicMock(spec=discord.Member)
        after = MagicMock(spec=discord.Member)

        await events_cog.on_member_update(before, after)

        events_cog.bot.logging.log_member_update.assert_called_once_with(before, after)


class TestEventsVoiceEvents:
    """Тесты голосовых событий."""

    @pytest.fixture
    def events_cog(self):
        """Фикстура для создания Events cog."""
        bot = MagicMock()
        bot.logging = MagicMock()
        bot.logging.log_voice_state_update = AsyncMock()
        return Events(bot)

    @pytest.mark.asyncio
    async def test_on_voice_state_update(self, events_cog):
        """Тест обработки изменения голосового состояния."""
        member = MagicMock(spec=discord.Member)
        before = MagicMock()
        after = MagicMock()

        await events_cog.on_voice_state_update(member, before, after)

        events_cog.bot.logging.log_voice_state_update.assert_called_once_with(
            member, before, after
        )


class TestEventsModerationEvents:
    """Тесты событий модерации."""

    @pytest.fixture
    def events_cog(self):
        """Фикстура для создания Events cog."""
        bot = MagicMock()
        bot.logging = MagicMock()
        bot.logging.log_ban = AsyncMock()
        bot.logging.log_unban = AsyncMock()
        return Events(bot)

    @pytest.mark.asyncio
    async def test_on_member_ban(self, events_cog):
        """Тест обработки бана участника."""
        guild = MagicMock(spec=discord.Guild)
        user = MagicMock(spec=discord.User)

        await events_cog.on_member_ban(guild, user)

        events_cog.bot.logging.log_ban.assert_called_once_with(guild, user)

    @pytest.mark.asyncio
    async def test_on_member_unban(self, events_cog):
        """Тест обработки разбана участника."""
        guild = MagicMock(spec=discord.Guild)
        user = MagicMock(spec=discord.User)

        await events_cog.on_member_unban(guild, user)

        events_cog.bot.logging.log_unban.assert_called_once_with(guild, user)


class TestEventsSetup:
    """Тесты функции setup."""

    @pytest.mark.asyncio
    async def test_setup_adds_cog(self):
        """Тест добавления cog к боту."""
        bot = MagicMock()
        bot.add_cog = AsyncMock()

        from cogs.events import setup
        await setup(bot)

        bot.add_cog.assert_called_once()
        args = bot.add_cog.call_args[0]
        assert isinstance(args[0], Events)
