from discord.ext import commands
import discord
from utils.monitoring import track_message
import logging

logger = logging.getLogger(__name__)

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f'{self.bot.user} запущен и готов к работе!')
        await self.print_commands()

    async def print_commands(self):
        print('Slash-команды:')
        print('Основные:')
        print('/rank - Показать ваш уровень')
        print('/leaderboard - Таблица лидеров')
        print('/help - Список команд')
        print('\nМодерация:')
        print('/ban - Забанить пользователя')
        print('/kick - Выгнать пользователя')
        print('/mute - Замутить пользователя')
        print('/clear - Очистить сообщения')
        print('/warn_add - Выдать предупреждение')
        print('/warn_remove - Удалить предупреждение')
        print('/warn_list - Список предупреждений')
        print('/warn_clear - Очистить все предупреждения')
        print('\nТикеты:')
        print('/ticket_create - Создать тикет')
        print('/ticket_close - Закрыть тикет')
        print('/ticket_setup - Настроить систему тикетов')
        print('\nГолосовые каналы:')
        print('/voice_setup - Настроить временные каналы')
        print('/voice_name - Изменить название канала')
        print('/voice_limit - Установить лимит пользователей')
        print('/voice_lock - Закрыть канал')
        print('/voice_unlock - Открыть канал')
        print('\nНастройки:')
        print('/setwelcome - Установить канал приветствий')
        print('/setlogs - Установить канал для логов')
        print('/addrole - Добавить роль за уровень')
        print('/removerole - Удалить роль за уровень')
        print('/listroles - Список ролей за уровни')
        print('/automod - Настройка автомодерации')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        track_message()
        
        # Проверка автомодерации (пропускаем для владельца сервера)
        if message.guild and message.author.id != message.guild.owner_id:
            if not await self.bot.automod.check_message(message):
                return
        
        await self.bot.leveling.add_experience(message.author.id, message.guild.id)
        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        await self.bot.logging.log_message_delete(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self.bot.logging.log_message_edit(before, after)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.bot.logging.log_member_join(member)
        await self.bot.welcome.send_welcome(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.bot.logging.log_member_remove(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        await self.bot.logging.log_member_update(before, after)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        await self.bot.logging.log_voice_state_update(member, before, after)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await self.bot.logging.log_ban(guild, user)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        await self.bot.logging.log_unban(guild, user)

async def setup(bot):
    await bot.add_cog(Events(bot)) 