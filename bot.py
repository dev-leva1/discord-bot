import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import leveling_system
from datetime import datetime
from moderation import Moderation
from welcome import Welcome
from roles import RoleRewards
from automod import AutoMod
from logging_system import LoggingSystem
from image_generator import ImageGenerator
from tickets import TicketSystem
from temp_voice import TempVoice
from warning_system import WarningSystem
import os
from dotenv import load_dotenv
from database.db import init_db, get_db, get_redis
from utils.monitoring import start_metrics_server, monitor_command, track_message, update_active_users, capture_error
import asyncio
import logging

# Настройка логирования
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
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup(self):
        # Инициализация модулей
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
        
        # Загрузка когов
        for extension in ['cogs.events', 'cogs.commands']:
            try:
                await self.load_extension(extension)
                logger.info(f"Загружен ког: {extension}")
            except Exception as e:
                logger.error(f"Ошибка при загрузке кога {extension}: {str(e)}")
                capture_error(e)
        
        # Запуск фоновых задач
        self.cleanup_tasks.start()
        self.update_metrics.start()
        
    async def setup_hook(self):
        # Инициализация базы данных
        init_db()
        
        # Запуск метрик
        start_metrics_server()
        
        # Настройка модулей
        await self.setup()
        await self.tree.sync()
        
    @tasks.loop(hours=1)
    async def cleanup_tasks(self):
        try:
            # Очистка старых предупреждений
            with get_db() as db:
                self.warnings.cleanup_expired_warnings(db)
            
            # Очистка неактивных голосовых каналов
            await self.temp_voice.cleanup_inactive_channels()
            
            # Очистка кэша
            redis = get_redis()
            if redis:
                redis.delete('temp_cache:*')
            
        except Exception as e:
            logger.error(f"Error in cleanup tasks: {str(e)}")
            capture_error(e)
    
    @tasks.loop(minutes=5)
    async def update_metrics(self):
        try:
            total_users = sum(guild.member_count for guild in self.guilds)
            update_active_users(total_users)
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            capture_error(e)
    
    async def on_error(self, event_method, *args, **kwargs):
        error = args[0] if args else None
        logger.error(f"Error in {event_method}: {str(error)}")
        capture_error(error, {'event': event_method})
    
    async def on_command_error(self, ctx, error):
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