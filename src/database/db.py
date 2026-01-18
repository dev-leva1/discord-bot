"""Модуль для работы с базой данных."""

import os
import sqlite3
from contextlib import contextmanager, asynccontextmanager
import redis
import aiosqlite
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с базой данных."""
    
    def __init__(self):
        """Инициализация подключения к базе данных."""
        self.db_path = os.getenv("DB_PATH", os.path.join("data", "bot.db"))
        self.redis_url = os.getenv("REDIS_URL")
        self.redis = None
        self.pool = None
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '5'))
        
    async def setup(self):
        """Настройка базы данных."""
        # Инициализация SQLite
        await self._init_sqlite()
        
        # Инициализация Redis если доступен
        await self._init_redis()
        
    async def _init_sqlite(self):
        """Инициализация SQLite базы данных."""
        try:
            # Проверяем существование файла базы данных
            db_exists = os.path.exists(self.db_path)
            
            # Сначала выполняем начальную инициализацию, если база не существует
            if not db_exists:
                # Создаем файл базы данных и таблицы
                init_db()
                logger.info(f"База данных {self.db_path} создана")
            
            # Создаем пул соединений
            self.pool = []
            for _ in range(self.pool_size):
                conn = await aiosqlite.connect(self.db_path)
                # Включаем поддержку внешних ключей
                await conn.execute("PRAGMA foreign_keys = ON")
                self.pool.append(conn)
            
            # Проверка структуры базы и обновление схемы, если необходимо
            await self._check_and_update_schema()
            
            logger.info("База данных SQLite успешно инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка при инициализации SQLite: {str(e)}")
            raise
            
    async def _check_and_update_schema(self):
        """Проверка и обновление схемы базы данных."""
        async with self.get_connection() as conn:
            # Получаем список существующих таблиц
            cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = await cursor.fetchall()
            tables = [table[0] for table in tables]
            
            # Создаем необходимые таблицы, если они не существуют
            if 'levels' not in tables:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS levels (
                        user_id INTEGER,
                        guild_id INTEGER,
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 0,
                        last_message_time TIMESTAMP,
                        PRIMARY KEY (user_id, guild_id)
                    )
                ''')
                logger.info("Создана таблица levels")
            else:
                # Проверяем наличие колонки last_message_time в таблице levels
                cursor = await conn.execute("PRAGMA table_info(levels)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'last_message_time' not in column_names:
                    try:
                        await conn.execute("ALTER TABLE levels ADD COLUMN last_message_time TIMESTAMP")
                        logger.info("Добавлена колонка last_message_time в таблицу levels")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении колонки last_message_time: {e}")
            
            if 'settings' not in tables:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        guild_id INTEGER PRIMARY KEY,
                        welcome_channel_id INTEGER,
                        logs_channel_id INTEGER,
                        tickets_category_id INTEGER,
                        voice_category_id INTEGER,
                        auto_roles TEXT,
                        prefix TEXT DEFAULT '!'
                    )
                ''')
                logger.info("Создана таблица settings")
            else:
                # Проверяем наличие новых колонок
                cursor = await conn.execute("PRAGMA table_info(settings)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'auto_roles' not in column_names:
                    try:
                        await conn.execute("ALTER TABLE settings ADD COLUMN auto_roles TEXT")
                        logger.info("Добавлена колонка auto_roles в таблицу settings")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении колонки auto_roles: {e}")
                
                if 'prefix' not in column_names:
                    try:
                        await conn.execute("ALTER TABLE settings ADD COLUMN prefix TEXT DEFAULT '!'")
                        logger.info("Добавлена колонка prefix в таблицу settings")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении колонки prefix: {e}")
            
            if 'role_rewards' not in tables:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS role_rewards (
                        guild_id INTEGER,
                        role_id INTEGER,
                        level INTEGER,
                        PRIMARY KEY (guild_id, role_id)
                    )
                ''')
                logger.info("Создана таблица role_rewards")
            
            if 'warnings' not in tables:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS warnings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        guild_id INTEGER, 
                        reason TEXT,
                        issued_by INTEGER,
                        issued_at TIMESTAMP,
                        expires_at TIMESTAMP NULL
                    )
                ''')
                logger.info("Создана таблица warnings")
            
            if 'tickets' not in tables:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        channel_id INTEGER,
                        user_id INTEGER,
                        created_at TIMESTAMP,
                        closed_at TIMESTAMP NULL,
                        topic TEXT
                    )
                ''')
                logger.info("Создана таблица tickets")
            
            # Фиксируем изменения
            await conn.commit()
    
    async def _init_redis(self):
        """Инициализация Redis."""
        if self.redis_url:
            try:
                self.redis = redis.from_url(self.redis_url)
                self.redis.ping()
                logger.info("Подключение к Redis успешно установлено")
            except redis.ConnectionError:
                logger.warning("Redis недоступен. Используется локальное кэширование.")
                self.redis = None
            except Exception as e:
                logger.error(f"Ошибка при подключении к Redis: {e}")
                self.redis = None
        else:
            logger.info("URL Redis не настроен. Используется локальное кэширование.")
            self.redis = None
    
    @asynccontextmanager
    async def get_connection(self):
        """Получение соединения из пула."""
        if not self.pool or len(self.pool) == 0:
            # Если пул не инициализирован или пуст, создаем одно соединение
            conn = await aiosqlite.connect(self.db_path)
            try:
                yield conn
            finally:
                await conn.close()
            return
            
        # Получаем соединение из пула
        conn = self.pool.pop()
        try:
            yield conn
        finally:
            # Возвращаем соединение в пул
            if self.pool is not None and len(self.pool) < self.pool_size:
                self.pool.append(conn)
            else:
                await conn.close()
    
    async def execute(self, query: str, params: tuple = ()):
        """Выполнение SQL запроса."""
        async with self.get_connection() as conn:
            try:
                await conn.execute(query, params)
                await conn.commit()
            except Exception as e:
                logger.error(f"Ошибка выполнения SQL запроса: {e}")
                logger.error(f"Запрос: {query}, Параметры: {params}")
                raise
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Получение одной записи."""
        async with self.get_connection() as conn:
            try:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(query, params)
                row = await cursor.fetchone()
                return dict(row) if row else None
            except Exception as e:
                logger.error(f"Ошибка при выполнении fetch_one: {e}")
                logger.error(f"Запрос: {query}, Параметры: {params}")
                return None
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Получение всех записей."""
        async with self.get_connection() as conn:
            try:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Ошибка при выполнении fetch_all: {e}")
                logger.error(f"Запрос: {query}, Параметры: {params}")
                return []
    
    async def close(self):
        """Закрытие всех соединений."""
        if self.pool:
            for conn in self.pool:
                try:
                    await conn.close()
                except Exception as e:
                    logger.error(f"Ошибка при закрытии соединения: {e}")
            self.pool = []

@contextmanager
def get_db():
    """Контекстный менеджер для работы с SQLite."""
    conn = None
    try:
        db_path = os.getenv("DB_PATH", os.path.join("data", "bot.db"))
        conn = sqlite3.connect(db_path)
        yield conn
    except Exception as e:
        logger.error(f"Ошибка при работе с базой данных: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_redis():
    """Получение подключения к Redis."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
            return redis_client
        except redis.ConnectionError:
            logger.warning("Ошибка подключения к Redis")
            return None
        except Exception as e:
            logger.error(f"Ошибка работы с Redis: {e}")
            return None
    return None

def init_db():
    """Инициализация базы данных."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Создание таблиц
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS levels (
                    user_id INTEGER,
                    guild_id INTEGER,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    last_message_time TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    guild_id INTEGER PRIMARY KEY,
                    welcome_channel_id INTEGER,
                    logs_channel_id INTEGER,
                    tickets_category_id INTEGER,
                    voice_category_id INTEGER,
                    auto_roles TEXT,
                    prefix TEXT DEFAULT '!'
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS role_rewards (
                    guild_id INTEGER,
                    role_id INTEGER,
                    level INTEGER,
                    PRIMARY KEY (guild_id, role_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER, 
                    reason TEXT,
                    issued_by INTEGER,
                    issued_at TIMESTAMP,
                    expires_at TIMESTAMP NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    user_id INTEGER,
                    created_at TIMESTAMP,
                    closed_at TIMESTAMP NULL,
                    topic TEXT
                )
            ''')
            
            conn.commit()
            logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise 
