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
from database.db import get_db, get_redis, init_db, Database
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
        
        # Инициализация базы данных
        self.db = Database()
        
        # Инициализация модулей
        self.initial_extensions = [
            'cogs.events',
            'cogs.commands',
            'cogs.admin',
            'cogs.moderation',
            'cogs.voice',
            'cogs.tickets'
        ]
        self.use_metrics = os.getenv('USE_METRICS', 'False').lower() == 'true'
        
        # Инициализация систем бота
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
        
        # Пул соединений с базой
        self.db_pool = None
        
    async def setup_hook(self):
        """Инициализация бота при запуске."""
        try:
            # Инициализация базы данных
            await self.db.setup()
            
            # Загрузка когов
            for extension in self.initial_extensions:
                try:
                    await self.load_extension(extension)
                    logger.info(f"Загружен ког: {extension}")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке кога {extension}: {str(e)}")
                    capture_error(e)
            
            # Синхронизация команд с Discord
            logger.info('Синхронизация команд...')
            
            # Синхронизируем команды глобально
            await self.tree.sync()
            
            # Синхронизируем команды для каждого сервера
            for guild in self.guilds:
                try:
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                    logger.info(f'Команды синхронизированы для сервера: {guild.name}')
                except Exception as e:
                    logger.error(f'Ошибка при синхронизации команд для сервера {guild.name}: {str(e)}')
                    capture_error(e)
            
            logger.info('Все команды успешно синхронизированы!')
            
            # Запуск фоновых задач
            self.cleanup_tasks.start()
            self.update_metrics.start()
            
            # Инициализация метрик
            if self.use_metrics:
                metrics_port = int(os.getenv('METRICS_PORT', '8000'))
                start_metrics_server(metrics_port)
                
        except Exception as e:
            logger.error(f"Ошибка в setup_hook: {str(e)}")
            raise
        
    @tasks.loop(hours=1)
    async def cleanup_tasks(self):
        """Очистка временных данных и кэша."""
        try:
            with get_db() as db:
                self.warnings.cleanup_expired_warnings(db)
            
            await self.temp_voice.cleanup_inactive_channels()
            
            redis = get_redis()
            if redis:
                # Используем патерн ключа для очистки временных данных
                cursor = 0
                while True:
                    cursor, keys = redis.scan(cursor, match='temp_cache:*', count=100)
                    if keys:
                        redis.delete(*keys)
                    if cursor == 0:
                        break
            
        except Exception as e:
            logger.error(f"Error in cleanup tasks: {str(e)}")
            capture_error(e)
    
    @tasks.loop(minutes=5)
    async def update_metrics(self):
        """Обновление метрик бота."""
        if not self.use_metrics:
            return
            
        try:
            total_users = sum(guild.member_count for guild in self.guilds)
            update_active_users(total_users)
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            capture_error(e)
    
    async def on_message(self, message):
        """Обработка сообщений.
        
        Args:
            message: Объект сообщения
        """
        # Игнорируем сообщения от ботов
        if message.author.bot:
            return
            
        try:
            # Трекинг сообщения для метрик
            track_message()
            
            # Обработка сообщения системами бота
            await self.automod.check_message(message)
            await self.leveling.process_message(message)
            
            # Обработка команд
            await self.process_commands(message)
            
        except Exception as e:
            logger.error(f"Error in on_message: {str(e)}")
            capture_error(e, {'event': 'on_message'})
    
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
    try:
        load_dotenv()
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            raise ValueError("DISCORD_TOKEN не найден в .env файле")
        
        bot = Bot()
        await bot.start(token)
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {str(e)}")
        capture_error(e)

if __name__ == "__main__":
    asyncio.run(main()) 