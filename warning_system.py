"""Модуль системы предупреждений."""

import discord
from discord import app_commands
from discord.ext import commands
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class WarningSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = self.load_warnings()
        self.config = self.load_config()

    async def setup(self):
        """Инициализация системы предупреждений"""
        print("Система предупреждений готова к работе")

    def load_warnings(self) -> Dict:
        """Загрузка предупреждений из файла.
        
        Returns:
            Dict: Загруженные предупреждения
        """
        try:
            with open('warnings.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            with open('warnings.json', 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {}

    def load_config(self) -> Dict:
        """Загрузка конфигурации из файла.
        
        Returns:
            Dict: Загруженная конфигурация
        """
        try:
            with open('warnings_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "punishments": {
                    "3": "mute_1h",
                    "5": "mute_12h",
                    "7": "kick",
                    "10": "ban"
                }
            }
            with open('warnings_config.json', 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def save_warnings(self) -> None:
        """Сохранение предупреждений в файл."""
        with open('warnings.json', 'w', encoding='utf-8') as f:
            json.dump(self.warnings, f, indent=4)

    def get_user_warnings(self, guild_id: int, user_id: int) -> List[Dict]:
        """Получение предупреждений пользователя.
        
        Args:
            guild_id: ID сервера
            user_id: ID пользователя
            
        Returns:
            List[Dict]: Список предупреждений
        """
        guild_id = str(guild_id)
        user_id = str(user_id)
        
        if guild_id not in self.warnings:
            self.warnings[guild_id] = {}
        
        if user_id not in self.warnings[guild_id]:
            self.warnings[guild_id][user_id] = []
        
        return self.warnings[guild_id][user_id]

    def cleanup_expired_warnings(self, db) -> None:
        """Очистка устаревших предупреждений.
        
        Args:
            db: Сессия базы данных
        """
        current_time = datetime.utcnow()
        expiration_time = timedelta(days=30)  # Предупреждения истекают через 30 дней
        
        for guild_id in list(self.warnings.keys()):
            for user_id in list(self.warnings[guild_id].keys()):
                warnings = self.warnings[guild_id][user_id]
                active_warnings = []
                
                for warning in warnings:
                    warning_time = datetime.fromisoformat(warning["timestamp"])
                    if current_time - warning_time < expiration_time:
                        active_warnings.append(warning)
                
                if active_warnings:
                    self.warnings[guild_id][user_id] = active_warnings
                else:
                    del self.warnings[guild_id][user_id]
            
            if not self.warnings[guild_id]:
                del self.warnings[guild_id]
        
        self.save_warnings()

    @app_commands.command(name="warn_add", description="Выдать предупреждение участнику")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(
        member="Участник, которому нужно выдать предупреждение",
        reason="Причина предупреждения"
    )
    async def add_warning(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Причина не указана"):
        if member.bot:
            return await interaction.response.send_message(
                "Нельзя выдать предупреждение боту!",
                ephemeral=True
            )

        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message(
                "Вы не можете выдать предупреждение участнику с ролью выше или равной вашей!",
                ephemeral=True
            )

        warning = {
            "reason": reason,
            "moderator": interaction.user.id,
            "timestamp": datetime.utcnow().isoformat()
        }

        warnings = self.get_user_warnings(interaction.guild.id, member.id)
        warnings.append(warning)
        self.save_warnings()

        warning_count = len(warnings)
        
        embed = discord.Embed(
            title="Выдано предупреждение",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Участник", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="Модератор", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="Причина", value=reason, inline=False)
        embed.add_field(name="Всего предупреждений", value=str(warning_count), inline=False)

        await interaction.response.send_message(embed=embed)

        for threshold, punishment in sorted(self.config["punishments"].items(), key=lambda x: int(x[0])):
            if warning_count == int(threshold):
                if punishment == "mute_1h":
                    try:
                        await member.timeout(timedelta(hours=1), reason=f"Автоматический мут: {warning_count} предупреждений")
                        await interaction.followup.send(f"{member.mention} получает мут на 1 час за {warning_count} предупреждений")
                    except discord.Forbidden:
                        await interaction.followup.send("Не удалось выдать мут - недостаточно прав")
                
                elif punishment == "mute_12h":
                    try:
                        await member.timeout(timedelta(hours=12), reason=f"Автоматический мут: {warning_count} предупреждений")
                        await interaction.followup.send(f"{member.mention} получает мут на 12 часов за {warning_count} предупреждений")
                    except discord.Forbidden:
                        await interaction.followup.send("Не удалось выдать мут - недостаточно прав")
                
                elif punishment == "kick":
                    try:
                        await member.kick(reason=f"Автоматический кик: {warning_count} предупреждений")
                        await interaction.followup.send(f"{member.mention} был кикнут за {warning_count} предупреждений")
                    except discord.Forbidden:
                        await interaction.followup.send("Не удалось кикнуть участника - недостаточно прав")
                
                elif punishment == "ban":
                    try:
                        await member.ban(reason=f"Автоматический бан: {warning_count} предупреждений")
                        await interaction.followup.send(f"{member.mention} был забанен за {warning_count} предупреждений")
                    except discord.Forbidden:
                        await interaction.followup.send("Не удалось забанить участника - недостаточно прав")

    @app_commands.command(name="warn_remove", description="Удалить предупреждение у участника")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(
        member="Участник, у которого нужно удалить предупреждение",
        index="Номер предупреждения для удаления"
    )
    async def remove_warning(self, interaction: discord.Interaction, member: discord.Member, index: int):
        warnings = self.get_user_warnings(interaction.guild.id, member.id)
        
        if not warnings:
            return await interaction.response.send_message(
                "У этого участника нет предупреждений",
                ephemeral=True
            )
        
        if index < 1 or index > len(warnings):
            return await interaction.response.send_message(
                f"Укажите число от 1 до {len(warnings)}",
                ephemeral=True
            )
        
        removed = warnings.pop(index - 1)
        self.save_warnings()
        
        await interaction.response.send_message(f"Предупреждение #{index} было удалено у {member.mention}")

    @app_commands.command(name="warn_list", description="Показать список предупреждений участника")
    @app_commands.describe(member="Участник, чьи предупреждения нужно показать")
    async def list_warnings(self, interaction: discord.Interaction, member: discord.Member):
        warnings = self.get_user_warnings(interaction.guild.id, member.id)
        
        if not warnings:
            return await interaction.response.send_message(
                "У этого участника нет предупреждений",
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"Предупреждения | {member.display_name}",
            color=discord.Color.blue()
        )
        
        for i, warning in enumerate(warnings, 1):
            moderator = interaction.guild.get_member(warning["moderator"])
            mod_name = moderator.mention if moderator else "Модератор покинул сервер"
            
            embed.add_field(
                name=f"Предупреждение #{i}",
                value=f"**Причина:** {warning['reason']}\n**Модератор:** {mod_name}\n**Дата:** <t:{int(datetime.fromisoformat(warning['timestamp']).timestamp())}:R>",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warn_clear", description="Очистить все предупреждения участника")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(member="Участник, чьи предупреждения нужно очистить")
    async def clear_warnings(self, interaction: discord.Interaction, member: discord.Member):
        warnings = self.get_user_warnings(interaction.guild.id, member.id)
        
        if not warnings:
            return await interaction.response.send_message(
                "У этого участника нет предупреждений",
                ephemeral=True
            )
        
        self.warnings[str(interaction.guild.id)][str(member.id)] = []
        self.save_warnings()
        
        await interaction.response.send_message(f"Все предупреждения {member.mention} были удалены")

async def setup(bot):
    await bot.add_cog(WarningSystem(bot)) 