import discord
from discord import app_commands
import json
from pathlib import Path
from datetime import datetime

class LoggingSystem:
    def __init__(self, bot):
        self.bot = bot
        self.config_file = Path("logging_config.json")
        self.load_config()
        
    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {}
            
    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)
            
    async def setup(self):
        @self.bot.tree.command(
            name="setlogs",
            description="Установить канал для логов"
        )
        @app_commands.checks.has_permissions(manage_guild=True)
        @app_commands.describe(
            channel="Выберите канал для логов из списка"
        )
        async def setlogs(
            interaction: discord.Interaction,
            channel: discord.TextChannel
        ):
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    "Пожалуйста, выберите текстовый канал из списка!",
                    ephemeral=True
                )
                return
                
            # Проверяем права бота в канале
            permissions = channel.permissions_for(interaction.guild.me)
            if not (permissions.send_messages and permissions.embed_links):
                await interaction.response.send_message(
                    f"У меня нет прав для отправки сообщений и эмбедов в канале {channel.mention}!",
                    ephemeral=True
                )
                return
                
            guild_id = str(interaction.guild.id)
            self.config[guild_id] = channel.id
            self.save_config()
            
            embed = discord.Embed(
                title="✅ Настройка логов",
                description=f"Канал для логов установлен: {channel.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
    async def log_event(self, guild, title, description, color=discord.Color.blue(), fields=None, author=None):
        if str(guild.id) not in self.config:
            return
            
        channel = guild.get_channel(self.config[str(guild.id)])
        if not channel:
            return
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
                
        if author:
            embed.set_footer(text=f"Действие выполнил: {author}")
            
        try:
            await channel.send(embed=embed)
        except:
            pass
            
    async def log_message_delete(self, message):
        if not message.guild:
            return
            
        await self.log_event(
            message.guild,
            "🗑️ Сообщение удалено",
            f"**Канал:** {message.channel.mention}\n**Автор:** {message.author.mention}\n**Содержание:**\n{message.content}",
            discord.Color.red(),
            author=message.author
        )
        
    async def log_message_edit(self, before, after):
        if not before.guild:
            return
            
        if before.content == after.content:
            return
            
        await self.log_event(
            before.guild,
            "✏️ Сообщение изменено",
            f"**Канал:** {before.channel.mention}\n**Автор:** {before.author.mention}",
            discord.Color.gold(),
            fields=[
                ("До:", before.content, False),
                ("После:", after.content, False)
            ],
            author=before.author
        )
        
    async def log_member_join(self, member):
        await self.log_event(
            member.guild,
            "👋 Участник присоединился",
            f"**Участник:** {member.mention}\n**ID:** {member.id}",
            discord.Color.green()
        )
        
    async def log_member_remove(self, member):
        await self.log_event(
            member.guild,
            "👋 Участник покинул сервер",
            f"**Участник:** {member}\n**ID:** {member.id}",
            discord.Color.red()
        )
        
    async def log_member_update(self, before, after):
        if before.roles != after.roles:
            # Находим измененные роли
            removed_roles = set(before.roles) - set(after.roles)
            added_roles = set(after.roles) - set(before.roles)
            
            description = f"**Участник:** {after.mention}\n"
            if added_roles:
                description += f"**Добавлены роли:** {', '.join(role.mention for role in added_roles)}\n"
            if removed_roles:
                description += f"**Удалены роли:** {', '.join(role.mention for role in removed_roles)}"
                
            # Получаем информацию о том, кто изменил роли из аудит лога
            try:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        author = entry.user
                        break
                else:
                    author = None
            except (discord.Forbidden, discord.HTTPException):
                author = None
                
            await self.log_event(
                after.guild,
                "👥 Роли участника изменены",
                description,
                discord.Color.blue(),
                author=author
            )
            
    async def log_voice_state_update(self, member, before, after):
        if before.channel != after.channel:
            if after.channel:
                description = f"**Участник:** {member.mention}\n**Подключился к:** {after.channel.name}"
                title = "🎤 Подключение к голосовому каналу"
            else:
                description = f"**Участник:** {member.mention}\n**Отключился от:** {before.channel.name}"
                title = "🎤 Отключение от голосового канала"
                
            await self.log_event(
                member.guild,
                title,
                description,
                discord.Color.blue(),
                author=member
            )
            
    async def log_ban(self, guild, user):
        # Получаем информацию о том, кто забанил участника
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    author = entry.user
                    reason = entry.reason
                    break
            else:
                author = None
                reason = "Причина не указана"
        except (discord.Forbidden, discord.HTTPException):
            author = None
            reason = "Причина не указана"
            
        await self.log_event(
            guild,
            "🔨 Участник забанен",
            f"**Участник:** {user}\n**ID:** {user.id}\n**Причина:** {reason}",
            discord.Color.red(),
            author=author
        )
        
    async def log_unban(self, guild, user):
        # Получаем информацию о том, кто разбанил участника
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    author = entry.user
                    break
            else:
                author = None
        except (discord.Forbidden, discord.HTTPException):
            author = None
            
        await self.log_event(
            guild,
            "🔓 Участник разбанен",
            f"**Участник:** {user}\n**ID:** {user.id}",
            discord.Color.green(),
            author=author
        ) 