"""Тесты для обертки базы данных."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import os
import aiosqlite
import redis

from database.db import Database, get_db, get_redis, init_db


class TestDatabaseInitialization:
    """Тесты инициализации Database."""

    @pytest.fixture
    def database(self):
        """Фикстура для создания Database."""
        with patch.dict(os.environ, {"DB_PATH": "test.db", "DB_POOL_SIZE": "3"}):
            db = Database()
            return db

    def test_database_initialization(self, database):
        """Тест инициализации Database."""
        assert database.db_path == "test.db"
        assert database.pool_size == 3
        assert database.pool is None
        assert database.redis is None

    def test_database_initialization_defaults(self):
        """Тест инициализации с дефолтными значениями."""
        with patch.dict(os.environ, {}, clear=True):
            db = Database()
            assert "bot.db" in db.db_path
            assert db.pool_size == 5


class TestDatabaseSetup:
    """Тесты настройки базы данных."""

    @pytest.fixture
    def database(self):
        """Фикстура для создания Database."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:", "DB_POOL_SIZE": "2"}):
            db = Database()
            return db

    @pytest.mark.asyncio
    async def test_setup_creates_pool(self, database):
        """Тест создания пула соединений."""
        with patch("database.db.init_db"):
            with patch("os.path.exists", return_value=True):
                await database.setup()

                assert database.pool is not None
                assert len(database.pool) == 2

                # Закрываем соединения
                await database.close()

    @pytest.mark.asyncio
    async def test_setup_initializes_new_database(self, database):
        """Тест инициализации новой базы данных."""
        with patch("os.path.exists", return_value=False):
            with patch("database.db.init_db") as mock_init:
                await database.setup()

                mock_init.assert_called_once()
                await database.close()

    @pytest.mark.asyncio
    async def test_setup_with_redis(self, database):
        """Тест настройки с Redis."""
        database.redis_url = "redis://localhost:6379"

        mock_redis = MagicMock()
        mock_redis.ping = MagicMock()

        with patch("database.db.init_db"):
            with patch("os.path.exists", return_value=True):
                with patch("redis.from_url", return_value=mock_redis):
                    await database.setup()

                    assert database.redis is not None
                    mock_redis.ping.assert_called_once()

                    await database.close()

    @pytest.mark.asyncio
    async def test_setup_redis_connection_error(self, database):
        """Тест обработки ошибки подключения к Redis."""
        database.redis_url = "redis://localhost:6379"

        with patch("database.db.init_db"):
            with patch("os.path.exists", return_value=True):
                with patch("redis.from_url", side_effect=redis.ConnectionError):
                    await database.setup()

                    assert database.redis is None
                    await database.close()


