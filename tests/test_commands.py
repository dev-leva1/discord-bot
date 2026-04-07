"""Тесты для основных команд бота."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from cogs.commands import Commands


class TestCommandsInitialization:
    """Тесты инициализации Commands."""

    @pytest.fixture
    def commands_cog(self):
        """Фикстура для создания Commands cog."""
        bot = MagicMock()
        return Commands(bot)

    def test_commands_initialization(self, commands_cog):
        """Тест инициализации Commands."""
        assert commands_cog.bot is not None


class TestRankCommand:
    """Тесты команды rank."""

    @pytest.fixture
    def commands_cog(self):
        """Фикстура для создания Commands cog."""
        bot = MagicMock()
        bot.leveling = MagicMock()
        bot.leveling.get_level_xp = AsyncMock(return_value=(5, 1000))
        bot.leveling.get_xp_for_level = MagicMock(return_value=2000)
        bot.image_generator = MagicMock()
        bot.image_generator.create_rank_card = AsyncMock()
        return Commands(bot)

    @pytest.mark.asyncio
    async def test_rank_command_for_self(self, commands_cog):
        """Тест команды rank для себя."""
        ctx = AsyncMock()
        ctx.author = MagicMock(spec=discord.Member)
        ctx.author.id = 123456
        ctx.author.bot = False
        ctx.guild = MagicMock()
        ctx.guild.id = 789012
        ctx.send = AsyncMock()

        rank_card = MagicMock()
        commands_cog.bot.image_generator.create_rank_card.return_value = rank_card

        await commands_cog.rank.callback(commands_cog, ctx)

        commands_cog.bot.leveling.get_level_xp.assert_called_once_with(123456, 789012)
        ctx.send.assert_called_once_with(file=rank_card)

    @pytest.mark.asyncio
    async def test_rank_command_for_bot(self, commands_cog):
        """Тест команды rank для бота."""
        ctx = AsyncMock()
        ctx.send = AsyncMock()

        member = MagicMock(spec=discord.Member)
        member.bot = True

        await commands_cog.rank.callback(commands_cog, ctx, member)

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "боты не могут получать опыт" in call_args.lower()


class TestLeaderboardCommand:
    """Тесты команды leaderboard."""

    @pytest.fixture
    def commands_cog(self):
        """Фикстура для создания Commands cog."""
        bot = MagicMock()
        bot.leveling = MagicMock()
        bot.leveling.get_leaderboard = AsyncMock()
        bot.image_generator = MagicMock()
        bot.image_generator.create_leaderboard_card = AsyncMock()
        return Commands(bot)

    @pytest.mark.asyncio
    async def test_leaderboard_command_success(self, commands_cog):
        """Тест успешного выполнения команды leaderboard."""
        ctx = AsyncMock()
        ctx.guild = MagicMock()
        ctx.guild.id = 789012
        ctx.guild.name = "Test Guild"
        ctx.send = AsyncMock()

        user1 = MagicMock(spec=discord.Member)
        user1.id = 111111

        ctx.guild.get_member = lambda uid: user1 if uid == 111111 else None

        commands_cog.bot.leveling.get_leaderboard.return_value = [
            {"user_id": "111111", "level": 10, "xp": 5000},
        ]

        leaderboard_card = MagicMock()
        commands_cog.bot.image_generator.create_leaderboard_card.return_value = leaderboard_card

        await commands_cog.leaderboard.callback(commands_cog, ctx)

        commands_cog.bot.leveling.get_leaderboard.assert_called_once_with(789012, 10)
        ctx.send.assert_called_once_with(file=leaderboard_card)

    @pytest.mark.asyncio
    async def test_leaderboard_command_no_data(self, commands_cog):
        """Тест команды leaderboard без данных."""
        ctx = AsyncMock()
        ctx.guild = MagicMock()
        ctx.guild.id = 789012
        ctx.send = AsyncMock()

        commands_cog.bot.leveling.get_leaderboard.return_value = []

        await commands_cog.leaderboard.callback(commands_cog, ctx)

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "пока нет участников" in call_args.lower()


class TestBotHelpCommand:
    """Тесты команды bothelp."""

    @pytest.fixture
    def commands_cog(self):
        """Фикстура для создания Commands cog."""
        bot = MagicMock()
        return Commands(bot)

    @pytest.mark.asyncio
    async def test_bothelp_command_for_regular_user(self, commands_cog):
        """Тест команды bothelp для обычного пользователя."""
        ctx = AsyncMock()
        ctx.author = MagicMock()
        ctx.author.id = 123456
        ctx.author.guild_permissions = MagicMock()
        ctx.author.guild_permissions.administrator = False
        ctx.author.guild_permissions.ban_members = False
        ctx.guild = MagicMock()
        ctx.guild.owner_id = 999999
        ctx.send = AsyncMock()

        await commands_cog.commands_list.callback(commands_cog, ctx)

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args
        assert "embed" in call_args.kwargs


class TestPingCommand:
    """Тесты команды ping."""

    @pytest.fixture
    def commands_cog(self):
        """Фикстура для создания Commands cog."""
        bot = MagicMock()
        return Commands(bot)

    @pytest.mark.asyncio
    async def test_ping_command_good_latency(self, commands_cog):
        """Тест команды ping с хорошей задержкой."""
        ctx = AsyncMock()
        ctx.send = AsyncMock()

        commands_cog.bot.latency = 0.05  # 50ms

        await commands_cog.ping.callback(commands_cog, ctx)

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args
        embed = call_args.kwargs["embed"]
        assert embed.color == discord.Color.green()


class TestServerInfoCommand:
    """Тесты команды serverinfo."""

    @pytest.fixture
    def commands_cog(self):
        """Фикстура для создания Commands cog."""
        bot = MagicMock()
        return Commands(bot)

    @pytest.mark.asyncio
    async def test_serverinfo_command(self, commands_cog):
        """Тест команды serverinfo."""
        ctx = AsyncMock()
        ctx.guild = MagicMock()
        ctx.guild.id = 123456
        ctx.guild.name = "Test Guild"
        ctx.guild.icon = None
        ctx.guild.owner = MagicMock()
        ctx.guild.owner.mention = "@Owner"
        ctx.guild.created_at = MagicMock()
        ctx.guild.created_at.strftime = MagicMock(return_value="01.01.2020")
        ctx.guild.member_count = 100
        ctx.guild.members = [MagicMock(bot=False) for _ in range(90)] + [
            MagicMock(bot=True) for _ in range(10)
        ]
        ctx.guild.text_channels = [MagicMock() for _ in range(10)]
        ctx.guild.voice_channels = [MagicMock() for _ in range(5)]
        ctx.guild.categories = [MagicMock() for _ in range(3)]
        ctx.guild.roles = [MagicMock() for _ in range(15)]
        ctx.guild.emojis = [MagicMock() for _ in range(20)]
        ctx.guild.premium_tier = 0
        ctx.author = MagicMock()
        ctx.author.display_name = "TestUser"
        ctx.send = AsyncMock()

        await commands_cog.serverinfo.callback(commands_cog, ctx)

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args
        assert "embed" in call_args.kwargs


class TestUserInfoCommand:
    """Тесты команды userinfo."""

    @pytest.fixture
    def commands_cog(self):
        """Фикстура для создания Commands cog."""
        bot = MagicMock()
        bot.leveling = MagicMock()
        bot.leveling.get_level_xp = AsyncMock(return_value=(5, 1000))
        bot.leveling.get_xp_for_level = MagicMock(return_value=2000)
        return Commands(bot)

    @pytest.mark.asyncio
    async def test_userinfo_command_for_self(self, commands_cog):
        """Тест команды userinfo для себя."""
        ctx = AsyncMock()
        ctx.author = MagicMock(spec=discord.Member)
        ctx.author.id = 123456
        ctx.author.display_name = "TestUser"
        ctx.author.bot = False
        ctx.author.status = discord.Status.online
        ctx.author.color = discord.Color.blue()  # Используем настоящий Color объект
        ctx.author.display_avatar = MagicMock()
        ctx.author.display_avatar.url = "https://example.com/avatar.png"
        ctx.author.joined_at = MagicMock()
        ctx.author.joined_at.strftime = MagicMock(return_value="01.01.2020 12:00")
        ctx.author.created_at = MagicMock()
        ctx.author.created_at.strftime = MagicMock(return_value="01.01.2019 12:00")

        # Создаем роль с правильным mention
        role = MagicMock()
        role.name = "@everyone"
        role.mention = "@everyone"
        ctx.author.roles = [role]

        ctx.author.activities = []
        ctx.guild = MagicMock()
        ctx.guild.id = 789012
        ctx.send = AsyncMock()

        await commands_cog.userinfo.callback(commands_cog, ctx)

        ctx.send.assert_called_once()
        call_args = ctx.send.call_args
        assert "embed" in call_args.kwargs


class TestCommandsSetup:
    """Тесты функции setup."""

    @pytest.mark.asyncio
    async def test_setup_adds_cog(self):
        """Тест добавления cog к боту."""
        bot = MagicMock()
        bot.add_cog = AsyncMock()

        from cogs.commands import setup
        await setup(bot)

        bot.add_cog.assert_called_once()
        args = bot.add_cog.call_args[0]
        assert isinstance(args[0], Commands)
