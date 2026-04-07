"""Модуль системы уровней для Discord бота."""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
import discord
import os

from infrastructure.config import LevelsStore

from application.contracts import LevelingServiceContract, LevelsRepositoryContract

logger = logging.getLogger(__name__)


class LevelingSystem(LevelingServiceContract):
    """Класс для управления системой уровней."""

    def __init__(
        self,
        bot,
        repository: LevelsRepositoryContract,
        store: LevelsStore,
    ):
        """Инициализация системы уровней.

        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
        self.repository = repository
        self.store = store
        self.data = self.load_data()
        self.xp_cooldowns: Dict[str, datetime] = {}
        self.use_db = True
        self._last_cooldown_cleanup = datetime.now()
        self._schema_checked = False

    def load_data(self) -> Dict:
        """Загрузка данных об уровнях из файла.

        Returns:
            Dict: Загруженные данные или пустой словарь
        """
        return self.store.load()

    def save_data(self) -> None:
        """Сохранение данных об уровнях в файл.

        Необходимо для обратной совместимости со старой системой.
        """
        # Сохраняем только если используем файловую систему
        if not self.use_db:
            self.store.save(self.data)

    def _cleanup_old_cooldowns(self) -> None:
        """Периодическая очистка устаревших кулдаунов для предотвращения утечки памяти."""
        now = datetime.now()
        # Очищаем каждые 5 минут
        if (now - self._last_cooldown_cleanup).total_seconds() < 300:
            return

        # Удаляем кулдауны старше 2 минут (кулдаун 60 сек + запас)
        cutoff = now - timedelta(seconds=120)
        expired_keys = [key for key, expiry in self.xp_cooldowns.items() if expiry < cutoff]
        for key in expired_keys:
            del self.xp_cooldowns[key]

        self._last_cooldown_cleanup = now
        if expired_keys:
            logger.debug(f"Очищено {len(expired_keys)} устаревших кулдаунов")

    def get_xp_for_level(self, level: int) -> int:
        """Расчет необходимого опыта для уровня.

        Args:
            level: Целевой уровень

        Returns:
            int: Необходимый опыт
        """
        return 5 * (level**2) + 50 * level + 100

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

        # Периодическая очистка устаревших кулдаунов
        self._cleanup_old_cooldowns()

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

    async def _ensure_schema_once(self) -> None:
        """Проверка схемы БД один раз при первом использовании."""
        if not self._schema_checked:
            await self.repository.ensure_last_message_time_column()
            self._schema_checked = True

    async def _add_experience_db(
        self, member: discord.Member, user_id: str, guild_id: str, current_time: datetime
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
        await self._ensure_schema_once()

        # Рассчитываем случайное количество опыта (от 15 до 25)
        xp_gain = random.randint(15, 25)

        # Проверяем, есть ли пользователь в базе
        user_data = await self.repository.get_user_level_xp(int(user_id), int(guild_id))

        if not user_data:
            # Если пользователя нет, добавляем его
            await self.repository.create_user(
                int(user_id),
                int(guild_id),
                xp_gain,
                0,
                current_time.isoformat(),
            )
            return False, None

        # Обновляем опыт пользователя
        current_xp = user_data["xp"] + xp_gain
        current_level = user_data["level"]
        new_level = self.get_level_for_xp(current_xp)

        # Обновляем данные в базе с проверкой наличия колонки last_message_time
        await self.repository.update_user(
            int(user_id),
            int(guild_id),
            current_xp,
            new_level,
            current_time.isoformat(),
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
        self, member: discord.Member, user_id: str, guild_id: str
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
            color=discord.Color.gold(),
        )
        try:
            # Проверяем, откуда пришло сообщение
            channel = getattr(member, "channel", None)
            if channel:
                await channel.send(embed=embed)
            else:
                # Отправляем в системный канал сервера, если доступен
                if member.guild.system_channel:
                    await member.guild.system_channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.error(f"Ошибка при отправке уведомления о повышении уровня: {e}")

    async def get_level_xp(
        self, user_id: Union[str, int], guild_id: Union[str, int]
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
                user_data = await self.repository.get_user_level_xp(int(user_id), int(guild_id))

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

        return (self.data[guild_id][user_id]["level"], self.data[guild_id][user_id]["xp"])

    async def get_leaderboard(
        self, guild_id: Union[str, int], limit: int = 10
    ) -> List[Dict[str, Union[str, int]]]:
        """Получение таблицы лидеров сервера.

        Args:
            guild_id: ID сервера
            limit: Количество пользователей в таблице

        Returns:
            List[Dict[str, Union[str, int]]]: Список лидеров
        """
        guild_id = str(guild_id)
        redis_url = os.getenv("REDIS_URL")
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
                    import json

                    return json.loads(cached.decode("utf-8"))
                except Exception as e:
                    logger.warning(f"Failed to load cached leaderboard: {e}")
        # Use DB if available
        if self.use_db:
            try:
                result = await self.repository.get_leaderboard(int(guild_id), limit)
                if redis_client:
                    try:
                        import json

                        redis_client.setex(cache_key, 60, json.dumps(result))
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
            users.append({"user_id": user_id, "xp": data["xp"], "level": data["level"]})
        return sorted(users, key=lambda x: (x["level"], x["xp"]), reverse=True)[:limit]

    async def migrate_to_db(self):
        """Миграция данных из JSON-файла в базу данных."""
        if not self.use_db:
            return

        # Проверяем, есть ли колонка last_message_time в таблице
        try:
            await self.repository.migrate_from_json(self.data)
        except Exception as e:
            logger.error(f"Ошибка при проверке схемы таблицы levels: {e}")
            self.use_db = False  # Используем файловую систему при ошибке


leveling: Optional[LevelingSystem] = None


def init_leveling(
    bot,
    repository: LevelsRepositoryContract,
    store: LevelsStore,
) -> LevelingSystem:
    """Инициализация системы уровней.

    Args:
        bot: Экземпляр бота

    Returns:
        LevelingSystem: Экземпляр системы уровней
    """
    global leveling
    leveling = LevelingSystem(bot, repository, store)

    return leveling


async def add_experience(
    user_id: Union[str, int], guild_id: Union[str, int]
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


async def get_level_xp(user_id: Union[str, int], guild_id: Union[str, int]) -> Tuple[int, int]:
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
    guild_id: Union[str, int], limit: int = 10
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
