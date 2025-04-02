"""Модуль для работы с базой данных и кэшем."""

import os
from contextlib import contextmanager
from typing import Optional, Any

import redis
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .models import Base

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = 'sqlite:///bot.db'

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db_session = scoped_session(SessionLocal)

try:
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    redis_client: Optional[redis.Redis] = redis.from_url(REDIS_URL)
    redis_client.ping()
except redis.ConnectionError:
    print("Redis недоступен. Используется локальное кэширование.")
    redis_client = None

@contextmanager
def get_db():
    """Контекстный менеджер для работы с базой данных.
    
    Yields:
        Session: Сессия базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Инициализация базы данных."""
    Base.metadata.create_all(bind=engine)

def get_redis() -> Optional[redis.Redis]:
    """Получение клиента Redis.
    
    Returns:
        Optional[redis.Redis]: Клиент Redis или None если недоступен
    """
    return redis_client

_local_cache: dict[str, Any] = {}

def cache_set(key: str, value: str, expire: int = 3600) -> None:
    """Установка значения в кэш.
    
    Args:
        key: Ключ
        value: Значение
        expire: Время жизни в секундах
    """
    if redis_client:
        redis_client.set(key, value, ex=expire)
    else:
        _local_cache[key] = value

def cache_get(key: str) -> Optional[str]:
    """Получение значения из кэша.
    
    Args:
        key: Ключ
        
    Returns:
        Optional[str]: Значение из кэша или None если не найдено
    """
    if redis_client:
        return redis_client.get(key)
    return _local_cache.get(key)

def cache_delete(key: str) -> None:
    """Удаление значения из кэша.
    
    Args:
        key: Ключ
    """
    if redis_client:
        redis_client.delete(key)
    elif key in _local_cache:
        del _local_cache[key]

def cache_clear_pattern(pattern: str) -> None:
    """Удаление значений из кэша по паттерну.
    
    Args:
        pattern: Паттерн для поиска ключей
    """
    if redis_client:
        for key in redis_client.scan_iter(pattern):
            redis_client.delete(key)
    else:
        keys_to_delete = [
            k for k in _local_cache.keys()
            if pattern.replace('*', '') in k
        ]
        for key in keys_to_delete:
            del _local_cache[key] 