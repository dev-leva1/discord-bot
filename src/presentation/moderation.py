"""Ког с командами модерации."""

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_helpers import check_role_hierarchy, parse_duration


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Забанить пользователя")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str | None = None,
    ):
        can_moderate, error_msg = check_role_hierarchy(interaction.user, member)
        if not can_moderate:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        await member.ban(reason=reason)
        embed = discord.Embed(
            title="Бан участника",
            description=(
                f"Участник {member.mention} был забанен\nПричина: {reason or 'Не указана'}"
            ),
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kick", description="Выгнать пользователя")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str | None = None,
    ):
        can_moderate, error_msg = check_role_hierarchy(interaction.user, member)
        if not can_moderate:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        await member.kick(reason=reason)
        embed = discord.Embed(
            title="Кик участника",
            description=(
                f"Участник {member.mention} был выгнан\nПричина: {reason or 'Не указана'}"
            ),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mute", description="Замутить пользователя")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str | None = None,
    ):
        can_moderate, error_msg = check_role_hierarchy(interaction.user, member)
        if not can_moderate:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        # Парсинг длительности
        try:
            delta = parse_duration(duration)
        except ValueError as e:
            await interaction.response.send_message(
                f"Ошибка: {str(e)}",
                ephemeral=True,
            )
            return

        await member.timeout(delta, reason=reason)
        embed = discord.Embed(
            title="Мут участника",
            description=(
                f"Участник {member.mention} был замучен на {duration}\n"
                f"Причина: {reason or 'Не указана'}"
            ),
            color=discord.Color.yellow(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Очистить сообщения")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "Количество сообщений должно быть от 1 до 100!", ephemeral=True
            )
            return

        await interaction.channel.purge(limit=amount)
        embed = discord.Embed(
            title="Очистка сообщений",
            description=f"Удалено {amount} сообщений",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
