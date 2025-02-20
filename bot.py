import discord
from discord import app_commands
from discord.ext import commands
import json
import leveling_system
from datetime import datetime
from moderation import Moderation
from welcome import Welcome
from roles import RoleRewards
from automod import AutoMod
from logging_system import LoggingSystem
from image_generator import ImageGenerator
import os
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.moderation = Moderation(self)
        self.welcome = Welcome(self)
        self.role_rewards = RoleRewards(self)
        self.leveling = leveling_system.init_leveling(self)
        self.automod = AutoMod(self)
        self.logging = LoggingSystem(self)
        self.image_generator = ImageGenerator()
        
    async def setup_hook(self):
        await self.moderation.setup()
        await self.welcome.setup()
        await self.role_rewards.setup()
        await self.automod.setup()
        await self.logging.setup()
        await self.tree.sync()
        
bot = Bot()

@bot.event
async def on_ready():
    print(f'{bot.user} запущен и готов к работе!')
    print('Slash-команды:')
    print('/rank - Показать ваш уровень')
    print('/leaderboard - Таблица лидеров')
    print('/help - Список команд')
    print('/ban - Забанить пользователя')
    print('/kick - Выгнать пользователя')
    print('/mute - Замутить пользователя')
    print('/clear - Очистить сообщения')
    print('/setwelcome - Установить канал приветствий')
    print('/addrole - Добавить роль за уровень')
    print('/removerole - Удалить роль за уровень')
    print('/listroles - Список ролей за уровни')
    print('/automod - Настройка автомодерации')
    print('/setlogs - Установить канал для логов')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
        
    # Проверка автомодерации (пропускаем для владельца сервера)
    if message.author.id != message.guild.owner_id:
        if not await bot.automod.check_message(message):
            return
        
    await leveling_system.add_experience(message.author.id, message.guild.id)
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    await bot.logging.log_message_delete(message)

@bot.event
async def on_message_edit(before, after):
    await bot.logging.log_message_edit(before, after)

@bot.event
async def on_member_join(member):
    await bot.logging.log_member_join(member)
    await bot.welcome.send_welcome(member)

@bot.event
async def on_member_remove(member):
    await bot.logging.log_member_remove(member)

@bot.event
async def on_member_update(before, after):
    await bot.logging.log_member_update(before, after)

@bot.event
async def on_voice_state_update(member, before, after):
    await bot.logging.log_voice_state_update(member, before, after)

@bot.event
async def on_member_ban(guild, user):
    await bot.logging.log_ban(guild, user)

@bot.event
async def on_member_unban(guild, user):
    await bot.logging.log_unban(guild, user)

# Slash команды
@bot.tree.command(name="rank", description="Показывает ваш текущий уровень и опыт")
async def rank(interaction: discord.Interaction):
    level, xp = await leveling_system.get_level_xp(interaction.user.id, interaction.guild.id)
    next_level_xp = bot.leveling.get_xp_for_level(level)
    
    # Создаем красивую карточку
    rank_card = await bot.image_generator.create_rank_card(
        interaction.user,
        level,
        xp,
        next_level_xp
    )
    
    await interaction.response.send_message(file=rank_card)

@bot.tree.command(name="leaderboard", description="Показывает таблицу лидеров по уровням")
async def leaderboard(interaction: discord.Interaction):
    leaders_data = await leveling_system.get_leaderboard(interaction.guild.id)
    
    if not leaders_data:
        await interaction.response.send_message("На сервере пока нет участников с опытом!", ephemeral=True)
        return
        
    # Преобразуем данные для генератора изображений
    leaders = []
    for data in leaders_data:
        user = interaction.guild.get_member(int(data["user_id"]))
        if user:
            leaders.append((user, data["level"], data["xp"]))
            
    # Создаем красивую карточку лидерборда
    leaderboard_card = await bot.image_generator.create_leaderboard_card(
        interaction.guild.name,
        leaders
    )
    
    await interaction.response.send_message(file=leaderboard_card)

@bot.tree.command(name="help", description="Показывает список доступных команд")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Помощь по командам",
        description="Список всех доступных команд:",
        color=discord.Color.blue()
    )
    
    # Проверяем права пользователя
    is_owner = interaction.guild.owner_id == interaction.user.id
    show_admin_commands = is_owner or interaction.user.guild_permissions.administrator
    show_mod_commands = show_admin_commands or interaction.user.guild_permissions.ban_members
    
    # Основные команды (доступны всем)
    embed.add_field(
        name="📊 Уровни и опыт", 
        value="""
• `/rank` - Показать ваш текущий уровень и опыт
• `/leaderboard` - Таблица лидеров сервера
        """, 
        inline=False
    )
    
    # Команды модерации
    if show_mod_commands:
        embed.add_field(
            name="🛡️ Модерация",
            value="""
• `/ban` - Забанить пользователя
• `/kick` - Выгнать пользователя
• `/mute` - Временно замутить пользователя
• `/clear` - Очистить сообщения в канале
            """,
            inline=False
        )
        
    # Команды автомодерации
    if show_admin_commands:
        embed.add_field(
            name="🤖 Автомодерация",
            value="""
• `/automod addword` - Добавить запрещенное слово
• `/automod removeword` - Удалить запрещенное слово
• `/automod listwords` - Список запрещенных слов
• `/automod setspam` - Установить порог спама
• `/automod setinterval` - Установить интервал спама
• `/automod setmentions` - Установить лимит упоминаний
• `/automod setwarnings` - Установить максимум предупреждений
• `/automod setmute` - Установить длительность мута
            """,
            inline=False
        )
    
    # Настройки сервера
    if show_admin_commands:
        embed.add_field(
            name="⚙️ Настройки сервера",
            value="""
• `/setwelcome` - Установить канал приветствий
• `/setlogs` - Установить канал для логов
            """,
            inline=False
        )
        
    # Настройки ролей
    if show_admin_commands:
        embed.add_field(
            name="👥 Управление ролями",
            value="""
• `/addrole` - Добавить роль-награду за уровень
• `/removerole` - Удалить роль-награду
• `/listroles` - Список ролей-наград за уровни
            """,
            inline=False
        )
    
    # Добавляем информацию о правах
    if is_owner:
        embed.set_footer(text="👑 Показаны все команды (вы владелец сервера)")
    elif not show_admin_commands:
        embed.set_footer(text="ℹ️ Некоторые команды скрыты, так как у вас недостаточно прав")
    
    await interaction.response.send_message(embed=embed)

# Загружаем токен из .env файла
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN) 