class TestDatabaseOperations:
    """Тесты операций с базой данных."""

    @pytest.fixture
    async def database(self):
        """Фикстура для создания и настройки Database."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:", "DB_POOL_SIZE": "2"}):
            db = Database()
            with patch("database.db.init_db"):
                with patch("os.path.exists", return_value=True):
                    await db.setup()
            yield db
            await db.close()

    @pytest.mark.asyncio
    async def test_execute_query(self, database):
        """Тест выполнения SQL запроса."""
        await database.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
        )
        await database.execute("INSERT INTO test (name) VALUES (?)", ("test_name",))

        result = await database.fetch_one("SELECT name FROM test WHERE id = 1")
        assert result is not None
        assert result["name"] == "test_name"

    @pytest.mark.asyncio
    async def test_fetch_one_returns_none(self, database):
        """Тест fetch_one возвращает None если записи нет."""
        await database.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
        )

        result = await database.fetch_one("SELECT * FROM test WHERE id = 999")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_all_returns_list(self, database):
        """Тест fetch_all возвращает список."""
        await database.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
        )
        await database.execute("INSERT INTO test (name) VALUES (?)", ("name1",))
        await database.execute("INSERT INTO test (name) VALUES (?)", ("name2",))

        results = await database.fetch_all("SELECT name FROM test ORDER BY id")
        assert len(results) == 2
        assert results[0]["name"] == "name1"
        assert results[1]["name"] == "name2"

    @pytest.mark.asyncio
    async def test_fetch_all_returns_empty_list(self, database):
        """Тест fetch_all возвращает пустой список."""
        await database.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
        )

        results = await database.fetch_all("SELECT * FROM test")
        assert results == []

    @pytest.mark.asyncio
    async def test_execute_with_error_logs_and_raises(self, database):
        """Тест что execute логирует и пробрасывает ошибку."""
        with pytest.raises(Exception):
            await database.execute("INVALID SQL QUERY")


class TestDatabaseConnectionPool:
    """Тесты пула соединений."""

    @pytest.fixture
    async def database(self):
        """Фикстура для создания и настройки Database."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:", "DB_POOL_SIZE": "2"}):
            db = Database()
            with patch("database.db.init_db"):
                with patch("os.path.exists", return_value=True):
                    await db.setup()
            yield db
            await db.close()

    @pytest.mark.asyncio
    async def test_get_connection_from_pool(self, database):
        """Тест получения соединения из пула."""
        initial_pool_size = len(database.pool)

        async with database.get_connection() as conn:
            assert conn is not None
            # Соединение взято из пула
            assert len(database.pool) == initial_pool_size - 1

        # Соединение возвращено в пул
        assert len(database.pool) == initial_pool_size

    @pytest.mark.asyncio
    async def test_get_connection_when_pool_empty(self):
        """Тест получения соединения когда пул пуст."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:"}):
            db = Database()
            # Не вызываем setup, пул остается None

            async with db.get_connection() as conn:
                assert conn is not None

    @pytest.mark.asyncio
    async def test_close_closes_all_connections(self, database):
        """Тест закрытия всех соединений."""
        assert len(database.pool) > 0

        await database.close()

        assert database.pool == []


class TestDatabaseSchemaManagement:
    """Тесты управления схемой базы данных."""

    @pytest.fixture
    async def database(self):
        """Фикстура для создания и настройки Database."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:", "DB_POOL_SIZE": "1"}):
            db = Database()
            with patch("database.db.init_db"):
                with patch("os.path.exists", return_value=True):
                    await db.setup()
            yield db
            await db.close()

    @pytest.mark.asyncio
    async def test_check_and_update_schema_creates_tables(self, database):
        """Тест создания таблиц при проверке схемы."""
        # Проверяем что таблицы созданы
        tables = await database.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [t["name"] for t in tables]

        assert "levels" in table_names
        assert "settings" in table_names
        assert "role_rewards" in table_names
        assert "warnings" in table_names
        assert "tickets" in table_names

    @pytest.mark.asyncio
    async def test_check_and_update_schema_creates_indexes(self, database):
        """Тест создания индексов."""
        indexes = await database.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        index_names = [i["name"] for i in indexes]

        assert "idx_levels_guild" in index_names
        assert "idx_warnings_guild_user" in index_names
        assert "idx_tickets_channel" in index_names


class TestHelperFunctions:
    """Тесты вспомогательных функций."""

    def test_get_db_context_manager(self):
        """Тест контекстного менеджера get_db."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:"}):
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn

                with get_db() as conn:
                    assert conn is not None

                mock_conn.close.assert_called_once()

    def test_get_db_handles_error(self):
        """Тест обработки ошибки в get_db."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:"}):
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn

                with pytest.raises(Exception):
                    with get_db() as conn:
                        raise Exception("Test error")

                mock_conn.rollback.assert_called_once()
                mock_conn.close.assert_called_once()

    def test_get_redis_success(self):
        """Тест успешного подключения к Redis."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}):
            mock_redis = MagicMock()
            mock_redis.ping = MagicMock()

            with patch("redis.from_url", return_value=mock_redis):
                result = get_redis()

                assert result is not None
                mock_redis.ping.assert_called_once()

    def test_get_redis_connection_error(self):
        """Тест обработки ошибки подключения к Redis."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}):
            with patch("redis.from_url", side_effect=redis.ConnectionError):
                result = get_redis()

                assert result is None

    def test_get_redis_no_url(self):
        """Тест когда URL Redis не настроен."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_redis()

            assert result is None

    def test_init_db_creates_tables(self):
        """Тест создания таблиц при инициализации."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:"}):
            with patch("database.db.get_db") as mock_get_db:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
                mock_get_db.return_value.__exit__ = MagicMock()

                init_db()

                # Проверяем что execute вызван для создания таблиц
                assert mock_cursor.execute.call_count >= 5
                mock_conn.commit.assert_called_once()
