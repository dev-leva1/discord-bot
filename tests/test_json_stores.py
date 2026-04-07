"""Тесты для JSON сторов конфигурации."""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import json
from pathlib import Path

from infrastructure.config.json_store import JsonStore
from infrastructure.config.automod_store import AutomodConfigStore
from infrastructure.config.levels_store import LevelsStore
from infrastructure.config.tickets_store import TicketsConfigStore
from infrastructure.config.warnings_store import WarningsStore, WarningsConfigStore


class TestJsonStore:
    """Тесты базового JsonStore."""

    @pytest.fixture
    def json_store(self, tmp_path):
        """Фикстура для создания JsonStore."""
        def default_factory():
            return {"key": "value"}

        with patch("infrastructure.config.json_store.Path") as mock_path:
            mock_path.return_value = tmp_path / "test.json"
            store = JsonStore("test.json", default_factory)
            store.path = tmp_path / "test.json"
            return store

    def test_json_store_initialization(self, json_store):
        """Тест инициализации JsonStore."""
        assert json_store.path is not None
        assert json_store.default_factory is not None

    def test_load_creates_default_file(self, json_store):
        """Тест создания файла с дефолтными данными."""
        result = json_store.load()

        assert result == {"key": "value"}
        assert json_store.path.exists()

    def test_load_reads_existing_file(self, json_store):
        """Тест чтения существующего файла."""
        # Создаем файл с данными
        json_store.path.parent.mkdir(parents=True, exist_ok=True)
        with json_store.path.open("w", encoding="utf-8") as f:
            json.dump({"existing": "data"}, f)

        result = json_store.load()

        assert result == {"existing": "data"}

    def test_save_writes_to_file(self, json_store):
        """Тест сохранения данных в файл."""
        data = {"test": "data", "number": 123}

        json_store.save(data)

        assert json_store.path.exists()
        with json_store.path.open("r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data == data

    def test_save_creates_parent_directory(self, tmp_path):
        """Тест создания родительской директории."""
        def default_factory():
            return {}

        nested_path = tmp_path / "nested" / "dir" / "test.json"
        store = JsonStore("test.json", default_factory)
        store.path = nested_path

        store.save({"test": "data"})

        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_save_with_unicode(self, json_store):
        """Тест сохранения данных с Unicode символами."""
        data = {"russian": "Привет мир", "emoji": "🎉"}

        json_store.save(data)

        with json_store.path.open("r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data == data


class TestAutomodConfigStore:
    """Тесты AutomodConfigStore."""

    @pytest.fixture
    def automod_store(self, tmp_path):
        """Фикстура для создания AutomodConfigStore."""
        with patch("infrastructure.config.json_store.Path") as mock_path:
            mock_path.return_value = tmp_path / "automod_config.json"
            store = AutomodConfigStore("automod_config.json")
            store._store.path = tmp_path / "automod_config.json"
            return store

    def test_automod_store_initialization(self, automod_store):
        """Тест инициализации AutomodConfigStore."""
        assert automod_store._store is not None

    def test_load_returns_default_config(self, automod_store):
        """Тест загрузки дефолтной конфигурации."""
        config = automod_store.load()

        assert "banned_words" in config
        assert "spam_threshold" in config
        assert "spam_interval" in config
        assert "max_mentions" in config
        assert "max_warnings" in config
        assert "mute_duration" in config

        assert config["spam_threshold"] == 5
        assert config["spam_interval"] == 5
        assert config["max_mentions"] == 3
        assert config["max_warnings"] == 3
        assert config["mute_duration"] == "1h"
        assert config["banned_words"] == []

    def test_save_stores_config(self, automod_store):
        """Тест сохранения конфигурации."""
        config = {
            "banned_words": ["bad", "word"],
            "spam_threshold": 10,
            "spam_interval": 3,
            "max_mentions": 5,
            "max_warnings": 5,
            "mute_duration": "2h",
        }

        automod_store.save(config)

        loaded_config = automod_store.load()
        assert loaded_config == config


class TestLevelsStore:
    """Тесты LevelsStore."""

    @pytest.fixture
    def levels_store(self, tmp_path):
        """Фикстура для создания LevelsStore."""
        with patch("infrastructure.config.json_store.Path") as mock_path:
            mock_path.return_value = tmp_path / "levels.json"
            store = LevelsStore("levels.json")
            store._store.path = tmp_path / "levels.json"
            return store

    def test_levels_store_initialization(self, levels_store):
        """Тест инициализации LevelsStore."""
        assert levels_store._store is not None

    def test_load_returns_empty_dict(self, levels_store):
        """Тест загрузки пустого словаря по умолчанию."""
        data = levels_store.load()

        assert data == {}

    def test_save_stores_levels_data(self, levels_store):
        """Тест сохранения данных уровней."""
        data = {
            "123456": {
                "789012": {"xp": 1000, "level": 5}
            }
        }

        levels_store.save(data)

        loaded_data = levels_store.load()
        assert loaded_data == data


class TestTicketsConfigStore:
    """Тесты TicketsConfigStore."""

    @pytest.fixture
    def tickets_store(self, tmp_path):
        """Фикстура для создания TicketsConfigStore."""
        with patch("infrastructure.config.json_store.Path") as mock_path:
            mock_path.return_value = tmp_path / "tickets_config.json"
            store = TicketsConfigStore("tickets_config.json")
            store._store.path = tmp_path / "tickets_config.json"
            return store

    def test_tickets_store_initialization(self, tickets_store):
        """Тест инициализации TicketsConfigStore."""
        assert tickets_store._store is not None

    def test_load_returns_default_config(self, tickets_store):
        """Тест загрузки дефолтной конфигурации."""
        config = tickets_store.load()

        assert "ticket_category" in config
        assert "support_role" in config
        assert "ticket_counter" in config

        assert config["ticket_category"] is None
        assert config["support_role"] is None
        assert config["ticket_counter"] == 0

    def test_save_stores_config(self, tickets_store):
        """Тест сохранения конфигурации."""
        config = {
            "ticket_category": 123456,
            "support_role": 789012,
            "ticket_counter": 42,
        }

        tickets_store.save(config)

        loaded_config = tickets_store.load()
        assert loaded_config == config


class TestWarningsStore:
    """Тесты WarningsStore."""

    @pytest.fixture
    def warnings_store(self, tmp_path):
        """Фикстура для создания WarningsStore."""
        with patch("infrastructure.config.json_store.Path") as mock_path:
            mock_path.return_value = tmp_path / "warnings.json"
            store = WarningsStore("warnings.json")
            store._store.path = tmp_path / "warnings.json"
            return store

    def test_warnings_store_initialization(self, warnings_store):
        """Тест инициализации WarningsStore."""
        assert warnings_store._store is not None

    def test_load_returns_empty_dict(self, warnings_store):
        """Тест загрузки пустого словаря по умолчанию."""
        data = warnings_store.load()

        assert data == {}

    def test_save_stores_warnings_data(self, warnings_store):
        """Тест сохранения данных предупреждений."""
        data = {
            "123456": {
                "789012": [
                    {"reason": "Spam", "moderator": 111111, "timestamp": "2024-01-01"}
                ]
            }
        }

        warnings_store.save(data)

        loaded_data = warnings_store.load()
        assert loaded_data == data


class TestWarningsConfigStore:
    """Тесты WarningsConfigStore."""

    @pytest.fixture
    def warnings_config_store(self, tmp_path):
        """Фикстура для создания WarningsConfigStore."""
        with patch("infrastructure.config.json_store.Path") as mock_path:
            mock_path.return_value = tmp_path / "warnings_config.json"
            store = WarningsConfigStore("warnings_config.json")
            store._store.path = tmp_path / "warnings_config.json"
            return store

    def test_warnings_config_store_initialization(self, warnings_config_store):
        """Тест инициализации WarningsConfigStore."""
        assert warnings_config_store._store is not None

    def test_load_returns_default_config(self, warnings_config_store):
        """Тест загрузки дефолтной конфигурации."""
        config = warnings_config_store.load()

        assert "punishments" in config
        assert config["punishments"]["3"] == "mute_1h"
        assert config["punishments"]["5"] == "mute_12h"
        assert config["punishments"]["7"] == "kick"
        assert config["punishments"]["10"] == "ban"

    def test_save_stores_config(self, warnings_config_store):
        """Тест сохранения конфигурации."""
        config = {
            "punishments": {
                "2": "warn",
                "4": "mute_6h",
                "6": "kick",
                "8": "ban",
            }
        }

        warnings_config_store.save(config)

        loaded_config = warnings_config_store.load()
        assert loaded_config == config


class TestJsonStoreEdgeCases:
    """Тесты граничных случаев JsonStore."""

    def test_load_with_corrupted_json(self, tmp_path):
        """Тест обработки поврежденного JSON файла."""
        def default_factory():
            return {"default": "value"}

        store = JsonStore("test.json", default_factory)
        store.path = tmp_path / "test.json"

        # Создаем файл с невалидным JSON
        store.path.parent.mkdir(parents=True, exist_ok=True)
        with store.path.open("w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        # Должна быть ошибка при загрузке
        with pytest.raises(json.JSONDecodeError):
            store.load()

    def test_save_with_nested_data(self, tmp_path):
        """Тест сохранения вложенных данных."""
        def default_factory():
            return {}

        store = JsonStore("test.json", default_factory)
        store.path = tmp_path / "test.json"

        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }

        store.save(nested_data)

        loaded_data = store.load()
        assert loaded_data == nested_data

    def test_save_with_list_data(self, tmp_path):
        """Тест сохранения данных со списками."""
        def default_factory():
            return []

        store = JsonStore("test.json", default_factory)
        store.path = tmp_path / "test.json"

        list_data = [1, 2, 3, "four", {"five": 5}]

        store.save(list_data)

        loaded_data = store.load()
        assert loaded_data == list_data

    def test_multiple_load_calls(self, tmp_path):
        """Тест множественных вызовов load."""
        def default_factory():
            return {"counter": 0}

        store = JsonStore("test.json", default_factory)
        store.path = tmp_path / "test.json"

        # Первый load создает файл
        data1 = store.load()
        assert data1 == {"counter": 0}

        # Изменяем данные и сохраняем
        data1["counter"] = 5
        store.save(data1)

        # Второй load читает обновленные данные
        data2 = store.load()
        assert data2 == {"counter": 5}
