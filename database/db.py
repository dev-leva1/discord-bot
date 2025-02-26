from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from contextlib import contextmanager
import redis
from .models import Base
import os
from dotenv import load_dotenv

load_dotenv()

# Используем SQLite вместо PostgreSQL для упрощения разработки
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = 'sqlite:///bot.db'

# Создаем движок базы данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db_session = scoped_session(SessionLocal)

# Инициализируем Redis только если он доступен
try:
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
except:
    print("Redis недоступен. Используется локальное кэширование.")
    redis_client = None

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

def get_redis():
    return redis_client

# Функции кэширования с поддержкой локального кэширования
_local_cache = {}

def cache_set(key: str, value: str, expire: int = 3600):
    if redis_client:
        redis_client.set(key, value, ex=expire)
    else:
        _local_cache[key] = value

def cache_get(key: str) -> str:
    if redis_client:
        return redis_client.get(key)
    return _local_cache.get(key)

def cache_delete(key: str):
    if redis_client:
        redis_client.delete(key)
    elif key in _local_cache:
        del _local_cache[key]

def cache_clear_pattern(pattern: str):
    if redis_client:
        for key in redis_client.scan_iter(pattern):
            redis_client.delete(key)
    else:
        # Простая реализация для локального кэша
        keys_to_delete = [k for k in _local_cache.keys() if pattern.replace('*', '') in k]
        for key in keys_to_delete:
            del _local_cache[key] 