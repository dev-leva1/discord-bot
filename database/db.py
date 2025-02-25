from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from contextlib import contextmanager
import redis
from .models import Base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Создаем движок базы данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db_session = scoped_session(SessionLocal)

# Создаем подключение к Redis
redis_client = redis.from_url(REDIS_URL)

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

# Функции кэширования
def cache_set(key: str, value: str, expire: int = 3600):
    redis_client.set(key, value, ex=expire)

def cache_get(key: str) -> str:
    return redis_client.get(key)

def cache_delete(key: str):
    redis_client.delete(key)

def cache_clear_pattern(pattern: str):
    for key in redis_client.scan_iter(pattern):
        redis_client.delete(key) 