"""Основной модуль Discord бота."""

import asyncio
import json
import logging
import os
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import leveling_system
from automod import AutoMod
from database.db import get_db, get_redis, init_db
from image_generator import ImageGenerator
from logging_system import LoggingSystem
from moderation import Moderation
from roles import RoleRewards
from temp_voice import TempVoice
from tickets import TicketSystem
from utils.monitoring import (
    capture_error,
    monitor_command,
    start_metrics_server,
    track_message,
    update_active_users,
)
from warning_system import WarningSystem
from welcome import Welcome

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.voice_states = True
intents.presences = True
intents.moderation = True

class Bot(commands.Bot):
    """Основной класс бота."""
    
    def __init__(self):
        """Инициализация бота."""
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup(self):
        """Настройка и инициализация модулей бота."""
        self.moderation = Moderation(self)
        self.welcome = Welcome(self)
        self.role_rewards = RoleRewards(self)
        self.leveling = leveling_system.init_leveling(self)
        self.automod = AutoMod(self)
        self.logging = LoggingSystem(self)
        self.image_generator = ImageGenerator()
        self.tickets = TicketSystem(self)
        self.temp_voice = TempVoice(self)
        self.warnings = WarningSystem(self)
        
        for extension in ['cogs.events', 'cogs.commands']:
            try:
                await self.load_extension(extension)
                logger.info(f"Загружен ког: {extension}")
            except Exception as e:
                logger.error(f"Ошибка при загрузке кога {extension}: {str(e)}")
                capture_error(e)
        
        self.cleanup_tasks.start()
        self.update_metrics.start()
        
    async def setup_hook(self):
        """Дополнительная настройка при запуске бота."""
        init_db()
        
        start_metrics_server()
        
        await self.setup()
        await self.tree.sync()
        
    @tasks.loop(hours=1)
    async def cleanup_tasks(self):
        """Очистка временных данных и кэша."""
        try:
            with get_db() as db:
                self.warnings.cleanup_expired_warnings(db)
            
            await self.temp_voice.cleanup_inactive_channels()
            
            redis = get_redis()
            if redis:
                redis.delete('temp_cache:*')
            
        except Exception as e:
            logger.error(f"Error in cleanup tasks: {str(e)}")
            capture_error(e)
    
    @tasks.loop(minutes=5)
    async def update_metrics(self):
        """Обновление метрик бота."""
        try:
            total_users = sum(guild.member_count for guild in self.guilds)
            update_active_users(total_users)
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            capture_error(e)
    
    async def on_error(self, event_method, *args, **kwargs):
        """Обработка ошибок событий бота.
        
        Args:
            event_method: Метод события
            *args: Аргументы
            **kwargs: Ключевые аргументы
        """
        error = args[0] if args else None
        logger.error(f"Error in {event_method}: {str(error)}")
        capture_error(error, {'event': event_method})
    
    async def on_command_error(self, ctx, error):
        """Обработка ошибок команд.
        
        Args:
            ctx: Контекст команды
            error: Ошибка
        """
        if isinstance(error, commands.CommandNotFound):
            return
        
        logger.error(f"Command error: {str(error)}")
        capture_error(error, {
            'command': ctx.command.name if ctx.command else 'Unknown',
            'guild': ctx.guild.id if ctx.guild else None,
            'channel': ctx.channel.id,
            'user': ctx.author.id
        })
        
        await ctx.send(f"Произошла ошибка при выполнении команды: {str(error)}")

async def main():
    """Основная функция запуска бота."""
    async with Bot() as bot:
        try:
            load_dotenv()
            token = os.getenv('DISCORD_TOKEN')
            if not token:
                raise ValueError("DISCORD_TOKEN не найден в .env файле")
            
            await bot.start(token)
        except Exception as e:
            logger.critical(f"Критическая ошибка при запуске бота: {str(e)}")
            capture_error(e)

if __name__ == "__main__":
    asyncio.run(main()) 