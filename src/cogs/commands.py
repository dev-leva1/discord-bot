"""Модуль с основными командами бота."""

from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
import logging

from utils.monitoring import monitor_command

logger = logging.getLogger(__name__)


class Commands(commands.Cog):
    """Класс с основными командами бота."""

    def __init__(self, bot):
        """Инициализация класса команд.

        Args:
            bot: Экземпляр бота
        """
        self.bot = bot

    @commands.hybrid_command(name="rank", description="Показывает ваш текущий уровень и опыт")
    @app_commands.describe(member="Пользователь, статистику которого нужно показать")
    @monitor_command
    async def rank(self, ctx, member: Optional[discord.Member] = None):
        """Показывает текущий уровень и опыт пользователя.

        Args:
            ctx: Контекст команды
            member: Пользователь, чей уровень нужно показать, по умолчанию автор команды
        """
        target = member or ctx.author

        # Чтобы не показывать информацию о ботах
        if target.bot:
            await ctx.send("Боты не могут получать опыт и уровни!", ephemeral=True)
            return

        # Получаем уровень и опыт
        level, xp = await self.bot.leveling.get_level_xp(target.id, ctx.guild.id)
        next_level_xp = self.bot.leveling.get_xp_for_level(level)

        # Создаём карточку ранга
        try:
            rank_card = await self.bot.image_generator.create_rank_card(
                target, level, xp, next_level_xp
            )

            await ctx.send(file=rank_card)
        except Exception as e:
            logger.error(f"Ошибка при создании карточки ранга: {e}")
            # Если не удалось создать изображение, отправляем текстовый ответ
            embed = discord.Embed(
                title=f"Уровень {target.display_name}",
                description=f"**Уровень:** {level}\n**Опыт:** {xp}/{next_level_xp}",
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="leaderboard", description="Показывает таблицу лидеров по уровням"
    )
    @app_commands.describe(limit="Количество пользователей в таблице (макс. 20)")
    @monitor_command
    async def leaderboard(self, ctx, limit: Optional[int] = 10):
        """Показывает таблицу лидеров сервера по уровням.

        Args:
            ctx: Контекст команды
            limit: Количество пользователей в таблице (макс. 20)
        """
        # Ограничиваем количество пользователей
        if limit > 20:
            limit = 20
        elif limit < 1:
            limit = 10

        # Получаем данные о лидерах
        leaders_data = await self.bot.leveling.get_leaderboard(ctx.guild.id, limit)

        if not leaders_data:
            await ctx.send("На сервере пока нет участников с опытом!", ephemeral=True)
            return

        # Форматируем данные для создания изображения
        leaders = []
        for data in leaders_data:
            user = ctx.guild.get_member(int(data["user_id"]))
            if user:
                leaders.append((user, data["level"], data["xp"]))

        # Если нет валидных пользователей, отправляем сообщение
        if not leaders:
            await ctx.send(
                "Не найдено активных пользователей с опытом на этом сервере.", ephemeral=True
            )
            return

        try:
            # Создаём изображение с таблицей лидеров
            leaderboard_card = await self.bot.image_generator.create_leaderboard_card(
                ctx.guild.name, leaders
            )

            await ctx.send(file=leaderboard_card)
        except Exception as e:
            logger.error(f"Ошибка при создании таблицы лидеров: {e}")
            # Если не удалось создать изображение, отправляем текстовую таблицу
            embed = discord.Embed(
                title=f"Таблица лидеров сервера {ctx.guild.name}", color=discord.Color.gold()
            )

            for i, (user, level, xp) in enumerate(leaders, 1):
                embed.add_field(
                    name=f"{i}. {user.display_name}",
                    value=f"Уровень: {level} | Опыт: {xp}",
                    inline=False,
                )

            await ctx.send(embed=embed)

    @commands.hybrid_command(name="bothelp", description="Показывает список доступных команд")
    @monitor_command
    async def commands_list(self, ctx):
        """Показывает список доступных команд бота.

        Args:
            ctx: Контекст команды
        """
        embed = discord.Embed(
            title="📚 Помощь по командам",
            description="Список всех доступных команд:",
            color=discord.Color.blue(),
        )

        # Проверяем права пользователя
        is_owner = ctx.guild.owner_id == ctx.author.id
        show_admin_commands = is_owner or ctx.author.guild_permissions.administrator
        show_mod_commands = show_admin_commands or ctx.author.guild_permissions.ban_members

        # Основные команды
        embed.add_field(
            name="📊 Уровни и опыт",
            value="""
• `/rank` - Показать ваш текущий уровень и опыт
• `/leaderboard` - Таблица лидеров сервера
            """,
            inline=False,
        )

        # Команды для тикетов
        embed.add_field(
            name="🎫 Тикеты",
            value="""
• `/ticket create` - Создать тикет
• `/ticket close` - Закрыть тикет
            """,
            inline=False,
        )

        # Команды для голосовых каналов
        embed.add_field(
            name="🔊 Голосовые каналы",
            value="""
• `/voice name` - Изменить название канала
• `/voice limit` - Установить лимит пользователей
• `/voice lock` - Закрыть канал
• `/voice unlock` - Открыть канал
            """,
            inline=False,
        )

        # Команды модерации
        if show_mod_commands:
            embed.add_field(
                name="🛡️ Модерация",
                value="""
• `/ban` - Забанить пользователя
• `/kick` - Выгнать пользователя
• `/mute` - Временно замутить пользователя
• `/clear` - Очистить сообщения в канале
• `/warn_add` - Выдать предупреждение
• `/warn_remove` - Удалить предупреждение
• `/warn_list` - Список предупреждений
• `/warn_clear` - Очистить все предупреждения
                """,
                inline=False,
            )

        # Команды автомодерации
        if show_admin_commands:
            embed.add_field(
                name="🤖 Автомодерация",
                value="""
• `/automod addword` - Добавить запрещенное слово
• `/automod removeword` - Удалить запрещенное слово
• `/automod listwords` - Список запрещенных слов
• `/automod setspam` - Установить порог спама
• `/automod setinterval` - Установить интервал спама
• `/automod setmentions` - Установить лимит упоминаний
• `/automod setwarnings` - Установить максимум предупреждений
• `/automod setmute` - Установить длительность мута
                """,
                inline=False,
            )

        # Настройки сервера
        if show_admin_commands:
            embed.add_field(
                name="⚙️ Настройки сервера",
                value="""
• `/setwelcome` - Установить канал приветствий
• `/setlogs` - Установить канал для логов
• `/ticket setup` - Настроить систему тикетов
• `/voice setup` - Настроить временные голосовые каналы
                """,
                inline=False,
            )

        # Управление ролями
        if show_admin_commands:
            embed.add_field(
                name="👥 Управление ролями",
                value="""
• `/addrole` - Добавить роль-награду за уровень
• `/removerole` - Удалить роль-награду
• `/listroles` - Список ролей-наград за уровни
                """,
                inline=False,
            )

        # Добавляем футер
        if is_owner:
            embed.set_footer(text="👑 Показаны все команды (вы владелец сервера)")
        elif show_admin_commands:
            embed.set_footer(text="🔰 Показаны команды администратора")
        elif show_mod_commands:
            embed.set_footer(text="🔨 Показаны команды модератора")
        else:
            embed.set_footer(text="ℹ️ Некоторые команды скрыты, так как у вас недостаточно прав")

        # Отправляем сообщение с командами
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping", description="Проверка задержки бота")
    @monitor_command
    async def ping(self, ctx):
        """Проверка задержки бота.

        Args:
            ctx: Контекст команды
        """
        # Получаем задержку в мс
        latency = round(self.bot.latency * 1000)

        # Определяем цвет в зависимости от задержки
        if latency < 100:
            color = discord.Color.green()
            status = "Отличное"
        elif latency < 200:
            color = discord.Color.gold()
            status = "Хорошее"
        else:
            color = discord.Color.red()
            status = "Плохое"

        # Создаем и отправляем сообщение
        embed = discord.Embed(
            title="🏓 Понг!",
            description=f"**Задержка API:** {latency} мс\n**Статус соединения:** {status}",
            color=color,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Показывает информацию о сервере")
    @monitor_command
    async def serverinfo(self, ctx):
        """Показывает информацию о сервере.

        Args:
            ctx: Контекст команды
        """
        guild = ctx.guild

        # Считаем каналы по категориям
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)

        # Считаем роли (без роли @everyone)
        roles_count = len(guild.roles) - 1

        # Считаем эмодзи
        emoji_count = len(guild.emojis)

        # Считаем пользователей и ботов
        member_count = guild.member_count
        bot_count = sum(1 for member in guild.members if member.bot)
        human_count = member_count - bot_count

        # Создаем эмбед
        embed = discord.Embed(
            title=f"Информация о сервере {guild.name}", color=discord.Color.blue()
        )

        # Если есть иконка сервера, добавляем ее
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Добавляем основную информацию
        embed.add_field(name="ID сервера", value=guild.id, inline=True)
        embed.add_field(
            name="Владелец", value=guild.owner.mention if guild.owner else "Неизвестно", inline=True
        )
        embed.add_field(name="Создан", value=guild.created_at.strftime("%d.%m.%Y"), inline=True)

        # Добавляем статистику
        embed.add_field(
            name="Участники",
            value=f"Всего: {member_count}\nЛюди: {human_count}\nБоты: {bot_count}",
            inline=True,
        )
        embed.add_field(
            name="Каналы",
            value=f"Текстовые: {text_channels}\nГолосовые: {voice_channels}\nКатегории: {categories}",
            inline=True,
        )
        embed.add_field(
            name="Прочее", value=f"Ролей: {roles_count}\nЭмодзи: {emoji_count}", inline=True
        )

        # Добавляем уровень буста если есть
        if guild.premium_tier > 0:
            embed.add_field(
                name="Уровень буста",
                value=f"{guild.premium_tier} уровень ({guild.premium_subscription_count} бустов)",
                inline=False,
            )

        # Добавляем футер
        embed.set_footer(text=f"Запрошено: {ctx.author.display_name}")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="userinfo", description="Показывает информацию о пользователе")
    @app_commands.describe(member="Пользователь, информацию о котором нужно показать")
    @monitor_command
    async def userinfo(self, ctx, member: Optional[discord.Member] = None):
        """Показывает информацию о пользователе.

        Args:
            ctx: Контекст команды
            member: Пользователь, информацию о котором нужно показать, по умолчанию автор команды
        """
        target = member or ctx.author

        # Получаем дату присоединения к серверу и Discord
        joined_at = (
            target.joined_at.strftime("%d.%m.%Y %H:%M") if target.joined_at else "Неизвестно"
        )
        created_at = target.created_at.strftime("%d.%m.%Y %H:%M")

        # Определяем статус пользователя
        status_emoji = {
            discord.Status.online: "🟢 В сети",
            discord.Status.idle: "🟡 Не активен",
            discord.Status.dnd: "🔴 Не беспокоить",
            discord.Status.offline: "⚫ Не в сети",
        }
        status = status_emoji.get(target.status, "⚪ Неизвестно")

        # Получаем роли пользователя (кроме @everyone)
        roles = [role.mention for role in target.roles if role.name != "@everyone"]
        roles_str = ", ".join(roles) if roles else "Нет ролей"

        # Создаем эмбед
        embed = discord.Embed(
            title=f"Информация о пользователе {target.display_name}",
            color=target.color if target.color.value else discord.Color.blue(),
        )

        # Добавляем аватар
        embed.set_thumbnail(url=target.display_avatar.url)

        # Добавляем основную информацию
        embed.add_field(name="ID", value=target.id, inline=True)
        embed.add_field(name="Статус", value=status, inline=True)
        embed.add_field(name="Бот", value="Да" if target.bot else "Нет", inline=True)

        # Добавляем информацию о времени
        embed.add_field(name="Присоединился к серверу", value=joined_at, inline=True)
        embed.add_field(name="Аккаунт создан", value=created_at, inline=True)

        # Добавляем информацию об активностях если есть
        if target.activities:
            activities = []
            for activity in target.activities:
                if isinstance(activity, discord.Game):
                    activities.append(f"🎮 Играет в {activity.name}")
                elif isinstance(activity, discord.Streaming):
                    activities.append(f"🔴 Стримит {activity.name}")
                elif isinstance(activity, discord.Spotify):
                    activities.append(f"🎵 Слушает {activity.title} - {activity.artist}")
                elif isinstance(activity, discord.CustomActivity):
                    activities.append(f"📝 {activity.name}")

            if activities:
                embed.add_field(name="Активности", value="\n".join(activities), inline=False)

        # Добавляем информацию о ролях
        if len(roles_str) <= 1024:  # Ограничение Discord на длину значения поля
            embed.add_field(name=f"Роли ({len(roles)})", value=roles_str, inline=False)
        else:
            embed.add_field(
                name=f"Роли ({len(roles)})",
                value="Слишком много ролей для отображения",
                inline=False,
            )

        # Добавляем уровень и опыт если доступно
        try:
            level, xp = await self.bot.leveling.get_level_xp(target.id, ctx.guild.id)
            if level > 0 or xp > 0:
                next_level_xp = self.bot.leveling.get_xp_for_level(level)
                embed.add_field(
                    name="Уровень и опыт",
                    value=f"Уровень: {level}\nОпыт: {xp}/{next_level_xp}",
                    inline=False,
                )
        except Exception:
            pass

        # Добавляем футер
        embed.set_footer(text=f"Запрошено: {ctx.author.display_name}")

        await ctx.send(embed=embed)


async def setup(bot):
    """Установка кога команд.

    Args:
        bot: Экземпляр бота
    """
    await bot.add_cog(Commands(bot))
