import json
from pathlib import Path
import random
import asyncio
from datetime import datetime, timedelta
import discord

class LevelingSystem:
    def __init__(self, bot):
        self.bot = bot
        self.data_file = Path("levels.json")
        self.data = self.load_data()
        self.xp_cooldowns = {}
        
    def load_data(self):
        if self.data_file.exists():
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
        
    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)
            
    def get_xp_for_level(self, level):
        return 5 * (level ** 2) + 50 * level + 100
        
    def get_level_for_xp(self, xp):
        level = 0
        while xp >= self.get_xp_for_level(level):
            xp -= self.get_xp_for_level(level)
            level += 1
        return level
        
    async def add_experience(self, member: discord.Member):
        user_id = str(member.id)
        guild_id = str(member.guild.id)
        
        # Проверка кулдауна
        cooldown_key = f"{user_id}_{guild_id}"
        current_time = datetime.now()
        if cooldown_key in self.xp_cooldowns:
            if current_time < self.xp_cooldowns[cooldown_key]:
                return False, None
                
        # Установка нового кулдауна (60 секунд)
        self.xp_cooldowns[cooldown_key] = current_time + timedelta(seconds=60)
        
        # Инициализация данных
        if guild_id not in self.data:
            self.data[guild_id] = {}
            
        if user_id not in self.data[guild_id]:
            self.data[guild_id][user_id] = {"xp": 0, "level": 0}
            
        # Добавление опыта
        xp_gain = random.randint(15, 25)
        self.data[guild_id][user_id]["xp"] += xp_gain
        
        # Проверка повышения уровня
        current_xp = self.data[guild_id][user_id]["xp"]
        new_level = self.get_level_for_xp(current_xp)
        
        if new_level > self.data[guild_id][user_id]["level"]:
            self.data[guild_id][user_id]["level"] = new_level
            self.save_data()
            
            # Отправка уведомления о повышении уровня
            embed = discord.Embed(
                title="🎉 Повышение уровня!",
                description=f"Поздравляем, {member.mention}! Вы достигли {new_level} уровня!",
                color=discord.Color.gold()
            )
            try:
                await member.channel.send(embed=embed)
            except:
                pass
                
            # Проверка и выдача ролей за уровень
            await self.bot.role_rewards.check_level_up(member, new_level)
            
            return True, new_level
            
        self.save_data()
        return False, None
        
    async def get_level_xp(self, user_id, guild_id):
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        if guild_id not in self.data or user_id not in self.data[guild_id]:
            return 0, 0
            
        return (
            self.data[guild_id][user_id]["level"],
            self.data[guild_id][user_id]["xp"]
        )
        
    async def get_leaderboard(self, guild_id, limit=10):
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

# Создание глобального экземпляра
leveling = None

def init_leveling(bot):
    global leveling
    leveling = LevelingSystem(bot)
    return leveling

# Экспорт функций для совместимости
async def add_experience(user_id, guild_id):
    if leveling:
        member = leveling.bot.get_guild(int(guild_id)).get_member(int(user_id))
        if member:
            return await leveling.add_experience(member)
    return False, None
    
async def get_level_xp(user_id, guild_id):
    if leveling:
        return await leveling.get_level_xp(user_id, guild_id)
    return 0, 0
    
async def get_leaderboard(guild_id, limit=10):
    if leveling:
        return await leveling.get_leaderboard(guild_id, limit)
    return [] 