import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import discord
from moderation import Moderation

class TestModerationCommands(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.moderation = Moderation(self.bot)
        self.interaction = AsyncMock()
        self.member = AsyncMock()
        
    async def test_ban_command(self):
        # Настройка мока
        self.interaction.user.top_role = MagicMock(position=2)
        self.member.top_role = MagicMock(position=1)
        
        # Запускаем тест
        await self.moderation.ban(self.interaction, self.member, "test reason")
        
        # Проверки
        self.member.ban.assert_called_once_with(reason="test reason")
        self.interaction.response.send_message.assert_called_once()

    async def test_ban_command_no_permission(self):
        # Настройка мока - одинаковые роли
        self.interaction.user.top_role = MagicMock(position=1)
        self.member.top_role = MagicMock(position=1)
        
        # Запускаем тест
        await self.moderation.ban(self.interaction, self.member, "test reason")
        
        # Проверки
        self.member.ban.assert_not_called()
        self.interaction.response.send_message.assert_called_once_with("У вас недостаточно прав для бана этого участника", ephemeral=True)
        
    async def test_kick_command(self):
        # Настройка мока
        self.interaction.user.top_role = MagicMock(position=2)
        self.member.top_role = MagicMock(position=1)
        
        # Запускаем тест
        await self.moderation.kick(self.interaction, self.member, "test reason")
        
        # Проверки
        self.member.kick.assert_called_once_with(reason="test reason")
        self.interaction.response.send_message.assert_called_once()

    async def test_kick_command_no_permission(self):
        # Настройка мока - роль цели выше
        self.interaction.user.top_role = MagicMock(position=1)
        self.member.top_role = MagicMock(position=2)
        
        # Запускаем тест
        await self.moderation.kick(self.interaction, self.member, "test reason")
        
        # Проверки
        self.member.kick.assert_not_called()
        self.interaction.response.send_message.assert_called_once_with("У вас недостаточно прав для кика этого участника", ephemeral=True)
        
    async def test_mute_command(self):
        # Настройка мока
        self.interaction.user.top_role = MagicMock(position=2)
        self.member.top_role = MagicMock(position=1)
        
        # Запускаем тест
        await self.moderation.mute(self.interaction, self.member, "30m", "test reason")
        
        # Проверки
        self.member.timeout.assert_called_once()
        self.interaction.response.send_message.assert_called_once()

    async def test_mute_command_invalid_duration(self):
        # Настройка мока
        self.interaction.user.top_role = MagicMock(position=2)
        self.member.top_role = MagicMock(position=1)
        
        # Запускаем тест
        await self.moderation.mute(self.interaction, self.member, "invalid", "test reason")
        
        # Проверки
        self.member.timeout.assert_not_called()
        self.interaction.response.send_message.assert_called_once_with("Неверный формат длительности. Используйте: 30s, 5m, 2h, 1d", ephemeral=True)
        
    async def test_clear_command(self):
        # Настройка мока
        self.interaction.channel = AsyncMock()
        
        # Запускаем тест
        await self.moderation.clear(self.interaction, 10)
        
        # Проверки
        self.interaction.channel.purge.assert_called_once_with(limit=10)
        self.interaction.response.send_message.assert_called_once()

    async def test_clear_command_invalid_amount(self):
        # Настройка мока
        self.interaction.channel = AsyncMock()
        
        # Запускаем тест с отрицательным числом
        await self.moderation.clear(self.interaction, -5)
        
        # Проверки
        self.interaction.channel.purge.assert_not_called()
        self.interaction.response.send_message.assert_called_once_with("Количество сообщений должно быть положительным числом", ephemeral=True)

    async def test_warn_command(self):
        # Настройка мока
        self.interaction.user.top_role = MagicMock(position=2)
        self.member.top_role = MagicMock(position=1)
        
        # Запускаем тест
        await self.moderation.warn(self.interaction, self.member, "test warning")
        
        # Проверки
        self.interaction.response.send_message.assert_called_once()
        
    async def test_unwarn_command(self):
        # Настройка мока
        self.interaction.user.top_role = MagicMock(position=2)
        self.member.top_role = MagicMock(position=1)
        
        # Запускаем тест
        await self.moderation.unwarn(self.interaction, self.member)
        
        # Проверки
        self.interaction.response.send_message.assert_called_once()