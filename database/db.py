"""Модуль для работы с базой данных."""

import os
import sqlite3
import asyncio
from contextlib import contextmanager, asynccontextmanager
import redis
import aiosqlite
import logging
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с базой данных."""
    
    def __init__(self):
        """Инициализация подключения к базе данных."""
        self.db_path = 'bot.db'
        self.redis_url = os.getenv('REDIS_URL')
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
            # Создаем пул соединений
            self.pool = []
            for _ in range(self.pool_size):
                conn = await aiosqlite.connect(self.db_path)
                self.pool.append(conn)
            
            # Используем одно соединение для инициализации структуры базы
            async with self.get_connection() as conn:
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
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS role_rewards (
                        guild_id INTEGER,
                        role_id INTEGER,
                        level INTEGER,
                        PRIMARY KEY (guild_id, role_id)
                    )
                ''')
                
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
                
                await conn.commit()
                logger.info("База данных SQLite успешно инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка при инициализации SQLite: {str(e)}")
            raise
            
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
        else:
            logger.info("URL Redis не настроен. Используется локальное кэширование.")
            self.redis = None
    
    @asynccontextmanager
    async def get_connection(self):
        """Получение соединения из пула."""
        if not self.pool:
            # Если пул не инициализирован, создаем одно соединение
            conn = await aiosqlite.connect(self.db_path)
            try:
                yield conn
            finally:
                await conn.close()
            return
            
        # Получаем соединение из пула
        if not self.pool:
            raise RuntimeError("Пул соединений не инициализирован")
            
        conn = self.pool.pop() if self.pool else await aiosqlite.connect(self.db_path)
        try:
            yield conn
        finally:
            # Возвращаем соединение в пул
            if len(self.pool) < self.pool_size:
                self.pool.append(conn)
            else:
                await conn.close()
    
    async def execute(self, query: str, params: tuple = ()):
        """Выполнение SQL запроса."""
        async with self.get_connection() as conn:
            await conn.execute(query, params)
            await conn.commit()
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Получение одной записи."""
        async with self.get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Получение всех записей."""
        async with self.get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def close(self):
        """Закрытие всех соединений."""
        if self.pool:
            for conn in self.pool:
                await conn.close()
            self.pool = []

@contextmanager
def get_db():
    """Контекстный менеджер для работы с SQLite."""
    conn = sqlite3.connect('bot.db')
    try:
        yield conn
    finally:
        conn.close()

def get_redis():
    """Получение подключения к Redis."""
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        try:
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
            return redis_client
        except redis.ConnectionError:
            return None
    return None

def init_db():
    """Инициализация базы данных."""
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