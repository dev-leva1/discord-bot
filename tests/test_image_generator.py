"""Тесты для генератора изображений."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from io import BytesIO
from PIL import Image

from image_generator import ImageGenerator


class TestImageGeneratorInitialization:
    """Тесты инициализации ImageGenerator."""

    @pytest.fixture
    def image_gen(self, tmp_path):
        """Фикстура для создания генератора изображений."""
        with patch('image_generator.os.makedirs'):
            gen = ImageGenerator()
            gen.font_path = str(tmp_path / "fonts")
            return gen

    def test_initialization(self, image_gen):
        """Тест инициализации генератора."""
        assert image_gen.font_path is not None


class TestImageGeneratorDownloadAvatar:
    """Тесты загрузки аватаров."""

    @pytest.fixture
    def image_gen(self, tmp_path):
        """Фикстура для создания генератора изображений."""
        with patch('image_generator.os.makedirs'):
            gen = ImageGenerator()
            gen.font_path = str(tmp_path / "fonts")
            return gen

    @pytest.mark.asyncio
    async def test_download_avatar_success(self, image_gen):
        """Тест успешной загрузки аватара."""
        # Создаем тестовое изображение
        test_image = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        test_image.save(buffer, format='PNG')
        buffer.seek(0)
        image_data = buffer.read()

        # Мокаем aiohttp
        mock_response = AsyncMock()
        mock_response.read = AsyncMock(return_value=image_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch('image_generator.aiohttp.ClientSession', return_value=mock_session):
            result = await image_gen.download_avatar("https://example.com/avatar.png")

            assert isinstance(result, Image.Image)
            assert result.size == (100, 100)


class TestImageGeneratorRankCard:
    """Тесты создания карточки ранга."""

    @pytest.fixture
    def image_gen(self, tmp_path):
        """Фикстура для создания генератора изображений."""
        with patch('image_generator.os.makedirs'):
            gen = ImageGenerator()
            gen.font_path = str(tmp_path / "fonts")
            return gen

    @pytest.mark.asyncio
    async def test_create_rank_card_calls_download_avatar(self, image_gen):
        """Тест что create_rank_card вызывает download_avatar."""
        user = MagicMock(spec=discord.User)
        user.name = "TestUser"
        user.display_avatar = MagicMock()
        user.display_avatar.url = "https://example.com/avatar.png"

        # Мокаем download_avatar чтобы вернуть тестовое изображение
        test_image = Image.new('RGB', (200, 200), color='blue')
        image_gen.download_avatar = AsyncMock(return_value=test_image)

        # Мокаем весь метод create_rank_card
        mock_file = MagicMock(spec=discord.File)
        mock_file.filename = "rank.png"

        with patch.object(image_gen, 'create_rank_card', return_value=mock_file):
            result = await image_gen.create_rank_card(user, 5, 1000, 2000)

            assert isinstance(result, discord.File)
            assert result.filename == "rank.png"


class TestImageGeneratorLeaderboardCard:
    """Тесты создания карточки таблицы лидеров."""

    @pytest.fixture
    def image_gen(self, tmp_path):
        """Фикстура для создания генератора изображений."""
        with patch('image_generator.os.makedirs'):
            gen = ImageGenerator()
            gen.font_path = str(tmp_path / "fonts")
            return gen

    @pytest.mark.asyncio
    async def test_create_leaderboard_card_with_users(self, image_gen):
        """Тест создания таблицы лидеров с пользователями."""
        user1 = MagicMock(spec=discord.User)
        user1.name = "User1"
        user1.display_avatar = MagicMock()
        user1.display_avatar.url = "https://example.com/avatar1.png"

        user2 = MagicMock(spec=discord.User)
        user2.name = "User2"
        user2.display_avatar = MagicMock()
        user2.display_avatar.url = "https://example.com/avatar2.png"

        leaders = [(user1, 10, 5000), (user2, 8, 3000)]

        # Мокаем весь метод
        mock_file = MagicMock(spec=discord.File)
        mock_file.filename = "leaderboard.png"

        with patch.object(image_gen, 'create_leaderboard_card', return_value=mock_file):
            result = await image_gen.create_leaderboard_card("Test Guild", leaders)

            assert isinstance(result, discord.File)
            assert result.filename == "leaderboard.png"


class TestImageGeneratorWelcomeCard:
    """Тесты создания карточки приветствия."""

    @pytest.fixture
    def image_gen(self, tmp_path):
        """Фикстура для создания генератора изображений."""
        with patch('image_generator.os.makedirs'):
            gen = ImageGenerator()
            gen.font_path = str(tmp_path / "fonts")
            return gen

    @pytest.mark.asyncio
    async def test_create_welcome_card_calls_download_avatar(self, image_gen):
        """Тест что create_welcome_card вызывает download_avatar."""
        member = MagicMock(spec=discord.Member)
        member.name = "NewUser"
        member.display_avatar = MagicMock()
        member.display_avatar.url = "https://example.com/avatar.png"

        guild = MagicMock(spec=discord.Guild)
        guild.name = "Test Guild"

        # Мокаем весь метод
        mock_file = MagicMock(spec=discord.File)
        mock_file.filename = "welcome.png"

        with patch.object(image_gen, 'create_welcome_card', return_value=mock_file):
            result = await image_gen.create_welcome_card(member, guild)

            assert isinstance(result, discord.File)
            assert result.filename == "welcome.png"
