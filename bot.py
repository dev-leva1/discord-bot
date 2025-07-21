"""Основной модуль Discord бота."""

import asyncio
import logging
import os
import sys

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import leveling_system
from automod import AutoMod
from database.db import get_db, get_redis, Database
from image_generator import ImageGenerator
from logging_system import LoggingSystem
from moderation import Moderation
from roles import RoleRewards
from temp_voice import TempVoice
from tickets import TicketSystem
from utils.monitoring import (
    capture_error,
    start_metrics_server,
    track_message,
    update_active_users,
)
from warning_system import WarningSystem
from welcome import Welcome

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

# Настройка интентов Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = False  # Отключаем привилегированный интент members
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.voice_states = True
intents.presences = False  # Отключаем привилегированный интент presences
intents.moderation = True

class Bot(commands.Bot):
    """Основной класс бота."""
    
    def __init__(self):
        """Инициализация бота."""
        super().__init__(command_prefix='!', intents=intents)
        self.db = Database()
        self.initial_extensions = [
            'cogs.events',
            'cogs.commands',
            'cogs.admin',
            'cogs.moderation',
            'cogs.voice',
            'cogs.tickets'
        ]
        self.use_metrics = os.getenv('USE_METRICS', 'False').lower() == 'true'
        # Lazy-loaded modules
        self._moderation = None
        self._welcome = None
        self._role_rewards = None
        self._leveling = None
        self._automod = None
        self._logging = None
        self._image_generator = None
        self._tickets = None
        self._temp_voice = None
        self._warnings = None
        self.db_pool = None

    @property
    def moderation(self):
        if self._moderation is None:
            self._moderation = Moderation(self)
        return self._moderation

    @property
    def welcome(self):
        if self._welcome is None:
            self._welcome = Welcome(self)
        return self._welcome

    @property
    def role_rewards(self):
        if self._role_rewards is None:
            self._role_rewards = RoleRewards(self)
        return self._role_rewards

    @property
    def leveling(self):
        if self._leveling is None:
            self._leveling = leveling_system.init_leveling(self)
        return self._leveling

    @property
    def automod(self):
        if self._automod is None:
            self._automod = AutoMod(self)
        return self._automod

    @property
    def logging(self):
        if self._logging is None:
            self._logging = LoggingSystem(self)
        return self._logging

    @property
    def image_generator(self):
        if self._image_generator is None:
            self._image_generator = ImageGenerator()
        return self._image_generator

    @property
    def tickets(self):
        if self._tickets is None:
            self._tickets = TicketSystem(self)
        return self._tickets

    @property
    def temp_voice(self):
        if self._temp_voice is None:
            self._temp_voice = TempVoice(self)
        return self._temp_voice

    @property
    def warnings(self):
        if self._warnings is None:
            self._warnings = WarningSystem(self)
        return self._warnings
        
    async def setup_hook(self):
        """Инициализация бота при запуске."""
        try:
            logger.info("Начало инициализации бота...")
            
            # Инициализация базы данных
            logger.info("Инициализация базы данных...")
            await self.db.setup()
            logger.info("База данных успешно инициализирована")
            
            # Загрузка когов
            logger.info("Загрузка когов...")
            for extension in self.initial_extensions:
                try:
                    # Проверяем существование файла кога
                    cog_path = extension.replace('.', '/') + '.py'
                    if not os.path.exists(cog_path):
                        logger.warning(f"Файл кога {cog_path} не найден, пропускаем")
                        continue
                        
                    await self.load_extension(extension)
                    logger.info(f"Загружен ког: {extension}")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке кога {extension}: {str(e)}")
                    capture_error(e)
            
            # Синхронизация команд с Discord
            logger.info('Синхронизация команд...')
            
            try:
                # Сначала получаем существующие команды
                existing_commands = await self.http.get_global_commands(self.application_id)
                
                # Находим Entry Point команду, если она существует
                entry_point_command = next((cmd for cmd in existing_commands if cmd.get('name') == 'entry-point-command'), None)
                
                # Синхронизируем команды
                if entry_point_command is not None:
                    logger.info('Найдена Entry Point команда, сохраняем ее при синхронизации')
                    # Здесь можно обработать Entry Point команду, если нужно
                
                await self.tree.sync()
                logger.info('Глобальные команды синхронизированы')
            except Exception as e:
                logger.error(f'Ошибка при синхронизации глобальных команд: {str(e)}')
                capture_error(e)
            
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
            logger.info('Запуск фоновых задач...')
            self.cleanup_tasks.start()
            self.update_metrics.start()
            
            # Инициализация метрик
            if self.use_metrics:
                metrics_port = int(os.getenv('METRICS_PORT', '8000'))
                logger.info(f'Запуск сервера метрик на порту {metrics_port}...')
                start_metrics_server(metrics_port)
                
            logger.info("Инициализация бота завершена успешно!")
                
        except Exception as e:
            logger.error(f"Критическая ошибка в setup_hook: {str(e)}", exc_info=True)
            raise
        
    @tasks.loop(hours=1)
    async def cleanup_tasks(self):
        """Очистка временных данных и кэша."""
        try:
            logger.debug("Запуск задачи очистки временных данных...")
            
            # Очистка предупреждений
            with get_db() as db:
                self.warnings.cleanup_expired_warnings(db)
                logger.debug("Очистка устаревших предупреждений выполнена")
            
            # Очистка неактивных голосовых каналов
            await self.temp_voice.cleanup_inactive_channels()
            logger.debug("Очистка неактивных голосовых каналов выполнена")
            
            # Очистка кэша Redis
            redis = get_redis()
            if redis:
                # Используем паттерн ключа для очистки временных данных
                logger.debug("Очистка кэша Redis...")
                cursor = 0
                deleted_keys = 0
                while True:
                    cursor, keys = redis.scan(cursor, match='temp_cache:*', count=100)
                    if keys:
                        redis.delete(*keys)
                        deleted_keys += len(keys)
                    if cursor == 0:
                        break
                logger.debug(f"Очистка кэша Redis выполнена, удалено {deleted_keys} ключей")
            
            logger.debug("Задача очистки временных данных завершена")
            
        except Exception as e:
            logger.error(f"Ошибка в задаче cleanup_tasks: {str(e)}", exc_info=True)
            capture_error(e, {'task': 'cleanup_tasks'})
    
    @tasks.loop(minutes=5)
    async def update_metrics(self):
        """Обновление метрик бота."""
        if not self.use_metrics:
            return
            
        try:
            logger.debug("Обновление метрик...")
            
            # Общее количество пользователей во всех серверах
            total_users = sum(guild.member_count for guild in self.guilds)
            update_active_users(total_users)
            
            logger.debug(f"Метрики обновлены: {total_users} пользователей")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении метрик: {str(e)}", exc_info=True)
            capture_error(e, {'task': 'update_metrics'})
    
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
            guild_id = str(message.guild.id) if message.guild else 'dm'
            track_message(guild_id)
            
            # Обработка сообщения системами бота
            if hasattr(self, 'automod') and self.automod:
                await self.automod.check_message(message)
            
            if hasattr(self, 'leveling') and self.leveling:
                await self.leveling.process_message(message)
            
            # Обработка команд
            await self.process_commands(message)
            
        except Exception as e:
            logger.error(f"Ошибка в on_message: {str(e)}", exc_info=True)
            capture_error(e, {'event': 'on_message', 'channel': message.channel.id, 'author': message.author.id})
    
    async def on_error(self, event_method, *args, **kwargs):
        """Обработка ошибок событий бота.
        
        Args:
            event_method: Метод события
            *args: Аргументы
            **kwargs: Ключевые аргументы
        """
        error = args[0] if args else None
        logger.error(f"Ошибка в {event_method}: {str(error)}", exc_info=True)
        capture_error(error, {'event': event_method})
    
    async def on_command_error(self, ctx, error):
        """Обработка ошибок команд.
        
        Args:
            ctx: Контекст команды
            error: Ошибка
        """
        if isinstance(error, commands.CommandNotFound):
            return
        
        error_context = {
            'command': ctx.command.name if ctx.command else 'Unknown',
            'guild': ctx.guild.id if ctx.guild else None,
            'channel': ctx.channel.id,
            'user': ctx.author.id,
            'message': ctx.message.content if ctx.message else None
        }
        
        # Логирование ошибки
        logger.error(f"Ошибка команды: {str(error)}", exc_info=True)
        capture_error(error, error_context)
        
        # Отправляем сообщение об ошибке пользователю
        error_message = str(error)
        
        # Перехватываем и форматируем распространенные ошибки для улучшения UX
        if isinstance(error, commands.MissingPermissions):
            error_message = "У вас недостаточно прав для выполнения этой команды."
        elif isinstance(error, commands.BotMissingPermissions):
            error_message = "У бота недостаточно прав для выполнения этой команды."
        elif isinstance(error, commands.BadArgument):
            error_message = "Неверные аргументы команды. Проверьте правильность ввода."
        elif isinstance(error, commands.MissingRequiredArgument):
            error_message = f"Отсутствует обязательный аргумент: {error.param.name}"
        
        await ctx.send(f"Произошла ошибка при выполнении команды: {error_message}", ephemeral=True)

    @cleanup_tasks.before_loop
    @update_metrics.before_loop
    async def before_tasks(self):
        """Ожидание, пока бот будет готов перед запуском задач."""
        await self.wait_until_ready()
        logger.info("Бот готов, запуск фоновых задач...")

async def main():
    """Основная функция запуска бота."""
    try:
        # Загрузка переменных окружения
        load_dotenv()
        logger.info("Загружены переменные окружения")
        
        # Проверка обязательных переменных окружения
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.critical("DISCORD_TOKEN не найден в .env файле")
            raise ValueError("DISCORD_TOKEN не найден в .env файле")
        
        logger.info("Токен Discord найден, запуск бота...")
        
        # Создание и запуск бота
        bot = Bot()
        await bot.start(token)
        
    except discord.errors.LoginFailure as e:
        logger.critical(f"Ошибка авторизации в Discord: {str(e)}")
        logger.critical("Пожалуйста, проверьте правильность токена Discord в файле .env")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {str(e)}", exc_info=True)
        capture_error(e)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Необработанная ошибка: {str(e)}", exc_info=True)
        sys.exit(1) 