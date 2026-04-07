"""Вспомогательные функции для работы с Discord."""

from datetime import timedelta
from typing import Union

import discord
from discord.ext import commands


def parse_duration(duration: str) -> timedelta:
    """Парсинг строки длительности в timedelta.

    Args:
        duration: Строка формата "1h", "30m", "7d"

    Returns:
        timedelta: Объект длительности

    Raises:
        ValueError: Если формат строки неверный
    """
    if not duration or len(duration) < 2:
        raise ValueError("Неверный формат длительности")

    try:
        value = int(duration[:-1])
    except ValueError:
        raise ValueError("Неверное числовое значение в длительности")

    unit = duration[-1].lower()

    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    else:
        raise ValueError(f"Неизвестная единица времени: {unit}. Используйте m/h/d")


def check_role_hierarchy(
    moderator: discord.Member, target: discord.Member
) -> tuple[bool, str | None]:
    """Проверка иерархии ролей для модерации.

    Args:
        moderator: Модератор выполняющий действие
        target: Цель действия

    Returns:
        tuple[bool, str | None]: (Можно ли выполнить действие, Сообщение об ошибке)
    """
    if target.top_role >= moderator.top_role:
        return False, "Вы не можете выполнить это действие на пользователе с равной или более высокой ролью!"

    if target.guild.owner_id == target.id:
        return False, "Вы не можете выполнить это действие на владельце сервера!"

    return True, None


async def send_response(
    ctx: Union[discord.Interaction, commands.Context],
    content: str,
    **kwargs,
) -> None:
    """Универсальная отправка ответа для Interaction или Context.

    Args:
        ctx: Контекст команды (Interaction или Context)
        content: Текст сообщения
        **kwargs: Дополнительные параметры для send_message
    """
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            await ctx.followup.send(content, **kwargs)
        else:
            await ctx.response.send_message(content, **kwargs)
    else:
        await ctx.send(content, **kwargs)
