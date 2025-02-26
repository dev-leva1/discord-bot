from discord.ext import commands
import discord
from utils.monitoring import monitor_command

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="rank", description="Показывает ваш текущий уровень и опыт")
    @monitor_command
    async def rank(self, ctx):
        level, xp = await self.bot.leveling.get_level_xp(ctx.author.id, ctx.guild.id)
        next_level_xp = self.bot.leveling.get_xp_for_level(level)
        
        # Создаем красивую карточку
        rank_card = await self.bot.image_generator.create_rank_card(
            ctx.author,
            level,
            xp,
            next_level_xp
        )
        
        await ctx.send(file=rank_card)

    @commands.hybrid_command(name="leaderboard", description="Показывает таблицу лидеров по уровням")
    @monitor_command
    async def leaderboard(self, ctx):
        leaders_data = await self.bot.leveling.get_leaderboard(ctx.guild.id)
        
        if not leaders_data:
            await ctx.send("На сервере пока нет участников с опытом!", ephemeral=True)
            return
            
        # Преобразуем данные для генератора изображений
        leaders = []
        for data in leaders_data:
            user = ctx.guild.get_member(int(data["user_id"]))
            if user:
                leaders.append((user, data["level"], data["xp"]))
                
        # Создаем красивую карточку лидерборда
        leaderboard_card = await self.bot.image_generator.create_leaderboard_card(
            ctx.guild.name,
            leaders
        )
        
        await ctx.send(file=leaderboard_card)

    @commands.hybrid_command(name="help", description="Показывает список доступных команд")
    @monitor_command
    async def help(self, ctx):
        embed = discord.Embed(
            title="📚 Помощь по командам",
            description="Список всех доступных команд:",
            color=discord.Color.blue()
        )
        
        # Проверяем права пользователя
        is_owner = ctx.guild.owner_id == ctx.author.id
        show_admin_commands = is_owner or ctx.author.guild_permissions.administrator
        show_mod_commands = show_admin_commands or ctx.author.guild_permissions.ban_members
        
        # Основные команды (доступны всем)
        embed.add_field(
            name="📊 Уровни и опыт", 
            value="""
• `/rank` - Показать ваш текущий уровень и опыт
• `/leaderboard` - Таблица лидеров сервера
            """, 
            inline=False
        )
        
        # Команды тикетов
        embed.add_field(
            name="🎫 Тикеты",
            value="""
• `/ticket create` - Создать тикет
• `/ticket close` - Закрыть тикет
            """,
            inline=False
        )
        
        # Команды голосовых каналов
        embed.add_field(
            name="🔊 Голосовые каналы",
            value="""
• `/voice name` - Изменить название канала
• `/voice limit` - Установить лимит пользователей
• `/voice lock` - Закрыть канал
• `/voice unlock` - Открыть канал
            """,
            inline=False
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
• `/warn add` - Выдать предупреждение
• `/warn remove` - Удалить предупреждение
• `/warn list` - Список предупреждений
• `/warn clear` - Очистить все предупреждения
                """,
                inline=False
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
                inline=False
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
                inline=False
            )
            
        # Настройки ролей
        if show_admin_commands:
            embed.add_field(
                name="👥 Управление ролями",
                value="""
• `/addrole` - Добавить роль-награду за уровень
• `/removerole` - Удалить роль-награду
• `/listroles` - Список ролей-наград за уровни
                """,
                inline=False
            )
        
        # Добавляем информацию о правах
        if is_owner:
            embed.set_footer(text="👑 Показаны все команды (вы владелец сервера)")
        elif not show_admin_commands:
            embed.set_footer(text="ℹ️ Некоторые команды скрыты, так как у вас недостаточно прав")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Commands(bot)) 