import discord
from discord import app_commands
import json
from pathlib import Path

class Welcome:
    def __init__(self, bot):
        self.bot = bot
        self.config_file = Path("welcome_config.json")
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
            name="setwelcome",
            description="Установить канал для приветствий"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def setwelcome(
            interaction: discord.Interaction,
            channel: discord.TextChannel
        ):
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    "Пожалуйста, выберите текстовый канал!",
                    ephemeral=True
                )
                return
                
            # Проверяем права бота
            if not channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message(
                    "У меня нет прав для отправки сообщений в этот канал!",
                    ephemeral=True
                )
                return
                
            if not channel.permissions_for(interaction.guild.me).embed_links:
                await interaction.response.send_message(
                    "У меня нет прав для отправки эмбедов в этот канал!",
                    ephemeral=True
                )
                return
                
            self.config[str(interaction.guild.id)] = channel.id
            self.save_config()
            
            embed = discord.Embed(
                title="✅ Канал приветствий установлен",
                description=f"Приветствия будут отправляться в канал {channel.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
    async def send_welcome(self, member):
        if str(member.guild.id) not in self.config:
            return
            
        channel = member.guild.get_channel(self.config[str(member.guild.id)])
        if not channel:
            return
            
        # Создаем красивую карточку приветствия
        welcome_card = await self.bot.image_generator.create_welcome_card(member, member.guild)
        
        # Отправляем сообщение с карточкой
        try:
            await channel.send(file=welcome_card)
        except:
            pass 