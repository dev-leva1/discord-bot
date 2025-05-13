import discord
from discord import app_commands
from discord.ext import commands
import json

class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_config = self.load_config()
        self.temp_channels = {}

    async def setup(self):
        """Инициализация системы временных голосовых каналов"""
        print("Система временных голосовых каналов готова к работе")

    def load_config(self):
        try:
            with open('voice_config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "creation_channel": None,
                "temp_category": None
            }
            with open('voice_config.json', 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def save_config(self):
        with open('voice_config.json', 'w') as f:
            json.dump(self.voice_config, f, indent=4)

    @app_commands.command(name="voice_setup", description="Настроить систему временных голосовых каналов")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(category="Категория для временных голосовых каналов")
    async def setup_voice(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        creation_channel = await interaction.guild.create_voice_channel(
            "➕ Создать канал",
            category=category
        )
        
        self.voice_config["creation_channel"] = creation_channel.id
        self.voice_config["temp_category"] = category.id
        self.save_config()
        
        await interaction.response.send_message(
            f"Система временных голосовых каналов настроена в категории {category.name}"
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel and after.channel.id == self.voice_config["creation_channel"]:
            category = self.bot.get_channel(self.voice_config["temp_category"])
            
            channel = await member.guild.create_voice_channel(
                f"Канал {member.display_name}",
                category=category
            )
            
            await member.move_to(channel)
            self.temp_channels[channel.id] = member.id

            # Даем создателю права на управление каналом
            await channel.set_permissions(member, 
                manage_channels=True,
                move_members=True,
                manage_permissions=True
            )
        
        if before.channel and before.channel.id in self.temp_channels:
            if len(before.channel.members) == 0:
                await before.channel.delete()
                del self.temp_channels[before.channel.id]

    @app_commands.command(name="voice_limit", description="Установить лимит пользователей в канале")
    @app_commands.describe(limit="Максимальное количество пользователей (0 - без лимита)")
    async def set_limit(self, interaction: discord.Interaction, limit: int):
        if not interaction.user.voice or interaction.user.voice.channel.id not in self.temp_channels:
            return await interaction.response.send_message(
                "Вы должны находиться в своем временном канале!",
                ephemeral=True
            )
        
        if self.temp_channels[interaction.user.voice.channel.id] != interaction.user.id:
            return await interaction.response.send_message(
                "Это не ваш канал!",
                ephemeral=True
            )
        
        await interaction.user.voice.channel.edit(user_limit=limit)
        await interaction.response.send_message(f"Установлен лимит пользователей: {limit}")

    @app_commands.command(name="voice_name", description="Изменить название канала")
    @app_commands.describe(new_name="Новое название канала")
    async def set_name(self, interaction: discord.Interaction, new_name: str):
        if not interaction.user.voice or interaction.user.voice.channel.id not in self.temp_channels:
            return await interaction.response.send_message(
                "Вы должны находиться в своем временном канале!",
                ephemeral=True
            )
        
        if self.temp_channels[interaction.user.voice.channel.id] != interaction.user.id:
            return await interaction.response.send_message(
                "Это не ваш канал!",
                ephemeral=True
            )
        
        await interaction.user.voice.channel.edit(name=new_name)
        await interaction.response.send_message(f"Название канала изменено на: {new_name}")

    @app_commands.command(name="voice_lock", description="Закрыть канал")
    async def lock_channel(self, interaction: discord.Interaction):
        if not interaction.user.voice or interaction.user.voice.channel.id not in self.temp_channels:
            return await interaction.response.send_message(
                "Вы должны находиться в своем временном канале!",
                ephemeral=True
            )
        
        if self.temp_channels[interaction.user.voice.channel.id] != interaction.user.id:
            return await interaction.response.send_message(
                "Это не ваш канал!",
                ephemeral=True
            )
        
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("Канал закрыт")

    @app_commands.command(name="voice_unlock", description="Открыть канал")
    async def unlock_channel(self, interaction: discord.Interaction):
        if not interaction.user.voice or interaction.user.voice.channel.id not in self.temp_channels:
            return await interaction.response.send_message(
                "Вы должны находиться в своем временном канале!",
                ephemeral=True
            )
        
        if self.temp_channels[interaction.user.voice.channel.id] != interaction.user.id:
            return await interaction.response.send_message(
                "Это не ваш канал!",
                ephemeral=True
            )
        
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("Канал открыт")

    async def cleanup_inactive_channels(self):
        """Очистка неактивных временных голосовых каналов"""
        if not self.temp_channels:
            return
            
        # Создаем копию словаря, чтобы избежать ошибок при изменении в цикле
        temp_channels_copy = self.temp_channels.copy()
        
        for channel_id, owner_id in temp_channels_copy.items():
            channel = self.bot.get_channel(channel_id)
            if not channel:
                # Канал был удален, удаляем из словаря
                if channel_id in self.temp_channels:
                    del self.temp_channels[channel_id]
                continue
                
            # Проверяем, есть ли пользователи в канале
            if len(channel.members) == 0:
                try:
                    await channel.delete(reason="Автоматическая очистка неактивных каналов")
                    if channel_id in self.temp_channels:
                        del self.temp_channels[channel_id]
                except discord.HTTPException:
                    pass  # Игнорируем ошибки при удалении канала

async def setup(bot):
    await bot.add_cog(TempVoice(bot)) 