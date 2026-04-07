"""Тесты для системы приветствий."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from pathlib import Path
import json

from welcome import Welcome


class TestWelcomeConfiguration:
    """Тесты конфигурации системы приветствий."""

    @pytest.fixture
    def welcome_system(self, tmp_path):
        """Фикстура для создания системы приветствий."""
        bot = MagicMock()
        bot.image_generator = MagicMock()
        system = Welcome(bot)
        system.config_file = tmp_path / "welcome_config.json"
        return system

    def test_load_config_creates_empty_if_not_exists(self, welcome_system):
        """Тест создания пустой конфигурации если файл не существует."""
        welcome_system.load_config()
        assert welcome_system.config == {}

    def test_load_config_reads_existing_file(self, welcome_system):
        """Тест чтения существующего файла конфигурации."""
        test_config = {"123456": 789012}
        welcome_system.config_file.write_text(json.dumps(test_config))

        welcome_system.load_config()

        assert welcome_system.config == test_config

    def test_save_config_writes_to_file(self, welcome_system):
        """Тест сохранения конфигурации в файл."""
        welcome_system.config = {"123456": 789012}

        welcome_system.save_config()

        saved_data = json.loads(welcome_system.config_file.read_text())
        assert saved_data == {"123456": 789012}


class TestWelcomeSetup:
    """Тесты настройки канала приветствий."""

    @pytest.fixture
    def welcome_system(self, tmp_path):
        """Фикстура для создания системы приветствий."""
        bot = MagicMock()

        # Сохраняем зарегистрированные команды
        registered_commands = {}

        def mock_command(**kwargs):
            def decorator(func):
                registered_commands[kwargs.get('name', func.__name__)] = func
                return func
            return decorator

        bot.tree.command = mock_command

        bot.image_generator = MagicMock()
        system = Welcome(bot)
        system.config_file = tmp_path / "welcome_config.json"
        system.config = {}
        system._registered_commands = registered_commands
        return system

    @pytest.mark.asyncio
    async def test_setup_registers_command(self, welcome_system):
        """Тест регистрации команды setwelcome."""
        await welcome_system.setup()

        assert 'setwelcome' in welcome_system._registered_commands

    @pytest.mark.asyncio
    async def test_setwelcome_command_success(self, welcome_system):
        """Тест успешной настройки канала приветствий."""
        await welcome_system.setup()

        setwelcome_func = welcome_system._registered_commands['setwelcome']

        guild = MagicMock()
        guild.id = 123456
        guild.me = MagicMock()

        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 789012
        channel.mention = "#welcome"

        # Настраиваем права бота
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = True
        channel.permissions_for = MagicMock(return_value=permissions)

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await setwelcome_func(interaction, channel)

        # Проверяем что канал сохранен в конфиге
        assert welcome_system.config["123456"] == 789012

        # Проверяем что отправлен embed
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_setwelcome_command_no_send_permission(self, welcome_system):
        """Тест настройки канала без прав на отправку сообщений."""
        await welcome_system.setup()

        setwelcome_func = welcome_system._registered_commands['setwelcome']

        guild = MagicMock()
        guild.id = 123456
        guild.me = MagicMock()

        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 789012

        # Нет прав на отправку сообщений
        permissions = MagicMock()
        permissions.send_messages = False
        permissions.embed_links = True
        channel.permissions_for = MagicMock(return_value=permissions)

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await setwelcome_func(interaction, channel)

        # Проверяем что канал НЕ сохранен
        assert "123456" not in welcome_system.config

        # Проверяем что отправлено сообщение об ошибке
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[1]
        assert call_args["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_setwelcome_command_no_embed_permission(self, welcome_system):
        """Тест настройки канала без прав на отправку эмбедов."""
        await welcome_system.setup()

        setwelcome_func = welcome_system._registered_commands['setwelcome']

        guild = MagicMock()
        guild.id = 123456
        guild.me = MagicMock()

        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 789012

        # Нет прав на отправку эмбедов
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = False
        channel.permissions_for = MagicMock(return_value=permissions)

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.response = AsyncMock()

        await setwelcome_func(interaction, channel)

        # Проверяем что канал НЕ сохранен
        assert "123456" not in welcome_system.config

        # Проверяем что отправлено сообщение об ошибке
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[1]
        assert call_args["ephemeral"] is True


class TestWelcomeSendWelcome:
    """Тесты отправки приветственных сообщений."""

    @pytest.fixture
    def welcome_system(self, tmp_path):
        """Фикстура для создания системы приветствий."""
        bot = MagicMock()
        bot.image_generator = MagicMock()
        bot.image_generator.create_welcome_card = AsyncMock()
        system = Welcome(bot)
        system.config_file = tmp_path / "welcome_config.json"
        system.config = {"123456": 789012}
        return system

    @pytest.mark.asyncio
    async def test_send_welcome_no_config(self, welcome_system):
        """Тест что приветствие не отправляется если канал не настроен."""
        guild = MagicMock()
        guild.id = 999999  # Нет в конфиге

        member = MagicMock(spec=discord.Member)
        member.guild = guild

        await welcome_system.send_welcome(member)

        # Не должно быть попыток создать карточку
        welcome_system.bot.image_generator.create_welcome_card.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_welcome_channel_not_found(self, welcome_system):
        """Тест что приветствие не отправляется если канал не найден."""
        guild = MagicMock()
        guild.id = 123456
        guild.get_channel = MagicMock(return_value=None)

        member = MagicMock(spec=discord.Member)
        member.guild = guild

        await welcome_system.send_welcome(member)

        # Не должно быть попыток создать карточку
        welcome_system.bot.image_generator.create_welcome_card.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_welcome_success(self, welcome_system):
        """Тест успешной отправки приветствия."""
        guild = MagicMock()
        guild.id = 123456

        channel = AsyncMock()
        guild.get_channel = MagicMock(return_value=channel)

        member = MagicMock(spec=discord.Member)
        member.guild = guild

        welcome_card = MagicMock()
        welcome_system.bot.image_generator.create_welcome_card.return_value = welcome_card

        await welcome_system.send_welcome(member)

        # Проверяем что карточка создана
        welcome_system.bot.image_generator.create_welcome_card.assert_called_once_with(
            member, guild
        )

        # Проверяем что сообщение отправлено
        channel.send.assert_called_once_with(file=welcome_card)

    @pytest.mark.asyncio
    async def test_send_welcome_handles_http_exception(self, welcome_system):
        """Тест обработки HTTPException при отправке."""
        guild = MagicMock()
        guild.id = 123456

        channel = AsyncMock()
        channel.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "Error"))
        guild.get_channel = MagicMock(return_value=channel)

        member = MagicMock(spec=discord.Member)
        member.guild = guild

        welcome_card = MagicMock()
        welcome_system.bot.image_generator.create_welcome_card.return_value = welcome_card

        # Не должно быть исключения
        await welcome_system.send_welcome(member)

        # Карточка должна быть создана
        welcome_system.bot.image_generator.create_welcome_card.assert_called_once()


class TestWelcomeMultipleGuilds:
    """Тесты работы с несколькими серверами."""

    @pytest.fixture
    def welcome_system(self, tmp_path):
        """Фикстура для создания системы приветствий."""
        bot = MagicMock()
        bot.image_generator = MagicMock()
        bot.image_generator.create_welcome_card = AsyncMock()
        system = Welcome(bot)
        system.config_file = tmp_path / "welcome_config.json"
        system.config = {
            "123456": 111111,
            "789012": 222222
        }
        return system

    @pytest.mark.asyncio
    async def test_send_welcome_correct_guild(self, welcome_system):
        """Тест отправки приветствия на правильный сервер."""
        guild1 = MagicMock()
        guild1.id = 123456

        channel1 = AsyncMock()
        guild1.get_channel = MagicMock(return_value=channel1)

        member1 = MagicMock(spec=discord.Member)
        member1.guild = guild1

        welcome_card = MagicMock()
        welcome_system.bot.image_generator.create_welcome_card.return_value = welcome_card

        await welcome_system.send_welcome(member1)

        # Проверяем что получен правильный канал
        guild1.get_channel.assert_called_once_with(111111)

        # Проверяем что сообщение отправлено
        channel1.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_welcome_different_guilds(self, welcome_system):
        """Тест отправки приветствий на разные серверы."""
        # Первый сервер
        guild1 = MagicMock()
        guild1.id = 123456

        channel1 = AsyncMock()
        guild1.get_channel = MagicMock(return_value=channel1)

        member1 = MagicMock(spec=discord.Member)
        member1.guild = guild1

        # Второй сервер
        guild2 = MagicMock()
        guild2.id = 789012

        channel2 = AsyncMock()
        guild2.get_channel = MagicMock(return_value=channel2)

        member2 = MagicMock(spec=discord.Member)
        member2.guild = guild2

        welcome_card = MagicMock()
        welcome_system.bot.image_generator.create_welcome_card.return_value = welcome_card

        # Отправляем приветствия
        await welcome_system.send_welcome(member1)
        await welcome_system.send_welcome(member2)

        # Проверяем что каналы получены правильно
        guild1.get_channel.assert_called_once_with(111111)
        guild2.get_channel.assert_called_once_with(222222)

        # Проверяем что сообщения отправлены в оба канала
        channel1.send.assert_called_once()
        channel2.send.assert_called_once()
