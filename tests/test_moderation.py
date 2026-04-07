from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.moderation import Moderation


@dataclass
class RoleStub:
    position: int

    def __ge__(self, other: "RoleStub") -> bool:
        return self.position >= other.position


@pytest.fixture()
def moderation_ctx():
    bot = MagicMock()
    moderation = Moderation(bot)
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.response = AsyncMock()
    member = AsyncMock()
    member.mention = "@member"
    return moderation, interaction, member


@pytest.mark.asyncio
async def test_ban_command(moderation_ctx):
    moderation, interaction, member = moderation_ctx
    interaction.user.top_role = RoleStub(position=2)
    member.top_role = RoleStub(position=1)
    member.guild.owner_id = 999999

    await moderation.ban.callback(moderation, interaction, member, "test reason")

    member.ban.assert_called_once_with(reason="test reason")
    interaction.response.send_message.assert_called_once()
    _, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs


@pytest.mark.asyncio
async def test_ban_command_no_permission(moderation_ctx):
    moderation, interaction, member = moderation_ctx
    interaction.user.top_role = RoleStub(position=1)
    member.top_role = RoleStub(position=1)
    member.guild.owner_id = 999999

    await moderation.ban.callback(moderation, interaction, member, "test reason")

    member.ban.assert_not_called()
    interaction.response.send_message.assert_called_once()
    call_args = interaction.response.send_message.call_args[0][0]
    assert "равной или более высокой ролью" in call_args


@pytest.mark.asyncio
async def test_kick_command(moderation_ctx):
    moderation, interaction, member = moderation_ctx
    interaction.user.top_role = RoleStub(position=2)
    member.top_role = RoleStub(position=1)
    member.guild.owner_id = 999999

    await moderation.kick.callback(moderation, interaction, member, "test reason")

    member.kick.assert_called_once_with(reason="test reason")
    interaction.response.send_message.assert_called_once()
    _, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs


@pytest.mark.asyncio
async def test_kick_command_no_permission(moderation_ctx):
    moderation, interaction, member = moderation_ctx
    interaction.user.top_role = RoleStub(position=1)
    member.top_role = RoleStub(position=2)
    member.guild.owner_id = 999999

    await moderation.kick.callback(moderation, interaction, member, "test reason")

    member.kick.assert_not_called()
    interaction.response.send_message.assert_called_once()
    call_args = interaction.response.send_message.call_args[0][0]
    assert "равной или более высокой ролью" in call_args


@pytest.mark.asyncio
async def test_mute_command(moderation_ctx):
    moderation, interaction, member = moderation_ctx
    interaction.user.top_role = RoleStub(position=2)
    member.top_role = RoleStub(position=1)
    member.guild.owner_id = 999999

    await moderation.mute.callback(moderation, interaction, member, "30m", "test reason")

    member.timeout.assert_called_once()
    args, kwargs = member.timeout.call_args
    assert args[0] == timedelta(minutes=30)
    assert kwargs["reason"] == "test reason"
    interaction.response.send_message.assert_called_once()
    _, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs


@pytest.mark.asyncio
async def test_mute_command_invalid_duration(moderation_ctx):
    moderation, interaction, member = moderation_ctx
    interaction.user.top_role = RoleStub(position=2)
    member.top_role = RoleStub(position=1)
    member.guild.owner_id = 999999

    await moderation.mute.callback(moderation, interaction, member, "invalid", "test reason")

    member.timeout.assert_not_called()
    interaction.response.send_message.assert_called_once()
    call_args = interaction.response.send_message.call_args[0][0]
    assert "Ошибка" in call_args


@pytest.mark.asyncio
async def test_clear_command(moderation_ctx):
    moderation, interaction, _ = moderation_ctx
    interaction.channel = AsyncMock()

    await moderation.clear.callback(moderation, interaction, 10)

    interaction.channel.purge.assert_called_once_with(limit=10)
    interaction.response.send_message.assert_called_once()
    _, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs


@pytest.mark.asyncio
async def test_clear_command_invalid_amount(moderation_ctx):
    moderation, interaction, _ = moderation_ctx
    interaction.channel = AsyncMock()

    await moderation.clear.callback(moderation, interaction, -5)

    interaction.channel.purge.assert_not_called()
    interaction.response.send_message.assert_called_once_with(
        "Количество сообщений должно быть от 1 до 100!",
        ephemeral=True,
    )
