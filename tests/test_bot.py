import pytest
from discord.ext import commands
import discord
import asyncio
from bot import Bot
from database.models import User, Warning, GuildConfig
from database.db import get_db
import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
async def bot():
    bot = Bot()
    await bot._async_setup_hook()
    return bot

@pytest.fixture
def db():
    with get_db() as session:
        yield session

@pytest.mark.asyncio
async def test_bot_initialization(bot):
    assert isinstance(bot, commands.Bot)
    assert bot.command_prefix == "!"
    assert bot.intents.message_content is True
    assert bot.intents.members is True

@pytest.mark.asyncio
async def test_warning_system(bot, db):
    # Создаем тестового пользователя
    user = User(id=123456789, guild_id=987654321)
    db.add(user)
    db.commit()
    
    # Добавляем предупреждение
    warning = Warning(
        user_id=user.id,
        guild_id=user.guild_id,
        moderator_id=111111111,
        reason="Test warning"
    )
    db.add(warning)
    db.commit()
    
    # Проверяем, что предупреждение добавлено
    warnings = db.query(Warning).filter_by(user_id=user.id).all()
    assert len(warnings) == 1
    assert warnings[0].reason == "Test warning"

@pytest.mark.asyncio
async def test_guild_config(bot, db):
    # Создаем конфигурацию сервера
    config = GuildConfig(
        guild_id=987654321,
        welcome_channel_id=111111111,
        log_channel_id=222222222
    )
    db.add(config)
    db.commit()
    
    # Проверяем, что конфигурация создана
    saved_config = db.query(GuildConfig).filter_by(guild_id=987654321).first()
    assert saved_config is not None
    assert saved_config.welcome_channel_id == 111111111
    assert saved_config.log_channel_id == 222222222

@pytest.mark.asyncio
async def test_automod(bot):
    # Создаем тестовое сообщение
    class MockMessage:
        content = "test message"
        author = type('obj', (object,), {'bot': False, 'id': 123456789})
        guild = type('obj', (object,), {'id': 987654321, 'owner_id': 111111111})
    
    message = MockMessage()
    
    # Проверяем автомодерацию
    result = await bot.automod.check_message(message)
    assert result is True  # Сообщение должно пройти проверку

@pytest.mark.asyncio
async def test_leveling_system(bot, db):
    # Создаем тестового пользователя
    user = User(id=123456789, guild_id=987654321, xp=0, level=1)
    db.add(user)
    db.commit()
    
    # Имитируем получение опыта
    user.xp += 100
    db.commit()
    
    # Проверяем обновление уровня
    updated_user = db.query(User).filter_by(id=123456789).first()
    assert updated_user.xp == 100

if __name__ == "__main__":
    pytest.main([__file__]) 