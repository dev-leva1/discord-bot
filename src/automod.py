"""Модуль автомодерации для Discord бота."""

from datetime import datetime

import discord

from infrastructure.config import AutomodConfigStore
from application.contracts import AutomodServiceContract
from utils.discord_helpers import parse_duration


class AutoMod(AutomodServiceContract):
    """Класс для управления автомодерацией на сервере."""

    def __init__(self, bot, store: AutomodConfigStore | None = None):
        """Инициализация автомодерации.

        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
        self.store = store or AutomodConfigStore()
        self.config = self.load_config()
        self.spam_counter = {}
        self.warning_counter = {}
        self._last_cleanup = datetime.now()

    def load_config(self):
        """Загрузка конфигурации из файла.

        Returns:
            dict: Загруженная конфигурация или значения по умолчанию
        """
        return self.store.load()

    def save_config(self):
        """Сохранение конфигурации в файл."""
        self.store.save(self.config)

    def _cleanup_old_entries(self) -> None:
        """Периодическая очистка устаревших счетчиков для предотвращения утечки памяти."""
        now = datetime.now()
        # Очищаем каждые 5 минут
        if (now - self._last_cleanup).total_seconds() < 300:
            return

        # Очистка spam_counter - удаляем записи старше удвоенного интервала спама
        spam_interval = self.config.get("spam_interval", 5)

        for user_key in list(self.spam_counter.keys()):
            # Фильтруем старые временные метки
            self.spam_counter[user_key] = [
                t for t in self.spam_counter[user_key]
                if (now - t).total_seconds() <= spam_interval * 2
            ]
            # Удаляем пустые записи
            if not self.spam_counter[user_key]:
                del self.spam_counter[user_key]

        # Очистка warning_counter - сбрасываем все счетчики старше 1 часа
        # Для полноценной очистки нужно отслеживать время последнего предупреждения
        # Пока просто очищаем весь словарь если прошло больше часа с последней очистки
        if (now - self._last_cleanup).total_seconds() > 3600:
            self.warning_counter.clear()

        self._last_cleanup = now

    async def check_message(self, message: discord.Message) -> bool:
        """Проверка сообщения на нарушения.

        Args:
            message: Проверяемое сообщение

        Returns:
            bool: True если сообщение прошло проверку
        """
        if message.author.bot or not message.guild:
            return True

        # Периодическая очистка устаревших счетчиков
        self._cleanup_old_entries()

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
            t
            for t in self.spam_counter[user_key]
            if (now - t).total_seconds() <= self.config["spam_interval"]
        ]

        if len(self.spam_counter[user_key]) > self.config["spam_threshold"]:
            await message.channel.purge(
                limit=self.config["spam_threshold"], check=lambda m: m.author == message.author
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
            color=discord.Color.yellow(),
        )
        embed.add_field(name="Причина", value=reason)
        embed.add_field(
            name="Всего предупреждений",
            value=f"{self.warning_counter[user_key]}/{self.config['max_warnings']}",
        )

        try:
            await member.send(embed=embed)
        except discord.HTTPException:
            pass

        if self.warning_counter[user_key] >= self.config["max_warnings"]:
            duration = parse_duration(self.config["mute_duration"])
            try:
                await member.timeout(duration, reason="Превышение лимита предупреждений")
                self.warning_counter[user_key] = 0  # Сброс счетчика

                mute_embed = discord.Embed(
                    title="🔇 Мут",
                    description=f"{member.mention} получил мут на {self.config['mute_duration']}!",
                    color=discord.Color.red(),
                )
                mute_embed.add_field(name="Причина", value="Превышение лимита предупреждений")

                try:
                    await member.send(embed=mute_embed)
                except discord.HTTPException:
                    pass

            except discord.Forbidden:
                pass
