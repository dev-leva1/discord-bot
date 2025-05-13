import discord
from discord import app_commands
from datetime import timedelta

class Moderation:
    def __init__(self, bot):
        self.bot = bot
        
    async def setup(self):
        # Регистрация команд модерации
        @self.bot.tree.command(name="ban", description="Забанить пользователя")
        @app_commands.checks.has_permissions(ban_members=True)
        async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
            if member.top_role >= interaction.user.top_role:
                await interaction.response.send_message("Вы не можете забанить участника с ролью выше или равной вашей!", ephemeral=True)
                return
                
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="Бан участника",
                description=f"Участник {member.mention} был забанен\nПричина: {reason or 'Не указана'}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            
        @self.bot.tree.command(name="kick", description="Выгнать пользователя")
        @app_commands.checks.has_permissions(kick_members=True)
        async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
            if member.top_role >= interaction.user.top_role:
                await interaction.response.send_message("Вы не можете выгнать участника с ролью выше или равной вашей!", ephemeral=True)
                return
                
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="Кик участника",
                description=f"Участник {member.mention} был выгнан\nПричина: {reason or 'Не указана'}",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            
        @self.bot.tree.command(name="mute", description="Замутить пользователя")
        @app_commands.checks.has_permissions(moderate_members=True)
        async def mute(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = None):
            if member.top_role >= interaction.user.top_role:
                await interaction.response.send_message("Вы не можете замутить участника с ролью выше или равной вашей!", ephemeral=True)
                return
                
            # Парсинг длительности
            try:
                duration_value = int(duration[:-1])
                duration_unit = duration[-1].lower()
                
                if duration_unit == 'm':
                    delta = timedelta(minutes=duration_value)
                elif duration_unit == 'h':
                    delta = timedelta(hours=duration_value)
                elif duration_unit == 'd':
                    delta = timedelta(days=duration_value)
                else:
                    raise ValueError
                    
            except ValueError:
                await interaction.response.send_message("Неверный формат длительности! Используйте число + m/h/d (например: 30m, 1h, 7d)", ephemeral=True)
                return
                
            await member.timeout(delta, reason=reason)
            embed = discord.Embed(
                title="Мут участника",
                description=f"Участник {member.mention} был замучен на {duration}\nПричина: {reason or 'Не указана'}",
                color=discord.Color.yellow()
            )
            await interaction.response.send_message(embed=embed)
            
        @self.bot.tree.command(name="clear", description="Очистить сообщения")
        @app_commands.checks.has_permissions(manage_messages=True)
        async def clear(interaction: discord.Interaction, amount: int):
            if amount < 1 or amount > 100:
                await interaction.response.send_message("Количество сообщений должно быть от 1 до 100!", ephemeral=True)
                return
                
            await interaction.channel.purge(limit=amount)
            embed = discord.Embed(
                title="Очистка сообщений",
                description=f"Удалено {amount} сообщений",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True) 