"""Тесты для утилит Discord."""

import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from utils.discord_helpers import parse_duration, check_role_hierarchy, send_response


class TestParseDuration:
    """Тесты для функции parse_duration."""

    def test_parse_minutes(self):
        """Тест парсинга минут."""
        result = parse_duration("30m")
        assert result == timedelta(minutes=30)

    def test_parse_hours(self):
        """Тест парсинга часов."""
        result = parse_duration("2h")
        assert result == timedelta(hours=2)

    def test_parse_days(self):
        """Тест парсинга дней."""
        result = parse_duration("7d")
        assert result == timedelta(days=7)

    def test_parse_single_digit(self):
        """Тест парсинга однозначных чисел."""
        assert parse_duration("1m") == timedelta(minutes=1)
        assert parse_duration("1h") == timedelta(hours=1)
        assert parse_duration("1d") == timedelta(days=1)

    def test_parse_large_numbers(self):
        """Тест парсинга больших чисел."""
        assert parse_duration("999m") == timedelta(minutes=999)
        assert parse_duration("168h") == timedelta(hours=168)  # неделя
        assert parse_duration("365d") == timedelta(days=365)  # год

    def test_invalid_empty_string(self):
        """Тест с пустой строкой."""
        with pytest.raises(ValueError, match="Неверный формат длительности"):
            parse_duration("")

    def test_invalid_single_char(self):
        """Тест с одним символом."""
        with pytest.raises(ValueError, match="Неверный формат длительности"):
            parse_duration("m")

    def test_invalid_unit(self):
        """Тест с неверной единицей времени."""
        with pytest.raises(ValueError, match="Неизвестная единица времени"):
            parse_duration("10s")  # секунды не поддерживаются

    def test_invalid_non_numeric(self):
        """Тест с нечисловым значением."""
        with pytest.raises(ValueError, match="Неверное числовое значение"):
            parse_duration("abcm")

    def test_negative_number_parsed(self):
        """Тест с отрицательным числом - парсится, но дает отрицательную длительность."""
        result = parse_duration("-5m")
        assert result == timedelta(minutes=-5)

    def test_case_insensitive(self):
        """Тест регистронезависимости единиц."""
        assert parse_duration("10M") == timedelta(minutes=10)
        assert parse_duration("2H") == timedelta(hours=2)
        assert parse_duration("3D") == timedelta(days=3)


class TestCheckRoleHierarchy:
    """Тесты для функции check_role_hierarchy."""

    def test_moderator_higher_role(self):
        """Тест: модератор имеет более высокую роль."""
        moderator = MagicMock(spec=discord.Member)
        target = MagicMock(spec=discord.Member)

        moderator.top_role = MagicMock(position=10)
        target.top_role = MagicMock(position=5)
        target.guild.owner_id = 999999
        target.id = 123456

        # Настройка сравнения ролей
        moderator.top_role.__ge__ = lambda self, other: self.position >= other.position
        target.top_role.__ge__ = lambda self, other: self.position >= other.position

        can_moderate, error = check_role_hierarchy(moderator, target)
        assert can_moderate is True
        assert error is None

    def test_equal_roles(self):
        """Тест: равные роли."""
        moderator = MagicMock(spec=discord.Member)
        target = MagicMock(spec=discord.Member)

        moderator.top_role = MagicMock(position=10)
        target.top_role = MagicMock(position=10)
        target.guild.owner_id = 999999
        target.id = 123456

        moderator.top_role.__ge__ = lambda self, other: self.position >= other.position
        target.top_role.__ge__ = lambda self, other: self.position >= other.position

        can_moderate, error = check_role_hierarchy(moderator, target)
        assert can_moderate is False
        assert "равной или более высокой ролью" in error

    def test_target_higher_role(self):
        """Тест: цель имеет более высокую роль."""
        moderator = MagicMock(spec=discord.Member)
        target = MagicMock(spec=discord.Member)

        moderator.top_role = MagicMock(position=5)
        target.top_role = MagicMock(position=10)
        target.guild.owner_id = 999999
        target.id = 123456

        moderator.top_role.__ge__ = lambda self, other: self.position >= other.position
        target.top_role.__ge__ = lambda self, other: self.position >= other.position

        can_moderate, error = check_role_hierarchy(moderator, target)
        assert can_moderate is False
        assert "равной или более высокой ролью" in error

    def test_target_is_owner(self):
        """Тест: цель является владельцем сервера."""
        moderator = MagicMock(spec=discord.Member)
        target = MagicMock(spec=discord.Member)

        moderator.top_role = MagicMock(position=10)
        target.top_role = MagicMock(position=5)
        target.guild.owner_id = 123456
        target.id = 123456  # Совпадает с owner_id

        moderator.top_role.__ge__ = lambda self, other: self.position >= other.position
        target.top_role.__ge__ = lambda self, other: self.position >= other.position

        can_moderate, error = check_role_hierarchy(moderator, target)
        assert can_moderate is False
        assert "владельце сервера" in error


class TestSendResponse:
    """Тесты для функции send_response."""

    @pytest.mark.asyncio
    async def test_send_to_interaction_not_responded(self):
        """Тест отправки в Interaction, который еще не ответил."""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()

        await send_response(interaction, "Test message", ephemeral=True)

        interaction.response.send_message.assert_called_once_with(
            "Test message", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_send_to_interaction_already_responded(self):
        """Тест отправки в Interaction, который уже ответил."""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.response.is_done.return_value = True
        interaction.followup.send = AsyncMock()

        await send_response(interaction, "Follow-up message", ephemeral=True)

        interaction.followup.send.assert_called_once_with(
            "Follow-up message", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_send_to_context(self):
        """Тест отправки в Context."""
        ctx = MagicMock(spec=commands.Context)
        ctx.send = AsyncMock()

        await send_response(ctx, "Context message", delete_after=5)

        ctx.send.assert_called_once_with("Context message", delete_after=5)

    @pytest.mark.asyncio
    async def test_send_with_embed(self):
        """Тест отправки с embed."""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()

        embed = discord.Embed(title="Test")
        await send_response(interaction, "Message", embed=embed)

        interaction.response.send_message.assert_called_once_with(
            "Message", embed=embed
        )

    @pytest.mark.asyncio
    async def test_send_with_multiple_kwargs(self):
        """Тест отправки с несколькими параметрами."""
        ctx = MagicMock(spec=commands.Context)
        ctx.send = AsyncMock()

        await send_response(
            ctx,
            "Complex message",
            ephemeral=True,
            delete_after=10,
            mention_author=False
        )

        ctx.send.assert_called_once_with(
            "Complex message",
            ephemeral=True,
            delete_after=10,
            mention_author=False
        )
