"""Тесты для системы временных голосовых каналов."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
from pathlib import Path
import json

from temp_voice import TempVoice


class TestTempVoiceConfiguration:
    """Тесты конфигурации временных голосовых каналов."""

    @pytest.fixture
    def temp_voice(self, tmp_path):
        """Фикстура для создания системы временных каналов."""
        bot = MagicMock()
        system = TempVoice(bot)
        system.config_path = tmp_path / "voice_config.json"
        return system

    def test_load_config_creates_default_if_not_exists(self, temp_voice):
        """Тест создания конфигурации по умолчанию."""
        config = temp_voice.load_config()

        assert "creation_channel" in config
        assert "temp_category" in config
        assert config["creation_channel"] is None
        assert config["temp_category"] is None

    def test_load_config_reads_existing_file(self, temp_voice):
        """Тест чтения существующего файла конфигурации."""
        test_config = {"creation_channel": 123456, "temp_category": 789012}
        temp_voice.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_voice.config_path.write_text(json.dumps(test_config))

        config = temp_voice.load_config()

        assert config == test_config

    def test_save_config_writes_to_file(self, temp_voice):
        """Тест сохранения конфигурации в файл."""
        temp_voice.voice_config = {"creation_channel": 123456, "temp_category": 789012}

        temp_voice.save_config()

        saved_data = json.loads(temp_voice.config_path.read_text())
        assert saved_data == temp_voice.voice_config

    def test_initialization(self, temp_voice):
        """Тест инициализации системы."""
        assert temp_voice.temp_channels == {}
        assert temp_voice.voice_config is not None


class TestTempVoiceSetup:
    """Тесты настройки системы временных каналов."""

    @pytest.fixture
    def temp_voice(self, tmp_path):
        """Фикстура для создания системы временных каналов."""
        bot = MagicMock()
        system = TempVoice(bot)
        system.config_path = tmp_path / "voice_config.json"
        system.voice_config = {}
        return system

    @pytest.mark.asyncio
    async def test_setup_voice_creates_channel(self, temp_voice):
        """Тест создания канала для создания временных каналов."""
        guild = MagicMock()
        guild.create_voice_channel = AsyncMock()

        created_channel = MagicMock()
        created_channel.id = 123456
        guild.create_voice_channel.return_value = created_channel

        category = MagicMock(spec=discord.CategoryChannel)
        category.id = 789012
        category.name = "Voice Category"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await temp_voice.setup_voice.callback(temp_voice, interaction, category)

        guild.create_voice_channel.assert_called_once()
        assert temp_voice.voice_config["creation_channel"] == 123456
        assert temp_voice.voice_config["temp_category"] == 789012
        interaction.response.send_message.assert_called_once()


class TestTempVoiceChannelCreation:
    """Тесты создания временных каналов."""

    @pytest.fixture
    def temp_voice(self, tmp_path):
        """Фикстура для создания системы временных каналов."""
        bot = MagicMock()
        bot.get_channel = MagicMock()
        system = TempVoice(bot)
        system.config_path = tmp_path / "voice_config.json"
        system.voice_config = {"creation_channel": 123456, "temp_category": 789012}
        system.temp_channels = {}
        return system

    @pytest.mark.asyncio
    async def test_on_voice_state_update_creates_channel(self, temp_voice):
        """Тест создания временного канала при подключении."""
        member = MagicMock(spec=discord.Member)
        member.id = 111111
        member.display_name = "TestUser"
        member.move_to = AsyncMock()

        guild = MagicMock()
        guild.create_voice_channel = AsyncMock()

        created_channel = MagicMock()
        created_channel.id = 999999
        created_channel.set_permissions = AsyncMock()
        guild.create_voice_channel.return_value = created_channel

        category = MagicMock()
        temp_voice.bot.get_channel.return_value = category

        after_channel = MagicMock()
        after_channel.id = 123456

        member.guild = guild

        before = MagicMock()
        before.channel = None

        after = MagicMock()
        after.channel = after_channel

        await temp_voice.on_voice_state_update(member, before, after)

        guild.create_voice_channel.assert_called_once()
        assert "TestUser" in guild.create_voice_channel.call_args[0][0]
        member.move_to.assert_called_once_with(created_channel)
        assert temp_voice.temp_channels[999999] == 111111
        created_channel.set_permissions.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_voice_state_update_deletes_empty_channel(self, temp_voice):
        """Тест удаления пустого временного канала."""
        member = MagicMock(spec=discord.Member)

        before_channel = MagicMock()
        before_channel.id = 999999
        before_channel.members = []
        before_channel.delete = AsyncMock()

        temp_voice.temp_channels[999999] = 111111

        before = MagicMock()
        before.channel = before_channel

        after = MagicMock()
        after.channel = None

        await temp_voice.on_voice_state_update(member, before, after)

        before_channel.delete.assert_called_once()
        assert 999999 not in temp_voice.temp_channels

    @pytest.mark.asyncio
    async def test_on_voice_state_update_keeps_channel_with_members(self, temp_voice):
        """Тест что канал не удаляется если в нем есть участники."""
        member = MagicMock(spec=discord.Member)

        other_member = MagicMock()

        before_channel = MagicMock()
        before_channel.id = 999999
        before_channel.members = [other_member]
        before_channel.delete = AsyncMock()

        temp_voice.temp_channels[999999] = 111111

        before = MagicMock()
        before.channel = before_channel

        after = MagicMock()
        after.channel = None

        await temp_voice.on_voice_state_update(member, before, after)

        before_channel.delete.assert_not_called()
        assert 999999 in temp_voice.temp_channels


class TestTempVoiceChannelManagement:
    """Тесты управления временными каналами."""

    @pytest.fixture
    def temp_voice(self, tmp_path):
        """Фикстура для создания системы временных каналов."""
        bot = MagicMock()
        system = TempVoice(bot)
        system.config_path = tmp_path / "voice_config.json"
        system.voice_config = {}
        system.temp_channels = {999999: 111111}
        return system

    @pytest.mark.asyncio
    async def test_set_limit_success(self, temp_voice):
        """Тест установки лимита пользователей."""
        voice_channel = MagicMock()
        voice_channel.id = 999999
        voice_channel.edit = AsyncMock()

        user = MagicMock()
        user.id = 111111
        user.voice = MagicMock()
        user.voice.channel = voice_channel

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.set_limit.callback(temp_voice, interaction, 5)

        voice_channel.edit.assert_called_once_with(user_limit=5)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_limit_not_in_voice(self, temp_voice):
        """Тест установки лимита когда пользователь не в голосовом канале."""
        user = MagicMock()
        user.voice = None

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.set_limit.callback(temp_voice, interaction, 5)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "должны находиться" in call_args.lower()

    @pytest.mark.asyncio
    async def test_set_limit_not_owner(self, temp_voice):
        """Тест установки лимита не владельцем канала."""
        voice_channel = MagicMock()
        voice_channel.id = 999999

        user = MagicMock()
        user.id = 222222  # Не владелец
        user.voice = MagicMock()
        user.voice.channel = voice_channel

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.set_limit.callback(temp_voice, interaction, 5)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "не ваш канал" in call_args.lower()

    @pytest.mark.asyncio
    async def test_set_name_success(self, temp_voice):
        """Тест изменения названия канала."""
        voice_channel = MagicMock()
        voice_channel.id = 999999
        voice_channel.edit = AsyncMock()

        user = MagicMock()
        user.id = 111111
        user.voice = MagicMock()
        user.voice.channel = voice_channel

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.set_name.callback(temp_voice, interaction, "New Channel Name")

        voice_channel.edit.assert_called_once_with(name="New Channel Name")
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_name_not_in_voice(self, temp_voice):
        """Тест изменения названия когда пользователь не в голосовом канале."""
        user = MagicMock()
        user.voice = None

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.set_name.callback(temp_voice, interaction, "New Name")

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "должны находиться" in call_args.lower()

    @pytest.mark.asyncio
    async def test_set_name_not_owner(self, temp_voice):
        """Тест изменения названия не владельцем канала."""
        voice_channel = MagicMock()
        voice_channel.id = 999999

        user = MagicMock()
        user.id = 222222  # Не владелец
        user.voice = MagicMock()
        user.voice.channel = voice_channel

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.set_name.callback(temp_voice, interaction, "New Name")

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "не ваш канал" in call_args.lower()


class TestTempVoiceChannelLocking:
    """Тесты блокировки/разблокировки каналов."""

    @pytest.fixture
    def temp_voice(self, tmp_path):
        """Фикстура для создания системы временных каналов."""
        bot = MagicMock()
        system = TempVoice(bot)
        system.config_path = tmp_path / "voice_config.json"
        system.voice_config = {}
        system.temp_channels = {999999: 111111}
        return system

    @pytest.mark.asyncio
    async def test_lock_channel_success(self, temp_voice):
        """Тест блокировки канала."""
        guild = MagicMock()
        guild.default_role = MagicMock()

        voice_channel = MagicMock()
        voice_channel.id = 999999
        voice_channel.set_permissions = AsyncMock()

        user = MagicMock()
        user.id = 111111
        user.voice = MagicMock()
        user.voice.channel = voice_channel

        interaction = AsyncMock()
        interaction.user = user
        interaction.guild = guild
        interaction.response = AsyncMock()

        await temp_voice.lock_channel.callback(temp_voice, interaction)

        voice_channel.set_permissions.assert_called_once()
        call_args = voice_channel.set_permissions.call_args
        assert call_args.kwargs["connect"] is False
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_channel_not_in_voice(self, temp_voice):
        """Тест блокировки когда пользователь не в голосовом канале."""
        user = MagicMock()
        user.voice = None

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.lock_channel.callback(temp_voice, interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "должны находиться" in call_args.lower()

    @pytest.mark.asyncio
    async def test_lock_channel_not_owner(self, temp_voice):
        """Тест блокировки не владельцем канала."""
        voice_channel = MagicMock()
        voice_channel.id = 999999

        user = MagicMock()
        user.id = 222222  # Не владелец
        user.voice = MagicMock()
        user.voice.channel = voice_channel

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.lock_channel.callback(temp_voice, interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "не ваш канал" in call_args.lower()

    @pytest.mark.asyncio
    async def test_unlock_channel_success(self, temp_voice):
        """Тест разблокировки канала."""
        guild = MagicMock()
        guild.default_role = MagicMock()

        voice_channel = MagicMock()
        voice_channel.id = 999999
        voice_channel.set_permissions = AsyncMock()

        user = MagicMock()
        user.id = 111111
        user.voice = MagicMock()
        user.voice.channel = voice_channel

        interaction = AsyncMock()
        interaction.user = user
        interaction.guild = guild
        interaction.response = AsyncMock()

        await temp_voice.unlock_channel.callback(temp_voice, interaction)

        voice_channel.set_permissions.assert_called_once()
        call_args = voice_channel.set_permissions.call_args
        assert call_args.kwargs["connect"] is True
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlock_channel_not_in_voice(self, temp_voice):
        """Тест разблокировки когда пользователь не в голосовом канале."""
        user = MagicMock()
        user.voice = None

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.unlock_channel.callback(temp_voice, interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "должны находиться" in call_args.lower()

    @pytest.mark.asyncio
    async def test_unlock_channel_not_owner(self, temp_voice):
        """Тест разблокировки не владельцем канала."""
        voice_channel = MagicMock()
        voice_channel.id = 999999

        user = MagicMock()
        user.id = 222222  # Не владелец
        user.voice = MagicMock()
        user.voice.channel = voice_channel

        interaction = AsyncMock()
        interaction.user = user
        interaction.response = AsyncMock()

        await temp_voice.unlock_channel.callback(temp_voice, interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "не ваш канал" in call_args.lower()


class TestTempVoiceCleanup:
    """Тесты очистки неактивных каналов."""

    @pytest.fixture
    def temp_voice(self, tmp_path):
        """Фикстура для создания системы временных каналов."""
        bot = MagicMock()
        system = TempVoice(bot)
        system.config_path = tmp_path / "voice_config.json"
        system.voice_config = {}
        return system

    @pytest.mark.asyncio
    async def test_cleanup_empty_channels(self, temp_voice):
        """Тест очистки пустых каналов."""
        channel1 = MagicMock()
        channel1.id = 111111
        channel1.members = []
        channel1.delete = AsyncMock()

        channel2 = MagicMock()
        channel2.id = 222222
        channel2.members = [MagicMock()]  # Есть участник

        temp_voice.bot.get_channel = lambda cid: channel1 if cid == 111111 else channel2
        temp_voice.temp_channels = {111111: 999999, 222222: 888888}

        await temp_voice.cleanup_inactive_channels()

        channel1.delete.assert_called_once()
        assert 111111 not in temp_voice.temp_channels
        assert 222222 in temp_voice.temp_channels

    @pytest.mark.asyncio
    async def test_cleanup_deleted_channels(self, temp_voice):
        """Тест очистки удаленных каналов из словаря."""
        temp_voice.bot.get_channel = lambda cid: None  # Канал не найден
        temp_voice.temp_channels = {111111: 999999}

        await temp_voice.cleanup_inactive_channels()

        assert 111111 not in temp_voice.temp_channels

    @pytest.mark.asyncio
    async def test_cleanup_no_channels(self, temp_voice):
        """Тест очистки когда нет временных каналов."""
        temp_voice.temp_channels = {}

        # Не должно быть ошибки
        await temp_voice.cleanup_inactive_channels()

    @pytest.mark.asyncio
    async def test_cleanup_handles_http_exception(self, temp_voice):
        """Тест обработки HTTPException при удалении канала."""
        channel = MagicMock()
        channel.id = 111111
        channel.members = []
        channel.delete = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "Error"))

        temp_voice.bot.get_channel = lambda cid: channel
        temp_voice.temp_channels = {111111: 999999}

        # Не должно быть исключения
        await temp_voice.cleanup_inactive_channels()

        # При HTTPException канал остается в словаре (по дизайну)
        assert 111111 in temp_voice.temp_channels
