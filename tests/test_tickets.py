"""Тесты для системы тикетов."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
from datetime import datetime

from tickets import TicketSystem
from infrastructure.config import TicketsConfigStore


class TestTicketSystemConfiguration:
    """Тесты конфигурации системы тикетов."""

    @pytest.fixture
    def ticket_system(self):
        """Фикстура для создания системы тикетов."""
        bot = MagicMock()
        repository = MagicMock()
        store = MagicMock(spec=TicketsConfigStore)
        store.load.return_value = {
            "ticket_category": None,
            "support_role": None,
            "ticket_counter": 0
        }

        system = TicketSystem(bot, repository, store)
        return system

    def test_load_config(self, ticket_system):
        """Тест загрузки конфигурации."""
        assert "ticket_category" in ticket_system.tickets_config
        assert "support_role" in ticket_system.tickets_config
        assert "ticket_counter" in ticket_system.tickets_config

    def test_save_config(self, ticket_system):
        """Тест сохранения конфигурации."""
        ticket_system.tickets_config["ticket_category"] = 123456

        ticket_system.save_config()

        ticket_system.store.save.assert_called_once_with(ticket_system.tickets_config)

    @pytest.mark.asyncio
    async def test_setup(self, ticket_system):
        """Тест инициализации системы."""
        # Не должно быть ошибки
        await ticket_system.setup()


class TestTicketSystemSetup:
    """Тесты настройки системы тикетов."""

    @pytest.fixture
    def ticket_system(self):
        """Фикстура для создания системы тикетов."""
        bot = MagicMock()
        repository = MagicMock()
        store = MagicMock(spec=TicketsConfigStore)
        store.load.return_value = {}

        system = TicketSystem(bot, repository, store)
        return system

    @pytest.mark.asyncio
    async def test_setup_tickets_success(self, ticket_system):
        """Тест успешной настройки системы тикетов."""
        category = MagicMock(spec=discord.CategoryChannel)
        category.id = 123456
        category.name = "Tickets"

        support_role = MagicMock(spec=discord.Role)
        support_role.id = 789012
        support_role.name = "Support"

        interaction = AsyncMock()
        interaction.response = AsyncMock()

        await ticket_system.setup_tickets.callback(ticket_system, interaction, category, support_role)

        assert ticket_system.tickets_config["ticket_category"] == 123456
        assert ticket_system.tickets_config["support_role"] == 789012
        ticket_system.store.save.assert_called_once()
        interaction.response.send_message.assert_called_once()


class TestTicketSystemCreateTicket:
    """Тесты создания тикетов."""

    @pytest.fixture
    def ticket_system(self):
        """Фикстура для создания системы тикетов."""
        bot = MagicMock()
        bot.get_channel = MagicMock()

        repository = MagicMock()
        repository.create_ticket = AsyncMock()

        store = MagicMock(spec=TicketsConfigStore)
        store.load.return_value = {
            "ticket_category": 123456,
            "support_role": 789012,
            "ticket_counter": 0
        }

        system = TicketSystem(bot, repository, store)
        return system

    @pytest.mark.asyncio
    async def test_create_ticket_not_configured(self, ticket_system):
        """Тест создания тикета когда система не настроена."""
        ticket_system.tickets_config["ticket_category"] = None

        interaction = AsyncMock()
        interaction.response = AsyncMock()

        await ticket_system.create_ticket.callback(ticket_system, interaction, "Test reason")

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "не настроена" in call_args.lower()

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, ticket_system):
        """Тест успешного создания тикета."""
        guild = MagicMock()
        guild.id = 111111
        guild.default_role = MagicMock()
        guild.get_role = MagicMock()

        support_role = MagicMock(spec=discord.Role)
        support_role.mention = "@Support"
        guild.get_role.return_value = support_role

        category = MagicMock(spec=discord.CategoryChannel)
        category.create_text_channel = AsyncMock()

        created_channel = MagicMock()
        created_channel.id = 999999
        created_channel.mention = "#ticket-1"
        created_channel.send = AsyncMock()
        category.create_text_channel.return_value = created_channel

        ticket_system.bot.get_channel.return_value = category

        user = MagicMock()
        user.id = 222222
        user.mention = "@User"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.user = user
        interaction.response = AsyncMock()

        await ticket_system.create_ticket.callback(ticket_system, interaction, "Need help")

        # Проверяем что счетчик увеличился
        assert ticket_system.tickets_config["ticket_counter"] == 1

        # Проверяем что канал создан
        category.create_text_channel.assert_called_once()
        assert "ticket-1" in category.create_text_channel.call_args[0][0]

        # Проверяем что сообщение отправлено в канал
        created_channel.send.assert_called_once()

        # Проверяем что тикет сохранен в БД
        ticket_system.repository.create_ticket.assert_called_once()

        # Проверяем что пользователю отправлен ответ
        interaction.response.send_message.assert_called_once()

        # Проверяем что конфиг сохранен
        ticket_system.store.save.assert_called()

    @pytest.mark.asyncio
    async def test_create_ticket_with_default_reason(self, ticket_system):
        """Тест создания тикета с причиной по умолчанию."""
        guild = MagicMock()
        guild.id = 111111
        guild.default_role = MagicMock()
        guild.get_role = MagicMock()

        support_role = MagicMock(spec=discord.Role)
        support_role.mention = "@Support"
        guild.get_role.return_value = support_role

        category = MagicMock(spec=discord.CategoryChannel)
        category.create_text_channel = AsyncMock()

        created_channel = MagicMock()
        created_channel.id = 999999
        created_channel.mention = "#ticket-1"
        created_channel.send = AsyncMock()
        category.create_text_channel.return_value = created_channel

        ticket_system.bot.get_channel.return_value = category

        user = MagicMock()
        user.id = 222222
        user.mention = "@User"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.user = user
        interaction.response = AsyncMock()

        # Вызываем без указания причины
        await ticket_system.create_ticket.callback(ticket_system, interaction)

        # Проверяем что тикет создан с причиной по умолчанию
        ticket_system.repository.create_ticket.assert_called_once()
        call_args = ticket_system.repository.create_ticket.call_args[0]
        assert call_args[3] == "Не указана"

    @pytest.mark.asyncio
    async def test_create_ticket_increments_counter(self, ticket_system):
        """Тест увеличения счетчика тикетов."""
        guild = MagicMock()
        guild.id = 111111
        guild.default_role = MagicMock()
        guild.get_role = MagicMock()

        support_role = MagicMock(spec=discord.Role)
        support_role.mention = "@Support"
        guild.get_role.return_value = support_role

        category = MagicMock(spec=discord.CategoryChannel)
        category.create_text_channel = AsyncMock()

        created_channel = MagicMock()
        created_channel.id = 999999
        created_channel.mention = "#ticket-1"
        created_channel.send = AsyncMock()
        category.create_text_channel.return_value = created_channel

        ticket_system.bot.get_channel.return_value = category

        user = MagicMock()
        user.id = 222222
        user.mention = "@User"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.user = user
        interaction.response = AsyncMock()

        initial_counter = ticket_system.tickets_config["ticket_counter"]

        await ticket_system.create_ticket.callback(ticket_system, interaction, "Test")

        assert ticket_system.tickets_config["ticket_counter"] == initial_counter + 1

    @pytest.mark.asyncio
    async def test_create_ticket_without_repository(self):
        """Тест создания тикета без репозитория."""
        bot = MagicMock()
        bot.get_channel = MagicMock()

        store = MagicMock(spec=TicketsConfigStore)
        store.load.return_value = {
            "ticket_category": 123456,
            "support_role": 789012,
            "ticket_counter": 0
        }

        system = TicketSystem(bot, repository=None, store=store)

        guild = MagicMock()
        guild.id = 111111
        guild.default_role = MagicMock()
        guild.get_role = MagicMock()

        support_role = MagicMock(spec=discord.Role)
        support_role.mention = "@Support"
        guild.get_role.return_value = support_role

        category = MagicMock(spec=discord.CategoryChannel)
        category.create_text_channel = AsyncMock()

        created_channel = MagicMock()
        created_channel.id = 999999
        created_channel.mention = "#ticket-1"
        created_channel.send = AsyncMock()
        category.create_text_channel.return_value = created_channel

        system.bot.get_channel.return_value = category

        user = MagicMock()
        user.id = 222222
        user.mention = "@User"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.user = user
        interaction.response = AsyncMock()

        # Не должно быть ошибки
        await system.create_ticket.callback(system, interaction, "Test")

        # Канал должен быть создан
        category.create_text_channel.assert_called_once()


class TestTicketSystemCloseTicket:
    """Тесты закрытия тикетов."""

    @pytest.fixture
    def ticket_system(self):
        """Фикстура для создания системы тикетов."""
        bot = MagicMock()

        repository = MagicMock()
        repository.close_ticket = AsyncMock()

        store = MagicMock(spec=TicketsConfigStore)
        store.load.return_value = {}

        system = TicketSystem(bot, repository, store)
        return system

    @pytest.mark.asyncio
    async def test_close_ticket_not_in_ticket_channel(self, ticket_system):
        """Тест закрытия тикета не в канале тикета."""
        channel = MagicMock()
        channel.name = "general"

        interaction = AsyncMock()
        interaction.channel = channel
        interaction.response = AsyncMock()

        await ticket_system.close_ticket.callback(ticket_system, interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args[0][0]
        assert "только в каналах тикетов" in call_args.lower()

    @pytest.mark.asyncio
    async def test_close_ticket_success(self, ticket_system):
        """Тест успешного закрытия тикета."""
        channel = MagicMock()
        channel.name = "ticket-1"
        channel.id = 999999
        channel.delete = AsyncMock()

        interaction = AsyncMock()
        interaction.channel = channel
        interaction.response = AsyncMock()

        with patch('asyncio.sleep', new_callable=AsyncMock):
            await ticket_system.close_ticket.callback(ticket_system, interaction)

        # Проверяем что отправлено сообщение о закрытии
        interaction.response.send_message.assert_called_once()

        # Проверяем что тикет закрыт в БД
        ticket_system.repository.close_ticket.assert_called_once_with(999999)

        # Проверяем что канал удален
        channel.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_ticket_without_repository(self):
        """Тест закрытия тикета без репозитория."""
        bot = MagicMock()
        store = MagicMock(spec=TicketsConfigStore)
        store.load.return_value = {}

        system = TicketSystem(bot, repository=None, store=store)

        channel = MagicMock()
        channel.name = "ticket-1"
        channel.id = 999999
        channel.delete = AsyncMock()

        interaction = AsyncMock()
        interaction.channel = channel
        interaction.response = AsyncMock()

        with patch('asyncio.sleep', new_callable=AsyncMock):
            # Не должно быть ошибки
            await system.close_ticket.callback(system, interaction)

        # Канал должен быть удален
        channel.delete.assert_called_once()


class TestTicketSystemPermissions:
    """Тесты прав доступа к тикетам."""

    @pytest.fixture
    def ticket_system(self):
        """Фикстура для создания системы тикетов."""
        bot = MagicMock()
        bot.get_channel = MagicMock()

        repository = MagicMock()
        repository.create_ticket = AsyncMock()

        store = MagicMock(spec=TicketsConfigStore)
        store.load.return_value = {
            "ticket_category": 123456,
            "support_role": 789012,
            "ticket_counter": 0
        }

        system = TicketSystem(bot, repository, store)
        return system

    @pytest.mark.asyncio
    async def test_create_ticket_sets_permissions(self, ticket_system):
        """Тест установки прав доступа при создании тикета."""
        guild = MagicMock()
        guild.id = 111111
        guild.default_role = MagicMock()
        guild.get_role = MagicMock()

        support_role = MagicMock(spec=discord.Role)
        support_role.mention = "@Support"
        guild.get_role.return_value = support_role

        category = MagicMock(spec=discord.CategoryChannel)
        category.create_text_channel = AsyncMock()

        created_channel = MagicMock()
        created_channel.id = 999999
        created_channel.mention = "#ticket-1"
        created_channel.send = AsyncMock()
        category.create_text_channel.return_value = created_channel

        ticket_system.bot.get_channel.return_value = category

        user = MagicMock()
        user.id = 222222
        user.mention = "@User"

        interaction = AsyncMock()
        interaction.guild = guild
        interaction.user = user
        interaction.response = AsyncMock()

        await ticket_system.create_ticket.callback(ticket_system, interaction, "Test")

        # Проверяем что переданы overwrites
        call_args = category.create_text_channel.call_args
        assert "overwrites" in call_args.kwargs

        overwrites = call_args.kwargs["overwrites"]

        # Проверяем что default_role не может читать
        assert guild.default_role in overwrites
        assert overwrites[guild.default_role].read_messages is False

        # Проверяем что пользователь может читать и писать
        assert user in overwrites
        assert overwrites[user].read_messages is True
        assert overwrites[user].send_messages is True

        # Проверяем что support_role может читать и писать
        assert support_role in overwrites
        assert overwrites[support_role].read_messages is True
        assert overwrites[support_role].send_messages is True
