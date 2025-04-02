"""Модуль системы уровней для Discord бота."""

import json
from pathlib import Path
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import discord

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
        """Сохранение данных об уровнях в файл."""
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
        
    async def add_experience(self, member: discord.Member) -> Tuple[bool, Optional[int]]:
        """Добавление опыта пользователю.
        
        Args:
            member: Пользователь
            
        Returns:
            Tuple[bool, Optional[int]]: (Было ли повышение уровня, Новый уровень)
        """
        user_id = str(member.id)
        guild_id = str(member.guild.id)
        
        cooldown_key = f"{user_id}_{guild_id}"
        current_time = datetime.now()
        if cooldown_key in self.xp_cooldowns:
            if current_time < self.xp_cooldowns[cooldown_key]:
                return False, None
                
        self.xp_cooldowns[cooldown_key] = current_time + timedelta(seconds=60)
        
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
            
            embed = discord.Embed(
                title="🎉 Повышение уровня!",
                description=f"Поздравляем, {member.mention}! Вы достигли {new_level} уровня!",
                color=discord.Color.gold()
            )
            try:
                await member.channel.send(embed=embed)
            except discord.HTTPException:
                pass
                
            await self.bot.role_rewards.check_level_up(member, new_level)
            
            return True, new_level
            
        self.save_data()
        return False, None
        
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