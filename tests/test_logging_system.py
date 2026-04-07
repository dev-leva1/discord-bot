"""Тесты для системы логирования."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from pathlib import Path
import json

from logging_system import LoggingSystem


class TestLoggingSystemConfiguration:
    """Тесты конфигурации системы логирования."""

    @pytest.fixture
    def logging_system(self, tmp_path):
        """Фикстура для создания системы логирования."""
        bot = MagicMock()
        system = LoggingSystem(bot)
        system.config_file = tmp_path / "logging_config.json"
        system.config = {}
        return system

    def test_load_config_creates_empty_if_not_exists(self, logging_system):
        """Тест создания пустой конфигурации если файл не существует."""
        logging_system.load_config()
        assert logging_system.config == {}

    def test_load_config_reads_existing_file(self, logging_system):
        """Тест чтения существующего файла конфигурации."""
        test_config = {"123456": 789012}
        logging_system.config_file.write_text(json.dumps(test_config))

        logging_system.load_config()

        assert logging_system.config == test_config

    def test_save_config_writes_to_file(self, logging_system):
        """Тест сохранения конфигурации в файл."""
        logging_system.config = {"123456": 789012}

        logging_system.save_config()

        saved_data = json.loads(logging_system.config_file.read_text())
        assert saved_data == {"123456": 789012}


class TestLoggingSystemSetup:
    """Тесты настройки канала логов."""

    @pytest.fixture
    def logging_system(self, tmp_path):
        """Фикстура для создания системы логирования."""
        bot = MagicMock()
        bot.tree = MagicMock()
        system = LoggingSystem(bot)
        system.config_file = tmp_path / "logging_config.json"
        system.config = {}
        return system

    @pytest.mark.asyncio
    async def test_setup_registers_command(self, logging_system):
        """Тест регистрации команды setlogs."""
        await logging_system.setup()

        logging_system.bot.tree.command.assert_called_once()


class TestLoggingSystemLogEvent:
    """Тесты базового метода логирования событий."""

    @pytest.fixture
    def logging_system(self, tmp_path):
        """Фикстура для создания системы логирования."""
        bot = MagicMock()
        system = LoggingSystem(bot)
        system.config_file = tmp_path / "logging_config.json"
        system.config = {}
        return system

    @pytest.mark.asyncio
    async def test_log_event_no_config(self, logging_system):
        """Тест что событие не логируется если канал не настроен."""
        guild = MagicMock()
        guild.id = 123456

        await logging_system.log_event(guild, "Test", "Description")

        guild.get_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_event_channel_not_found(self, logging_system):
        """Тест что событие не логируется если канал не найден."""
        guild = MagicMock()
        guild.id = 123456
        guild.get_channel = MagicMock(return_value=None)

        logging_system.config = {"123456": 789012}

        await logging_system.log_event(guild, "Test", "Description")

        guild.get_channel.assert_called_once_with(789012)

    @pytest.mark.asyncio
    async def test_log_event_sends_embed(self, logging_system):
        """Тест отправки embed сообщения."""
        guild = MagicMock()
        guild.id = 123456

        channel = AsyncMock()
        guild.get_channel = MagicMock(return_value=channel)

        logging_system.config = {"123456": 789012}

        await logging_system.log_event(
            guild,
            "Test Title",
            "Test Description",
            discord.Color.blue()
        )

        channel.send.assert_called_once()
        call_args = channel.send.call_args
        assert "embed" in call_args.kwargs
        embed = call_args.kwargs["embed"]
        assert embed.title == "Test Title"
        assert embed.description == "Test Description"

    @pytest.mark.asyncio
    async def test_log_event_with_fields(self, logging_system):
        """Тест добавления полей в embed."""
        guild = MagicMock()
        guild.id = 123456

        channel = AsyncMock()
        guild.get_channel = MagicMock(return_value=channel)

        logging_system.config = {"123456": 789012}

        fields = [("Field 1", "Value 1", False), ("Field 2", "Value 2", True)]

        await logging_system.log_event(
            guild,
            "Test",
            "Description",
            fields=fields
        )

        channel.send.assert_called_once()
        call_args = channel.send.call_args
        embed = call_args.kwargs["embed"]
        assert len(embed.fields) == 2

    @pytest.mark.asyncio
    async def test_log_event_with_author(self, logging_system):
        """Тест добавления автора в footer."""
        guild = MagicMock()
        guild.id = 123456

        channel = AsyncMock()
        guild.get_channel = MagicMock(return_value=channel)

        logging_system.config = {"123456": 789012}

        author = MagicMock()
        author.__str__ = MagicMock(return_value="TestUser")

        await logging_system.log_event(
            guild,
            "Test",
            "Description",
            author=author
        )

        channel.send.assert_called_once()
        call_args = channel.send.call_args
        embed = call_args.kwargs["embed"]
        assert "TestUser" in embed.footer.text

    @pytest.mark.asyncio
    async def test_log_event_handles_http_exception(self, logging_system):
        """Тест обработки HTTPException при отправке."""
        guild = MagicMock()
        guild.id = 123456

        channel = AsyncMock()
        channel.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "Error"))
        guild.get_channel = MagicMock(return_value=channel)

        logging_system.config = {"123456": 789012}

        # Не должно быть исключения
        await logging_system.log_event(guild, "Test", "Description")


class TestLoggingSystemMessageEvents:
    """Тесты логирования событий сообщений."""

    @pytest.fixture
    def logging_system(self, tmp_path):
        """Фикстура для создания системы логирования."""
        bot = MagicMock()
        system = LoggingSystem(bot)
        system.config_file = tmp_path / "logging_config.json"
        system.config = {"123456": 789012}
        system.log_event = AsyncMock()
        return system

    @pytest.mark.asyncio
    async def test_log_message_delete(self, logging_system):
        """Тест логирования удаления сообщения."""
        guild = MagicMock()
        guild.id = 123456

        channel = MagicMock()
        channel.mention = "#test-channel"

        author = MagicMock()
        author.mention = "@user"

        message = MagicMock(spec=discord.Message)
        message.guild = guild
        message.channel = channel
        message.author = author
        message.content = "Test message"

        await logging_system.log_message_delete(message)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "удалено" in call_args[1].lower()
        assert "Test message" in call_args[2]

    @pytest.mark.asyncio
    async def test_log_message_delete_no_guild(self, logging_system):
        """Тест что DM сообщения не логируются."""
        message = MagicMock(spec=discord.Message)
        message.guild = None

        await logging_system.log_message_delete(message)

        logging_system.log_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_message_edit(self, logging_system):
        """Тест логирования редактирования сообщения."""
        guild = MagicMock()
        guild.id = 123456

        channel = MagicMock()
        channel.mention = "#test-channel"

        author = MagicMock()
        author.mention = "@user"

        before = MagicMock(spec=discord.Message)
        before.guild = guild
        before.channel = channel
        before.author = author
        before.content = "Old content"

        after = MagicMock(spec=discord.Message)
        after.guild = guild
        after.channel = channel
        after.author = author
        after.content = "New content"

        await logging_system.log_message_edit(before, after)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args
        assert "изменено" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_log_message_edit_same_content(self, logging_system):
        """Тест что не логируется если контент не изменился."""
        guild = MagicMock()
        guild.id = 123456

        before = MagicMock(spec=discord.Message)
        before.guild = guild
        before.content = "Same content"

        after = MagicMock(spec=discord.Message)
        after.guild = guild
        after.content = "Same content"

        await logging_system.log_message_edit(before, after)

        logging_system.log_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_message_edit_no_guild(self, logging_system):
        """Тест что DM сообщения не логируются."""
        before = MagicMock(spec=discord.Message)
        before.guild = None
        before.content = "Old"

        after = MagicMock(spec=discord.Message)
        after.guild = None
        after.content = "New"

        await logging_system.log_message_edit(before, after)

        logging_system.log_event.assert_not_called()


class TestLoggingSystemMemberEvents:
    """Тесты логирования событий участников."""

    @pytest.fixture
    def logging_system(self, tmp_path):
        """Фикстура для создания системы логирования."""
        bot = MagicMock()
        system = LoggingSystem(bot)
        system.config_file = tmp_path / "logging_config.json"
        system.config = {"123456": 789012}
        system.log_event = AsyncMock()
        return system

    @pytest.mark.asyncio
    async def test_log_member_join(self, logging_system):
        """Тест логирования присоединения участника."""
        guild = MagicMock()
        guild.id = 123456

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.mention = "@newuser"
        member.id = 789012

        await logging_system.log_member_join(member)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "присоединился" in call_args[1].lower()
        assert str(member.id) in call_args[2]

    @pytest.mark.asyncio
    async def test_log_member_remove(self, logging_system):
        """Тест логирования выхода участника."""
        guild = MagicMock()
        guild.id = 123456

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.__str__ = MagicMock(return_value="User#1234")
        member.id = 789012

        await logging_system.log_member_remove(member)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "покинул" in call_args[1].lower()

    @pytest.mark.asyncio
    async def test_log_member_update_roles_added(self, logging_system):
        """Тест логирования добавления ролей."""
        guild = MagicMock()
        guild.id = 123456

        # Создаем async generator для audit_logs
        async def mock_audit_logs(*args, **kwargs):
            return
            yield  # Пустой генератор

        guild.audit_logs = mock_audit_logs

        role1 = MagicMock()
        role1.mention = "@Role1"

        role2 = MagicMock()
        role2.mention = "@Role2"

        before = MagicMock(spec=discord.Member)
        before.guild = guild
        before.roles = [role1]

        after = MagicMock(spec=discord.Member)
        after.guild = guild
        after.mention = "@user"
        after.id = 789012
        after.roles = [role1, role2]

        await logging_system.log_member_update(before, after)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "роли" in call_args[1].lower()
        assert "добавлены" in call_args[2].lower()

    @pytest.mark.asyncio
    async def test_log_member_update_roles_removed(self, logging_system):
        """Тест логирования удаления ролей."""
        guild = MagicMock()
        guild.id = 123456

        # Создаем async generator для audit_logs
        async def mock_audit_logs(*args, **kwargs):
            return
            yield  # Пустой генератор

        guild.audit_logs = mock_audit_logs

        role1 = MagicMock()
        role1.mention = "@Role1"

        role2 = MagicMock()
        role2.mention = "@Role2"

        before = MagicMock(spec=discord.Member)
        before.guild = guild
        before.roles = [role1, role2]

        after = MagicMock(spec=discord.Member)
        after.guild = guild
        after.mention = "@user"
        after.id = 789012
        after.roles = [role1]

        await logging_system.log_member_update(before, after)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "удалены" in call_args[2].lower()

    @pytest.mark.asyncio
    async def test_log_member_update_no_role_changes(self, logging_system):
        """Тест что не логируется если роли не изменились."""
        guild = MagicMock()
        guild.id = 123456

        role1 = MagicMock()

        before = MagicMock(spec=discord.Member)
        before.guild = guild
        before.roles = [role1]

        after = MagicMock(spec=discord.Member)
        after.guild = guild
        after.roles = [role1]

        await logging_system.log_member_update(before, after)

        logging_system.log_event.assert_not_called()


class TestLoggingSystemVoiceEvents:
    """Тесты логирования голосовых событий."""

    @pytest.fixture
    def logging_system(self, tmp_path):
        """Фикстура для создания системы логирования."""
        bot = MagicMock()
        system = LoggingSystem(bot)
        system.config_file = tmp_path / "logging_config.json"
        system.config = {"123456": 789012}
        system.log_event = AsyncMock()
        return system

    @pytest.mark.asyncio
    async def test_log_voice_join(self, logging_system):
        """Тест логирования подключения к голосовому каналу."""
        guild = MagicMock()
        guild.id = 123456

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.mention = "@user"

        channel = MagicMock()
        channel.name = "Voice Channel"

        before = MagicMock()
        before.channel = None

        after = MagicMock()
        after.channel = channel

        await logging_system.log_voice_state_update(member, before, after)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "подключение" in call_args[1].lower()
        assert "Voice Channel" in call_args[2]

    @pytest.mark.asyncio
    async def test_log_voice_leave(self, logging_system):
        """Тест логирования отключения от голосового канала."""
        guild = MagicMock()
        guild.id = 123456

        member = MagicMock(spec=discord.Member)
        member.guild = guild
        member.mention = "@user"

        channel = MagicMock()
        channel.name = "Voice Channel"

        before = MagicMock()
        before.channel = channel

        after = MagicMock()
        after.channel = None

        await logging_system.log_voice_state_update(member, before, after)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "отключение" in call_args[1].lower()

    @pytest.mark.asyncio
    async def test_log_voice_no_channel_change(self, logging_system):
        """Тест что не логируется если канал не изменился."""
        guild = MagicMock()
        guild.id = 123456

        member = MagicMock(spec=discord.Member)
        member.guild = guild

        channel = MagicMock()

        before = MagicMock()
        before.channel = channel

        after = MagicMock()
        after.channel = channel

        await logging_system.log_voice_state_update(member, before, after)

        logging_system.log_event.assert_not_called()


class TestLoggingSystemModerationEvents:
    """Тесты логирования событий модерации."""

    @pytest.fixture
    def logging_system(self, tmp_path):
        """Фикстура для создания системы логирования."""
        bot = MagicMock()
        system = LoggingSystem(bot)
        system.config_file = tmp_path / "logging_config.json"
        system.config = {"123456": 789012}
        system.log_event = AsyncMock()
        return system

    @pytest.mark.asyncio
    async def test_log_ban_with_audit_log(self, logging_system):
        """Тест логирования бана с информацией из audit log."""
        guild = MagicMock()
        guild.id = 123456

        moderator = MagicMock()
        moderator.__str__ = MagicMock(return_value="Moderator")

        user = MagicMock()
        user.id = 789012
        user.__str__ = MagicMock(return_value="BannedUser")

        audit_entry = MagicMock()
        audit_entry.target = user
        audit_entry.user = moderator
        audit_entry.reason = "Spam"

        async def mock_audit_logs(*args, **kwargs):
            yield audit_entry

        guild.audit_logs = mock_audit_logs

        await logging_system.log_ban(guild, user)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "забанен" in call_args[1].lower()
        assert "Spam" in call_args[2]

    @pytest.mark.asyncio
    async def test_log_ban_no_audit_log(self, logging_system):
        """Тест логирования бана без audit log."""
        guild = MagicMock()
        guild.id = 123456

        async def mock_audit_logs(*args, **kwargs):
            return
            yield

        guild.audit_logs = mock_audit_logs

        user = MagicMock()
        user.id = 789012
        user.__str__ = MagicMock(return_value="BannedUser")

        await logging_system.log_ban(guild, user)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "не указана" in call_args[2].lower()

    @pytest.mark.asyncio
    async def test_log_ban_forbidden(self, logging_system):
        """Тест логирования бана когда нет доступа к audit log."""
        guild = MagicMock()
        guild.id = 123456

        async def mock_audit_logs(*args, **kwargs):
            raise discord.Forbidden(MagicMock(), "No access")
            yield

        guild.audit_logs = mock_audit_logs

        user = MagicMock()
        user.id = 789012
        user.__str__ = MagicMock(return_value="BannedUser")

        await logging_system.log_ban(guild, user)

        logging_system.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_unban_with_audit_log(self, logging_system):
        """Тест логирования разбана с информацией из audit log."""
        guild = MagicMock()
        guild.id = 123456

        moderator = MagicMock()
        moderator.__str__ = MagicMock(return_value="Moderator")

        user = MagicMock()
        user.id = 789012
        user.__str__ = MagicMock(return_value="UnbannedUser")

        audit_entry = MagicMock()
        audit_entry.target = user
        audit_entry.user = moderator

        async def mock_audit_logs(*args, **kwargs):
            yield audit_entry

        guild.audit_logs = mock_audit_logs

        await logging_system.log_unban(guild, user)

        logging_system.log_event.assert_called_once()
        call_args = logging_system.log_event.call_args[0]
        assert "разбанен" in call_args[1].lower()

    @pytest.mark.asyncio
    async def test_log_unban_no_audit_log(self, logging_system):
        """Тест логирования разбана без audit log."""
        guild = MagicMock()
        guild.id = 123456

        async def mock_audit_logs(*args, **kwargs):
            return
            yield

        guild.audit_logs = mock_audit_logs

        user = MagicMock()
        user.id = 789012
        user.__str__ = MagicMock(return_value="UnbannedUser")

        await logging_system.log_unban(guild, user)

        logging_system.log_event.assert_called_once()
