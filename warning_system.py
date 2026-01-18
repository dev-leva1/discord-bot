"""Модуль системы предупреждений."""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Dict, List, Union

from infrastructure.config import WarningsConfigStore, WarningsStore

from application.contracts import WarningsRepositoryContract, WarningsServiceContract

class WarningSystem(commands.Cog, WarningsServiceContract):
    def __init__(
        self,
        bot,
        repository: WarningsRepositoryContract | None = None,
        store: WarningsStore | None = None,
        config_store: WarningsConfigStore | None = None,
    ):
        self.bot = bot
        self.repository = repository
        self.store = store or WarningsStore()
        self.config_store = config_store or WarningsConfigStore()
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
        return self.store.load()

    def load_config(self) -> Dict:
        """Загрузка конфигурации из файла.
        
        Returns:
            Dict: Загруженная конфигурация
        """
        return self.config_store.load()

    async def migrate_to_db(self) -> None:
        """Миграция предупреждений из JSON в БД."""

        if not self.repository:
            return

        await self.repository.migrate_from_json(self.warnings)

    def save_warnings(self) -> None:
        """Сохранение предупреждений в файл."""
        self.store.save(self.warnings)

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

    async def cleanup_expired_warnings(self, db) -> None:
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
        if self.repository:
            await self.repository.cleanup_expired(days=30)

    @commands.hybrid_command(name="warn_add", description="Выдать предупреждение участнику")
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(
        member="Участник, которому нужно выдать предупреждение",
        reason="Причина предупреждения"
    )
    async def add_warning(self, ctx: Union[commands.Context, discord.Interaction], member: discord.Member, reason: str = "Причина не указана"):
        """Выдать предупреждение участнику."""
        is_interaction = isinstance(ctx, discord.Interaction)
        
        if member.bot:
            response = "Нельзя выдать предупреждение боту!"
            return await (ctx.response.send_message if is_interaction else ctx.send)(response, ephemeral=True)

        if member.top_role >= ctx.user.top_role:
            response = "Вы не можете выдать предупреждение участнику с ролью выше или равной вашей!"
            return await (ctx.response.send_message if is_interaction else ctx.send)(response, ephemeral=True)

        warning = {
            "reason": reason,
            "moderator": ctx.user.id,
            "timestamp": datetime.utcnow().isoformat()
        }

        warnings = self.get_user_warnings(ctx.guild.id, member.id)
        warnings.append(warning)
        self.save_warnings()
        if self.repository:
            await self.repository.add_warning(
                ctx.guild.id,
                member.id,
                reason,
                ctx.user.id,
                warning["timestamp"],
                None,
            )

        warning_count = len(warnings)
        
        embed = discord.Embed(
            title="Выдано предупреждение",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Участник", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="Модератор", value=f"{ctx.user.mention}", inline=False)
        embed.add_field(name="Причина", value=reason, inline=False)
        embed.add_field(name="Всего предупреждений", value=str(warning_count), inline=False)

        await (ctx.response.send_message if is_interaction else ctx.send)(embed=embed)

        send_followup = ctx.followup.send if is_interaction else ctx.send
        
        for threshold, punishment in sorted(self.config["punishments"].items(), key=lambda x: int(x[0])):
            if warning_count == int(threshold):
                if punishment == "mute_1h":
                    try:
                        await member.timeout(timedelta(hours=1), reason=f"Автоматический мут: {warning_count} предупреждений")
                        await send_followup(f"{member.mention} получает мут на 1 час за {warning_count} предупреждений")
                    except discord.Forbidden:
                        await send_followup("Не удалось выдать мут - недостаточно прав")
                
                elif punishment == "mute_12h":
                    try:
                        await member.timeout(timedelta(hours=12), reason=f"Автоматический мут: {warning_count} предупреждений")
                        await send_followup(f"{member.mention} получает мут на 12 часов за {warning_count} предупреждений")
                    except discord.Forbidden:
                        await send_followup("Не удалось выдать мут - недостаточно прав")
                
                elif punishment == "kick":
                    try:
                        await member.kick(reason=f"Автоматический кик: {warning_count} предупреждений")
                        await send_followup(f"{member.mention} был кикнут за {warning_count} предупреждений")
                    except discord.Forbidden:
                        await send_followup("Не удалось кикнуть участника - недостаточно прав")
                
                elif punishment == "ban":
                    try:
                        await member.ban(reason=f"Автоматический бан: {warning_count} предупреждений")
                        await send_followup(f"{member.mention} был забанен за {warning_count} предупреждений")
                    except discord.Forbidden:
                        await send_followup("Не удалось забанить участника - недостаточно прав")

    @commands.hybrid_command(name="warn_remove", description="Удалить предупреждение у участника")
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(
        member="Участник, у которого нужно удалить предупреждение",
        index="Номер предупреждения для удаления"
    )
    async def remove_warning(self, ctx: Union[commands.Context, discord.Interaction], member: discord.Member, index: int):
        """Удалить предупреждение у участника."""
        is_interaction = isinstance(ctx, discord.Interaction)
        warnings = self.get_user_warnings(ctx.guild.id, member.id)
        
        if not warnings:
            response = "У этого участника нет предупреждений"
            return await (ctx.response.send_message if is_interaction else ctx.send)(response, ephemeral=True)
        
        if index < 1 or index > len(warnings):
            response = f"Укажите число от 1 до {len(warnings)}"
            return await (ctx.response.send_message if is_interaction else ctx.send)(response, ephemeral=True)
        
        removed = warnings.pop(index - 1)
        self.save_warnings()
        if self.repository:
            listed = await self.repository.list_warnings(ctx.guild.id, member.id)
            if 0 <= index - 1 < len(listed):
                await self.repository.delete_warning(listed[index - 1]["id"])
        
        await (ctx.response.send_message if is_interaction else ctx.send)(f"Предупреждение #{index} было удалено у {member.mention}: \"{removed['reason']}\"")

    @commands.hybrid_command(name="warn_list", description="Показать список предупреждений участника")
    @app_commands.describe(member="Участник, чьи предупреждения нужно показать")
    async def list_warnings(self, ctx: Union[commands.Context, discord.Interaction], member: discord.Member):
        """Показать список предупреждений участника."""
        is_interaction = isinstance(ctx, discord.Interaction)
        warnings = self.get_user_warnings(ctx.guild.id, member.id)
        
        if not warnings:
            response = "У этого участника нет предупреждений"
            return await (ctx.response.send_message if is_interaction else ctx.send)(response, ephemeral=True)
        
        embed = discord.Embed(
            title=f"Предупреждения | {member.display_name}",
            color=discord.Color.blue()
        )
        
        for i, warning in enumerate(warnings, 1):
            moderator = ctx.guild.get_member(warning["moderator"])
            mod_name = moderator.mention if moderator else "Модератор покинул сервер"
            
            embed.add_field(
                name=f"Предупреждение #{i}",
                value=f"**Причина:** {warning['reason']}\n**Модератор:** {mod_name}\n**Дата:** <t:{int(datetime.fromisoformat(warning['timestamp']).timestamp())}:R>",
                inline=False
            )
        
        await (ctx.response.send_message if is_interaction else ctx.send)(embed=embed)

    @commands.hybrid_command(name="warn_clear", description="Очистить все предупреждения участника")
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(member="Участник, чьи предупреждения нужно очистить")
    async def clear_warnings(self, ctx: Union[commands.Context, discord.Interaction], member: discord.Member):
        """Очистить все предупреждения участника."""
        is_interaction = isinstance(ctx, discord.Interaction)
        warnings = self.get_user_warnings(ctx.guild.id, member.id)
        
        if not warnings:
            response = "У этого участника нет предупреждений"
            return await (ctx.response.send_message if is_interaction else ctx.send)(response, ephemeral=True)
        
        self.warnings[str(ctx.guild.id)][str(member.id)] = []
        self.save_warnings()
        if self.repository:
            await self.repository.clear_user_warnings(ctx.guild.id, member.id)
        
        await (ctx.response.send_message if is_interaction else ctx.send)(f"Все предупреждения {member.mention} были удалены")

async def setup(bot):
    await bot.add_cog(WarningSystem(bot)) 
