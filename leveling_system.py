"""Модуль системы уровней для Discord бота."""

import json
from pathlib import Path
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
import discord
import os
import pickle

logger = logging.getLogger(__name__)

class LevelingSystem:
    """Класс для управления системой уровней."""
    
    def __init__(self, bot):
        """Инициализация системы уровней.
        
        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
        self.data_file = Path("levels.json")
        self.data = self.load_data()
        self.xp_cooldowns: Dict[str, datetime] = {}
        self.use_db = True
        
    def load_data(self) -> Dict:
        """Загрузка данных об уровнях из файла.
        
        Returns:
            Dict: Загруженные данные или пустой словарь
        """
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
        
    def save_data(self) -> None:
        """Сохранение данных об уровнях в файл.
        
        Необходимо для обратной совместимости со старой системой.
        """
        # Сохраняем только если используем файловую систему
        if not self.use_db:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
            
    def get_xp_for_level(self, level: int) -> int:
        """Расчет необходимого опыта для уровня.
        
        Args:
            level: Целевой уровень
            
        Returns:
            int: Необходимый опыт
        """
        return 5 * (level ** 2) + 50 * level + 100
        
    def get_level_for_xp(self, xp: int) -> int:
        """Расчет уровня на основе опыта.
        
        Args:
            xp: Количество опыта
            
        Returns:
            int: Текущий уровень
        """
        level = 0
        while xp >= self.get_xp_for_level(level):
            xp -= self.get_xp_for_level(level)
            level += 1
        return level
    
    async def process_message(self, message: discord.Message) -> Tuple[bool, Optional[int]]:
        """Обработка сообщения для начисления опыта.
        
        Args:
            message: Сообщение пользователя
            
        Returns:
            Tuple[bool, Optional[int]]: (Было ли повышение уровня, Новый уровень)
        """
        # Проверяем, что сообщение из гильдии и не от бота
        if not message.guild or message.author.bot:
            return False, None
            
        return await self.add_experience(message.author)
        
    async def add_experience(self, member: discord.Member) -> Tuple[bool, Optional[int]]:
        """Добавление опыта пользователю.
        
        Args:
            member: Пользователь
            
        Returns:
            Tuple[bool, Optional[int]]: (Было ли повышение уровня, Новый уровень)
        """
        user_id = str(member.id)
        guild_id = str(member.guild.id)
        
        # Проверка кулдауна
        cooldown_key = f"{user_id}_{guild_id}"
        current_time = datetime.now()
        if cooldown_key in self.xp_cooldowns:
            if current_time < self.xp_cooldowns[cooldown_key]:
                return False, None
                
        # Устанавливаем кулдаун 60 секунд
        self.xp_cooldowns[cooldown_key] = current_time + timedelta(seconds=60)
        
        # Используем БД если доступна
        if self.use_db:
            try:
                return await self._add_experience_db(member, user_id, guild_id, current_time)
            except Exception as e:
                logger.error(f"Ошибка при добавлении опыта в БД: {e}")
                # Если произошла ошибка, то используем файловую систему
                self.use_db = False
        
        # Используем файловую систему как запасной вариант
        return await self._add_experience_file(member, user_id, guild_id)
    
    async def _add_experience_db(
        self, 
        member: discord.Member, 
        user_id: str, 
        guild_id: str,
        current_time: datetime
    ) -> Tuple[bool, Optional[int]]:
        """Добавление опыта пользователю через базу данных.
        
        Args:
            member: Пользователь
            user_id: ID пользователя
            guild_id: ID сервера
            current_time: Текущее время
            
        Returns:
            Tuple[bool, Optional[int]]: (Было ли повышение уровня, Новый уровень)
        """
        # Рассчитываем случайное количество опыта (от 15 до 25)
        xp_gain = random.randint(15, 25)
        
        # Проверяем, есть ли пользователь в базе
        user_data = await self.bot.db.fetch_one(
            "SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?",
            (int(user_id), int(guild_id))
        )
        
        if not user_data:
            # Если пользователя нет, добавляем его
            try:
                # Проверяем, есть ли колонка last_message_time в таблице
                table_info = await self.bot.db.fetch_all(
                    "PRAGMA table_info(levels)"
                )
                columns = [col["name"] for col in table_info]
                
                if "last_message_time" in columns:
                    # Если колонка существует
                    await self.bot.db.execute(
                        "INSERT INTO levels (user_id, guild_id, xp, level, last_message_time) VALUES (?, ?, ?, ?, ?)",
                        (int(user_id), int(guild_id), xp_gain, 0, current_time.isoformat())
                    )
                else:
                    # Если колонки нет, используем старую схему
                    await self.bot.db.execute(
                        "INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                        (int(user_id), int(guild_id), xp_gain, 0)
                    )
            except Exception as e:
                logger.error(f"Ошибка при добавлении пользователя в БД: {e}")
                # Используем простой запрос без last_message_time
                await self.bot.db.execute(
                    "INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                    (int(user_id), int(guild_id), xp_gain, 0)
                )
            return False, None
        
        # Обновляем опыт пользователя
        current_xp = user_data["xp"] + xp_gain
        current_level = user_data["level"]
        new_level = self.get_level_for_xp(current_xp)
        
        # Обновляем данные в базе с проверкой наличия колонки last_message_time
        try:
            # Проверяем, есть ли колонка last_message_time в таблице
            table_info = await self.bot.db.fetch_all(
                "PRAGMA table_info(levels)"
            )
            columns = [col["name"] for col in table_info]
            
            if "last_message_time" in columns:
                # Если колонка существует
                await self.bot.db.execute(
                    "UPDATE levels SET xp = ?, level = ?, last_message_time = ? WHERE user_id = ? AND guild_id = ?",
                    (current_xp, new_level, current_time.isoformat(), int(user_id), int(guild_id))
                )
            else:
                # Если колонки нет, используем старую схему
                await self.bot.db.execute(
                    "UPDATE levels SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
                    (current_xp, new_level, int(user_id), int(guild_id))
                )
        except Exception as e:
            logger.error(f"Ошибка при обновлении опыта в БД: {e}")
            # Используем простой запрос без last_message_time
            await self.bot.db.execute(
                "UPDATE levels SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
                (current_xp, new_level, int(user_id), int(guild_id))
            )
        
        # Если уровень повысился
        if new_level > current_level:
            # Отправляем уведомление
            await self._send_level_up_notification(member, new_level)
            
            # Проверяем роли
            await self.bot.role_rewards.check_level_up(member, new_level)
            
            return True, new_level
        
        return False, None
    
    async def _add_experience_file(
        self, 
        member: discord.Member, 
        user_id: str, 
        guild_id: str
    ) -> Tuple[bool, Optional[int]]:
        """Добавление опыта пользователю через файловую систему.
        
        Args:
            member: Пользователь
            user_id: ID пользователя
            guild_id: ID сервера
            
        Returns:
            Tuple[bool, Optional[int]]: (Было ли повышение уровня, Новый уровень)
        """
        if guild_id not in self.data:
            self.data[guild_id] = {}
            
        if user_id not in self.data[guild_id]:
            self.data[guild_id][user_id] = {"xp": 0, "level": 0}
            
        xp_gain = random.randint(15, 25)
        self.data[guild_id][user_id]["xp"] += xp_gain
        
        current_xp = self.data[guild_id][user_id]["xp"]
        new_level = self.get_level_for_xp(current_xp)
        
        if new_level > self.data[guild_id][user_id]["level"]:
            self.data[guild_id][user_id]["level"] = new_level
            self.save_data()
            
            await self._send_level_up_notification(member, new_level)
            
            await self.bot.role_rewards.check_level_up(member, new_level)
            
            return True, new_level
            
        self.save_data()
        return False, None
    
    async def _send_level_up_notification(self, member: discord.Member, new_level: int) -> None:
        """Отправка уведомления о повышении уровня.
        
        Args:
            member: Пользователь
            new_level: Новый уровень
        """
        embed = discord.Embed(
            title="🎉 Повышение уровня!",
            description=f"Поздравляем, {member.mention}! Вы достигли {new_level} уровня!",
            color=discord.Color.gold()
        )
        try:
            # Проверяем, откуда пришло сообщение
            channel = getattr(member, 'channel', None)
            if channel:
                await channel.send(embed=embed)
            else:
                # Отправляем в системный канал сервера, если доступен
                if member.guild.system_channel:
                    await member.guild.system_channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.error(f"Ошибка при отправке уведомления о повышении уровня: {e}")
        
    async def get_level_xp(
        self,
        user_id: Union[str, int],
        guild_id: Union[str, int]
    ) -> Tuple[int, int]:
        """Получение уровня и опыта пользователя.
        
        Args:
            user_id: ID пользователя
            guild_id: ID сервера
            
        Returns:
            Tuple[int, int]: (Уровень, Опыт)
        """
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        # Используем БД если доступна
        if self.use_db:
            try:
                user_data = await self.bot.db.fetch_one(
                    "SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?",
                    (int(user_id), int(guild_id))
                )
                
                if user_data:
                    return user_data["level"], user_data["xp"]
                return 0, 0
            except Exception as e:
                logger.error(f"Ошибка при получении уровня из БД: {e}")
                # Если произошла ошибка, используем файловую систему
                self.use_db = False
        
        # Используем файловую систему как запасной вариант
        if guild_id not in self.data or user_id not in self.data[guild_id]:
            return 0, 0
            
        return (
            self.data[guild_id][user_id]["level"],
            self.data[guild_id][user_id]["xp"]
        )
        
    async def get_leaderboard(
        self,
        guild_id: Union[str, int],
        limit: int = 10
    ) -> List[Dict[str, Union[str, int]]]:
        """Получение таблицы лидеров сервера.
        
        Args:
            guild_id: ID сервера
            limit: Количество пользователей в таблице
            
        Returns:
            List[Dict[str, Union[str, int]]]: Список лидеров
        """
        guild_id = str(guild_id)
        redis_url = os.getenv('REDIS_URL')
        redis_client = None
        if redis_url:
            try:
                import redis as redis_lib
                redis_client = redis_lib.from_url(redis_url)
            except Exception as e:
                logger.warning(f"Redis unavailable for leaderboard cache: {e}")
                redis_client = None
        cache_key = f"leaderboard:{guild_id}:{limit}"
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                try:
                    return pickle.loads(cached)
                except Exception as e:
                    logger.warning(f"Failed to load cached leaderboard: {e}")
        # Use DB if available
        if self.use_db:
            try:
                leaderboard_data = await self.bot.db.fetch_all(
                    "SELECT user_id, xp, level FROM levels WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?",
                    (int(guild_id), limit)
                )
                result = [
                    {
                        "user_id": str(row["user_id"]),
                        "xp": row["xp"],
                        "level": row["level"]
                    }
                    for row in leaderboard_data
                ]
                if redis_client:
                    try:
                        redis_client.setex(cache_key, 60, pickle.dumps(result))
                    except Exception as e:
                        logger.warning(f"Failed to cache leaderboard: {e}")
                return result
            except Exception as e:
                logger.error(f"Ошибка при получении таблицы лидеров из БД: {e}")
                # Если произошла ошибка, используем файловую систему
                self.use_db = False
        # Use file system as fallback
        if guild_id not in self.data:
            return []
        users = []
        for user_id, data in self.data[guild_id].items():
            users.append({
                "user_id": user_id,
                "xp": data["xp"],
                "level": data["level"]
            })
        return sorted(users, key=lambda x: (x["level"], x["xp"]), reverse=True)[:limit]

    async def migrate_to_db(self):
        """Миграция данных из JSON-файла в базу данных."""
        if not self.use_db:
            return
            
        # Проверяем, есть ли колонка last_message_time в таблице
        try:
            table_info = await self.bot.db.fetch_all(
                "PRAGMA table_info(levels)"
            )
            columns = [col["name"] for col in table_info]
            
            has_last_message_time = "last_message_time" in columns
            
            # Если колонки нет, добавляем её
            if not has_last_message_time:
                logger.info("Добавление колонки last_message_time в таблицу levels")
                await self.bot.db.execute(
                    "ALTER TABLE levels ADD COLUMN last_message_time TIMESTAMP"
                )
                
            # Теперь мигрируем данные
            for guild_id, guild_data in self.data.items():
                for user_id, user_data in guild_data.items():
                    try:
                        # Проверяем, есть ли пользователь в базе
                        user_db = await self.bot.db.fetch_one(
                            "SELECT user_id FROM levels WHERE user_id = ? AND guild_id = ?",
                            (int(user_id), int(guild_id))
                        )
                        
                        if not user_db:
                            # Если пользователя нет, добавляем его
                            current_time = datetime.now().isoformat()
                            if has_last_message_time:
                                await self.bot.db.execute(
                                    "INSERT INTO levels (user_id, guild_id, xp, level, last_message_time) VALUES (?, ?, ?, ?, ?)",
                                    (int(user_id), int(guild_id), user_data["xp"], user_data["level"], current_time)
                                )
                            else:
                                await self.bot.db.execute(
                                    "INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                                    (int(user_id), int(guild_id), user_data["xp"], user_data["level"])
                                )
                    except Exception as e:
                        logger.error(f"Ошибка при миграции данных в БД: {e}")
        except Exception as e:
            logger.error(f"Ошибка при проверке схемы таблицы levels: {e}")
            self.use_db = False  # Используем файловую систему при ошибке

leveling: Optional[LevelingSystem] = None

def init_leveling(bot) -> LevelingSystem:
    """Инициализация системы уровней.
    
    Args:
        bot: Экземпляр бота
        
    Returns:
        LevelingSystem: Экземпляр системы уровней
    """
    global leveling
    leveling = LevelingSystem(bot)

    return leveling

async def add_experience(
    user_id: Union[str, int],
    guild_id: Union[str, int]
) -> Tuple[bool, Optional[int]]:
    """Добавление опыта пользователю (для совместимости).
    
    Args:
        user_id: ID пользователя
        guild_id: ID сервера
        
    Returns:
        Tuple[bool, Optional[int]]: (Было ли повышение уровня, Новый уровень)
    """
    if leveling:
        member = leveling.bot.get_guild(int(guild_id)).get_member(int(user_id))
        if member:
            return await leveling.add_experience(member)
    return False, None
    
async def get_level_xp(
    user_id: Union[str, int],
    guild_id: Union[str, int]
) -> Tuple[int, int]:
    """Получение уровня и опыта пользователя (для совместимости).
    
    Args:
        user_id: ID пользователя
        guild_id: ID сервера
        
    Returns:
        Tuple[int, int]: (Уровень, Опыт)
    """
    if leveling:
        return await leveling.get_level_xp(user_id, guild_id)
    return 0, 0
    
async def get_leaderboard(
    guild_id: Union[str, int],
    limit: int = 10
) -> List[Dict[str, Union[str, int]]]:
    """Получение таблицы лидеров сервера (для совместимости).
    
    Args:
        guild_id: ID сервера
        limit: Количество пользователей в таблице
        
    Returns:
        List[Dict[str, Union[str, int]]]: Список лидеров
    """
    if leveling:
        return await leveling.get_leaderboard(guild_id, limit)
    return [] 
