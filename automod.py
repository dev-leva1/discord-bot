"""Модуль автомодерации для Discord бота."""

import json
from datetime import datetime, timedelta
from pathlib import Path
import re

import discord
from discord import app_commands

class AutoMod:
    """Класс для управления автомодерацией на сервере."""
    
    def __init__(self, bot):
        """Инициализация автомодерации.
        
        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
        self.config_file = Path("automod_config.json")
        self.config = self.load_config()
        self.spam_counter = {}
        self.warning_counter = {}
        
    def load_config(self):
        """Загрузка конфигурации из файла.
        
        Returns:
            dict: Загруженная конфигурация или значения по умолчанию
        """
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "banned_words": [],
            "spam_threshold": 5,
            "spam_interval": 5,
            "max_mentions": 3,
            "max_warnings": 3,
            "mute_duration": "1h"
        }
        
    def save_config(self):
        """Сохранение конфигурации в файл."""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
            
    async def setup(self):
        """Настройка команд автомодерации."""
        @self.bot.tree.command(
            name="automod",
            description="Настройка автомодерации"
        )
        @app_commands.checks.has_permissions(manage_guild=True)
        async def automod(
            interaction: discord.Interaction,
            action: str,
            value: str = None
        ):
            """Управление настройками автомодерации.
            
            Args:
                interaction: Объект взаимодействия
                action: Действие для выполнения
                value: Значение для действия
            """
            action = action.lower()
            
            if action == "addword" and value:
                if value not in self.config["banned_words"]:
                    self.config["banned_words"].append(value)
                    self.save_config()
                    await interaction.response.send_message(
                        f"Слово '{value}' добавлено в список запрещенных",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Это слово уже в списке",
                        ephemeral=True
                    )
                    
            elif action == "removeword" and value:
                if value in self.config["banned_words"]:
                    self.config["banned_words"].remove(value)
                    self.save_config()
                    await interaction.response.send_message(
                        f"Слово '{value}' удалено из списка запрещенных",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Этого слова нет в списке",
                        ephemeral=True
                    )
                    
            elif action == "listwords":
                if self.config["banned_words"]:
                    words = "\n".join(self.config["banned_words"])
                    await interaction.response.send_message(
                        f"Запрещенные слова:\n```\n{words}\n```",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Список запрещенных слов пуст",
                        ephemeral=True
                    )
                    
            elif action == "setspam" and value:
                try:
                    threshold = int(value)
                    if 1 <= threshold <= 20:
                        self.config["spam_threshold"] = threshold
                        self.save_config()
                        await interaction.response.send_message(
                            f"Порог спама установлен на {threshold} сообщений",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            "Значение должно быть от 1 до 20",
                            ephemeral=True
                        )
                except ValueError:
                    await interaction.response.send_message(
                        "Требуется числовое значение",
                        ephemeral=True
                    )
                    
            elif action == "setinterval" and value:
                try:
                    interval = int(value)
                    if 1 <= interval <= 60:
                        self.config["spam_interval"] = interval
                        self.save_config()
                        await interaction.response.send_message(
                            f"Интервал спама установлен на {interval} секунд",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            "Значение должно быть от 1 до 60",
                            ephemeral=True
                        )
                except ValueError:
                    await interaction.response.send_message(
                        "Требуется числовое значение",
                        ephemeral=True
                    )
                    
            elif action == "setmentions" and value:
                try:
                    mentions = int(value)
                    if 1 <= mentions <= 10:
                        self.config["max_mentions"] = mentions
                        self.save_config()
                        await interaction.response.send_message(
                            f"Лимит упоминаний установлен на {mentions}",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            "Значение должно быть от 1 до 10",
                            ephemeral=True
                        )
                except ValueError:
                    await interaction.response.send_message(
                        "Требуется числовое значение",
                        ephemeral=True
                    )
                    
            elif action == "setwarnings" and value:
                try:
                    warnings = int(value)
                    if 1 <= warnings <= 10:
                        self.config["max_warnings"] = warnings
                        self.save_config()
                        await interaction.response.send_message(
                            f"Максимум предупреждений установлен на {warnings}",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            "Значение должно быть от 1 до 10",
                            ephemeral=True
                        )
                except ValueError:
                    await interaction.response.send_message(
                        "Требуется числовое значение",
                        ephemeral=True
                    )
                    
            elif action == "setmute" and value:
                if re.match(r'^\d+[mhd]$', value):
                    self.config["mute_duration"] = value
                    self.save_config()
                    await interaction.response.send_message(
                        f"Длительность мута установлена на {value}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Неверный формат. Используйте число + m/h/d (например: 30m, 1h, 7d)",
                        ephemeral=True
                    )
                    
            else:
                await interaction.response.send_message(
                    "Неверная команда или отсутствует значение",
                    ephemeral=True
                )
                
    def parse_duration(self, duration: str) -> timedelta:
        """Парсинг длительности мута.
        
        Args:
            duration: Строка с длительностью (например, "1h", "30m", "7d")
            
        Returns:
            timedelta: Объект с длительностью
        """
        value = int(duration[:-1])
        unit = duration[-1].lower()
        
        if unit == 'm':
            return timedelta(minutes=value)
        if unit == 'h':
            return timedelta(hours=value)
        if unit == 'd':
            return timedelta(days=value)
        return timedelta(hours=1)  # По умолчанию
            
    async def check_message(self, message: discord.Message) -> bool:
        """Проверка сообщения на нарушения.
        
        Args:
            message: Проверяемое сообщение
            
        Returns:
            bool: True если сообщение прошло проверку
        """
        if message.author.bot or not message.guild:
            return True
            
        # Проверка запрещенных слов
        content = message.content.lower()
        for word in self.config["banned_words"]:
            if word.lower() in content:
                await message.delete()
                await self.add_warning(message.author, "Использование запрещенных слов")
                return False
                
        # Проверка спама
        now = datetime.now()
        user_key = f"{message.author.id}_{message.guild.id}"
        
        if user_key not in self.spam_counter:
            self.spam_counter[user_key] = []
            
        self.spam_counter[user_key].append(now)
        
        # Удаление старых сообщений из счетчика
        self.spam_counter[user_key] = [
            t for t in self.spam_counter[user_key]
            if (now - t).total_seconds() <= self.config["spam_interval"]
        ]
        
        if len(self.spam_counter[user_key]) > self.config["spam_threshold"]:
            await message.channel.purge(
                limit=self.config["spam_threshold"],
                check=lambda m: m.author == message.author
            )
            await self.add_warning(message.author, "Спам")
            return False
            
        # Проверка массовых упоминаний
        if len(message.mentions) > self.config["max_mentions"]:
            await message.delete()
            await self.add_warning(message.author, "Массовые упоминания")
            return False
            
        return True
        
    async def add_warning(self, member: discord.Member, reason: str):
        """Добавление предупреждения пользователю.
        
        Args:
            member: Пользователь
            reason: Причина предупреждения
        """
        user_key = f"{member.id}_{member.guild.id}"
        
        if user_key not in self.warning_counter:
            self.warning_counter[user_key] = 0
            
        self.warning_counter[user_key] += 1
        
        embed = discord.Embed(
            title="⚠️ Предупреждение",
            description=f"{member.mention} получил предупреждение!",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Причина", value=reason)
        embed.add_field(
            name="Всего предупреждений",
            value=f"{self.warning_counter[user_key]}/{self.config['max_warnings']}"
        )
        
        try:
            await member.send(embed=embed)
        except discord.HTTPException:
            pass
            
        if self.warning_counter[user_key] >= self.config["max_warnings"]:
            duration = self.parse_duration(self.config["mute_duration"])
            try:
                await member.timeout(duration, reason="Превышение лимита предупреждений")
                self.warning_counter[user_key] = 0  # Сброс счетчика
                
                mute_embed = discord.Embed(
                    title="🔇 Мут",
                    description=f"{member.mention} получил мут на {self.config['mute_duration']}!",
                    color=discord.Color.red()
                )
                mute_embed.add_field(name="Причина", value="Превышение лимита предупреждений")
                
                try:
                    await member.send(embed=mute_embed)
                except discord.HTTPException:
                    pass
                    
            except discord.Forbidden:
                pass 