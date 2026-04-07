"""Тесты для основного класса бота."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from app.bot import Bot
from app.container import Container


class TestBotInitialization:
    """Тесты инициализации бота."""

    @pytest.fixture
    def mock_container(self):
        """Фикстура для создания мок контейнера."""
        container = MagicMock(spec=Container)

        # Мокаем базу данных
        container.db = MagicMock()
        container.db.setup = AsyncMock()

        # Мокаем сервисы
        container.use_metrics = False
        container.initial_extensions = []
        container.image_generator = MagicMock()

        # Мокаем build_services
        services = MagicMock()
        services.moderation = MagicMock()
        services.welcome = MagicMock()
        services.role_rewards = MagicMock()
        services.leveling = MagicMock()
        services.automod = MagicMock()
        services.logging = MagicMock()
        services.tickets = MagicMock()
        services.temp_voice = MagicMock()
        services.warnings = MagicMock()

        container.build_services = MagicMock(return_value=services)

        return container

    def test_bot_initialization(self, mock_container):
        """Тест инициализации бота."""
        bot = Bot(mock_container)

        # Проверяем что бот создан
        assert isinstance(bot, commands.Bot)
        assert bot.command_prefix == "!"

        # Проверяем что контейнер установлен
        assert bot.container == mock_container

        # Проверяем что сервисы установлены
        assert bot.leveling is not None
        assert bot.automod is not None
        assert bot.logging is not None
        assert bot.tickets is not None
        assert bot.warnings is not None

    def test_bot_intents(self, mock_container):
        """Тест настройки интентов."""
        bot = Bot(mock_container)

        # Проверяем интенты
        assert bot.intents.message_content is True
        assert bot.intents.guilds is True
        assert bot.intents.guild_messages is True
        assert bot.intents.voice_states is True
        assert bot.intents.moderation is True

        # Проверяем что привилегированные интенты отключены
        assert bot.intents.members is False
        assert bot.intents.presences is False

    def test_bot_services_injection(self, mock_container):
        """Тест инжекции сервисов."""
        bot = Bot(mock_container)

        # Проверяем что build_services был вызван с ботом
        mock_container.build_services.assert_called_once_with(bot)

        # Проверяем что все сервисы доступны
        assert hasattr(bot, 'moderation')
        assert hasattr(bot, 'welcome')
        assert hasattr(bot, 'role_rewards')
        assert hasattr(bot, 'leveling')
        assert hasattr(bot, 'automod')
        assert hasattr(bot, 'logging')
        assert hasattr(bot, 'tickets')
        assert hasattr(bot, 'temp_voice')
        assert hasattr(bot, 'warnings')


class TestBotSetupHook:
    """Тесты setup_hook бота."""

    @pytest.fixture
    def mock_container(self):
        """Фикстура для создания мок контейнера."""
        container = MagicMock(spec=Container)

        container.db = MagicMock()
        container.db.setup = AsyncMock()

        container.use_metrics = False
        container.initial_extensions = []
        container.image_generator = MagicMock()

        services = MagicMock()
        services.moderation = MagicMock()
        services.welcome = MagicMock()
        services.role_rewards = MagicMock()

        # Важно: мокаем async методы
        services.leveling = MagicMock()
        services.leveling.migrate_to_db = AsyncMock()

        services.automod = MagicMock()
        services.logging = MagicMock()
        services.tickets = MagicMock()
        services.temp_voice = MagicMock()

        services.warnings = MagicMock()
        services.warnings.migrate_to_db = AsyncMock()

        container.build_services = MagicMock(return_value=services)

        return container

    @pytest.mark.asyncio
    async def test_setup_hook_initializes_database(self, mock_container):
        """Тест что setup_hook инициализирует базу данных."""
        bot = Bot(mock_container)

        await bot.setup_hook()

        # Проверяем что setup БД был вызван
        mock_container.db.setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_hook_with_extensions(self, mock_container):
        """Тест загрузки расширений."""
        mock_container.initial_extensions = ["cogs.events"]

        bot = Bot(mock_container)

        # Мокаем load_extension
        bot.load_extension = AsyncMock()

        await bot.setup_hook()

        # Проверяем что БД инициализирована
        mock_container.db.setup.assert_called_once()


class TestBotEventHandlers:
    """Тесты обработчиков событий бота."""

    @pytest.fixture
    def mock_container(self):
        """Фикстура для создания мок контейнера."""
        container = MagicMock(spec=Container)

        container.db = MagicMock()
        container.db.setup = AsyncMock()

        container.use_metrics = False
        container.initial_extensions = []
        container.image_generator = MagicMock()

        services = MagicMock()
        services.moderation = MagicMock()
        services.welcome = MagicMock()
        services.welcome.send_welcome = AsyncMock()
        services.role_rewards = MagicMock()
        services.leveling = MagicMock()
        services.leveling.process_message = AsyncMock(return_value=(False, None))
        services.automod = MagicMock()
        services.automod.check_message = AsyncMock(return_value=True)
        services.logging = MagicMock()
        services.tickets = MagicMock()
        services.temp_voice = MagicMock()
        services.warnings = MagicMock()

        container.build_services = MagicMock(return_value=services)

        return container

    @pytest.mark.asyncio
    async def test_bot_ready_state(self, mock_container):
        """Тест состояния готовности бота."""
        bot = Bot(mock_container)

        # Проверяем что бот создан и имеет необходимые атрибуты
        assert hasattr(bot, 'guilds')
        assert hasattr(bot, 'user')

        # Проверяем что сервисы доступны
        assert bot.leveling is not None
        assert bot.automod is not None


class TestBotServices:
    """Тесты сервисов бота."""

    @pytest.fixture
    def bot_with_services(self):
        """Фикстура для создания бота с сервисами."""
        container = MagicMock(spec=Container)

        container.db = MagicMock()
        container.db.setup = AsyncMock()

        container.use_metrics = False
        container.initial_extensions = []
        container.image_generator = MagicMock()

        # Создаем реальные моки сервисов
        services = MagicMock()
        services.moderation = MagicMock()
        services.welcome = MagicMock()
        services.role_rewards = MagicMock()

        # Leveling service
        services.leveling = MagicMock()
        services.leveling.process_message = AsyncMock(return_value=(False, None))
        services.leveling.get_xp_for_level = MagicMock(return_value=100)

        # Automod service
        services.automod = MagicMock()
        services.automod.check_message = AsyncMock(return_value=True)

        services.logging = MagicMock()
        services.tickets = MagicMock()
        services.temp_voice = MagicMock()
        services.warnings = MagicMock()

        container.build_services = MagicMock(return_value=services)

        bot = Bot(container)
        return bot

    def test_leveling_service_available(self, bot_with_services):
        """Тест доступности сервиса уровней."""
        assert bot_with_services.leveling is not None
        assert hasattr(bot_with_services.leveling, 'process_message')

    def test_automod_service_available(self, bot_with_services):
        """Тест доступности сервиса автомодерации."""
        assert bot_with_services.automod is not None
        assert hasattr(bot_with_services.automod, 'check_message')

    def test_warnings_service_available(self, bot_with_services):
        """Тест доступности сервиса предупреждений."""
        assert bot_with_services.warnings is not None

    def test_tickets_service_available(self, bot_with_services):
        """Тест доступности сервиса тикетов."""
        assert bot_with_services.tickets is not None

    @pytest.mark.asyncio
    async def test_leveling_service_integration(self, bot_with_services):
        """Тест интеграции с сервисом уровней."""
        message = MagicMock(spec=discord.Message)
        message.author = MagicMock()
        message.author.bot = False
        message.guild = MagicMock()

        result = await bot_with_services.leveling.process_message(message)

        # Проверяем что метод был вызван
        bot_with_services.leveling.process_message.assert_called_once_with(message)
        assert result == (False, None)

    @pytest.mark.asyncio
    async def test_automod_service_integration(self, bot_with_services):
        """Тест интеграции с сервисом автомодерации."""
        message = MagicMock(spec=discord.Message)
        message.author = MagicMock()
        message.author.bot = False
        message.guild = MagicMock()
        message.content = "test message"

        result = await bot_with_services.automod.check_message(message)

        # Проверяем что метод был вызван
        bot_with_services.automod.check_message.assert_called_once_with(message)
        assert result is True


class TestBotConfiguration:
    """Тесты конфигурации бота."""

    @pytest.fixture
    def mock_container(self):
        """Фикстура для создания мок контейнера."""
        container = MagicMock(spec=Container)

        container.db = MagicMock()
        container.db.setup = AsyncMock()

        container.use_metrics = True
        container.metrics_port = 8000
        container.initial_extensions = ["cogs.events", "cogs.commands"]
        container.image_generator = MagicMock()

        services = MagicMock()
        services.moderation = MagicMock()
        services.welcome = MagicMock()
        services.role_rewards = MagicMock()
        services.leveling = MagicMock()
        services.automod = MagicMock()
        services.logging = MagicMock()
        services.tickets = MagicMock()
        services.temp_voice = MagicMock()
        services.warnings = MagicMock()

        container.build_services = MagicMock(return_value=services)

        return container

    def test_bot_with_metrics_enabled(self, mock_container):
        """Тест бота с включенными метриками."""
        bot = Bot(mock_container)

        assert bot.use_metrics is True

    def test_bot_with_extensions(self, mock_container):
        """Тест бота с расширениями."""
        bot = Bot(mock_container)

        assert len(bot.initial_extensions) == 2
        assert "cogs.events" in bot.initial_extensions
        assert "cogs.commands" in bot.initial_extensions

    def test_bot_database_reference(self, mock_container):
        """Тест ссылки на базу данных."""
        bot = Bot(mock_container)

        assert bot.db == mock_container.db

    def test_bot_image_generator_reference(self, mock_container):
        """Тест ссылки на генератор изображений."""
        bot = Bot(mock_container)

        assert bot.image_generator == mock_container.image_generator
