# Документация по тестам

Полное руководство по тестированию MEE6 Discord бота.

## Обзор

Проект содержит 119 автотестов, покрывающих весь core функционал бота:
- Инициализация и конфигурация бота
- Системы модерации и автомодерации
- Система уровней и опыта
- Система предупреждений
- Система тикетов
- Репозитории базы данных
- Вспомогательные функции Discord

## Структура тестов

```
tests/
├── conftest.py                 # Настройка pytest, добавление src/ в sys.path
├── test_bot.py                 # Тесты основного класса бота (16 тестов)
├── test_contracts.py           # Тесты контрактов приложения (1 тест)
├── test_moderation.py          # Тесты команд модерации (8 тестов)
├── test_automod.py             # Тесты автомодерации (18 тестов)
├── test_leveling_system.py     # Тесты системы уровней (21 тест)
├── test_warning_system.py      # Тесты системы предупреждений (16 тестов)
├── test_repositories.py        # Тесты репозиториев БД (19 тестов)
└── test_discord_helpers.py     # Тесты вспомогательных функций (20 тестов)
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### Конкретный файл
```bash
pytest tests/test_bot.py -v
```

### Конкретный тест
```bash
pytest tests/test_bot.py::TestBotInitialization::test_bot_initialization -v
```

### С подробным выводом ошибок
```bash
pytest tests/test_bot.py -v --tb=short
```

### Без вывода traceback
```bash
pytest tests/ -v --tb=no -q
```

## Детальное описание тестов

### test_bot.py (16 тестов)

Тесты основного класса бота с DI Container.

#### TestBotInitialization (3 теста)
- `test_bot_initialization` - проверка создания бота с контейнером
- `test_bot_intents` - проверка настройки Discord интентов
- `test_bot_services_injection` - проверка инжекции сервисов через контейнер

#### TestBotSetupHook (2 теста)
- `test_setup_hook_initializes_database` - проверка инициализации БД при старте
- `test_setup_hook_with_extensions` - проверка загрузки расширений

#### TestBotEventHandlers (1 тест)
- `test_bot_ready_state` - проверка состояния готовности бота

#### TestBotServices (6 тестов)
- `test_leveling_service_available` - доступность сервиса уровней
- `test_automod_service_available` - доступность сервиса автомодерации
- `test_warnings_service_available` - доступность сервиса предупреждений
- `test_tickets_service_available` - доступность сервиса тикетов
- `test_leveling_service_integration` - интеграция с сервисом уровней
- `test_automod_service_integration` - интеграция с сервисом автомодерации

#### TestBotConfiguration (4 теста)
- `test_bot_with_metrics_enabled` - проверка включения метрик
- `test_bot_with_extensions` - проверка списка расширений
- `test_bot_database_reference` - проверка ссылки на БД
- `test_bot_image_generator_reference` - проверка ссылки на генератор изображений

### test_moderation.py (8 тестов)

Тесты команд модерации (ban, kick, mute, clear).

- `test_ban_command` - успешный бан пользователя
- `test_ban_command_no_permission` - бан без прав (равная роль)
- `test_kick_command` - успешный кик пользователя
- `test_kick_command_no_permission` - кик без прав
- `test_mute_command` - успешный мут с парсингом времени
- `test_mute_command_invalid_duration` - мут с неверным форматом времени
- `test_clear_command` - очистка сообщений в канале
- `test_clear_command_invalid_amount` - очистка с неверным количеством

**Важно**: Команды Discord вызываются через `.callback()`:
```python
await moderation.ban.callback(moderation, interaction, member, "reason")
```

### test_automod.py (18 тестов)

Тесты системы автомодерации.

#### TestAutoModConfiguration (3 теста)
- Загрузка и сохранение конфигурации
- Проверка значений по умолчанию

#### TestAutoModBannedWords (3 теста)
- Обнаружение запрещенных слов
- Регистронезависимость
- Пропуск чистых сообщений

#### TestAutoModSpamDetection (2 теста)
- Срабатывание анти-спама при превышении порога
- Сброс счетчика после интервала

#### TestAutoModMentions (2 теста)
- Блокировка массовых упоминаний
- Пропуск допустимого количества упоминаний

#### TestAutoModWarnings (2 теста)
- Увеличение счетчика предупреждений
- Автоматический мут при достижении лимита

#### TestAutoModCleanup (4 теста)
- Очистка старых записей спама
- Сохранение свежих записей
- Очистка предупреждений после часа

#### TestAutoModBotMessages (2 теста)
- Игнорирование сообщений от ботов
- Игнорирование DM сообщений

### test_warning_system.py (16 тестов)

Тесты системы предупреждений.

#### TestWarningSystemConfiguration (3 теста)
- Загрузка предупреждений из JSON
- Загрузка конфигурации наказаний
- Сохранение предупреждений

#### TestWarningSystemGetUserWarnings (3 теста)
- Получение существующих предупреждений
- Создание пустого списка для нового пользователя
- Создание гильдии если не существует

#### TestWarningSystemAddWarning (3 теста)
- Запрет выдачи предупреждения боту
- Запрет выдачи с равной ролью
- Успешное добавление предупреждения

#### TestWarningSystemRemoveWarning (3 теста)
- Удаление когда нет предупреждений
- Удаление с неверным индексом
- Успешное удаление предупреждения

#### TestWarningSystemCleanup (1 тест)
- Очистка устаревших предупреждений через репозиторий

#### TestWarningSystemMigration (2 теста)
- Миграция предупреждений в БД
- Миграция без репозитория

#### TestWarningSystemPunishments (1 тест)
- Автоматический мут на 1 час при достижении порога

### test_leveling_system.py (21 тест)

Тесты системы уровней и опыта.

#### TestLevelingSystemConfiguration (3 теста)
- Загрузка данных уровней
- Сохранение данных
- Значения по умолчанию

#### TestLevelingSystemXPGain (4 теста)
- Начисление XP за сообщение
- Кулдаун между сообщениями
- Игнорирование ботов
- Игнорирование DM

#### TestLevelingSystemLevelUp (3 теста)
- Повышение уровня при достижении порога
- Отсутствие повышения при недостатке XP
- Расчет XP для следующего уровня

#### TestLevelingSystemLeaderboard (2 теста)
- Получение топа пользователей
- Сортировка по XP

#### TestLevelingSystemMigration (2 теста)
- Миграция данных в БД
- Миграция без репозитория

#### TestLevelingSystemRoleRewards (3 теста)
- Выдача роли при достижении уровня
- Отсутствие выдачи если роль уже есть
- Обработка ошибок выдачи роли

#### TestLevelingSystemDatabase (4 теста)
- Создание пользователя в БД
- Обновление данных пользователя
- Получение данных из БД
- Обработка отсутствующего пользователя

### test_repositories.py (19 тестов)

Тесты репозиториев базы данных.

#### TestLevelsRepository (6 тестов)
- Создание пользователя
- Получение данных уровня и XP
- Обновление данных
- Получение таблицы лидеров
- Батчинг при миграции из JSON
- Проверка наличия колонки last_message_time

#### TestWarningsRepository (6 тестов)
- Добавление предупреждения
- Получение списка предупреждений
- Удаление предупреждения
- Очистка всех предупреждений пользователя
- Очистка устаревших предупреждений
- Батчинг при миграции из JSON

#### TestTicketsRepository (4 теста)
- Создание тикета
- Закрытие тикета
- Получение тикета по каналу
- Возврат None если тикет не найден

#### TestRepositoryErrorHandling (3 теста)
- Обработка ошибок БД в LevelsRepository
- Обработка ошибок БД в WarningsRepository
- Обработка ошибок БД в TicketsRepository

### test_discord_helpers.py (20 тестов)

Тесты вспомогательных функций для работы с Discord.

- Парсинг длительности времени (30m, 1h, 2d)
- Форматирование времени
- Создание embed сообщений
- Проверка прав модератора
- Валидация пользовательского ввода

### test_contracts.py (1 тест)

Проверка импорта контрактов приложения (Protocols).

## Паттерны тестирования

### Моки для Discord объектов

```python
# Мок для Member
member = MagicMock(spec=discord.Member)
member.bot = False
member.id = 123456
member.mention = "<@123456>"
member.top_role = MagicMock(position=5)

# Мок для Message
message = MagicMock(spec=discord.Message)
message.content = "test message"
message.author = member
message.guild = guild
message.delete = AsyncMock()

# Мок для Interaction
interaction = AsyncMock()
interaction.user = member
interaction.response = AsyncMock()
interaction.response.send_message = AsyncMock()
```

### Моки для Container

```python
@pytest.fixture
def mock_container(self):
    container = MagicMock(spec=Container)
    
    # Мокаем базу данных
    container.db = MagicMock()
    container.db.setup = AsyncMock()
    
    # Мокаем сервисы
    services = MagicMock()
    services.leveling = MagicMock()
    services.leveling.migrate_to_db = AsyncMock()  # AsyncMock для async методов!
    
    container.build_services = MagicMock(return_value=services)
    return container
```

### Тестирование async методов

```python
@pytest.mark.asyncio
async def test_async_method(self):
    # Используйте AsyncMock для async методов
    service.process_message = AsyncMock(return_value=(False, None))
    
    result = await service.process_message(message)
    
    service.process_message.assert_called_once_with(message)
    assert result == (False, None)
```

### Тестирование команд Discord

```python
@pytest.mark.asyncio
async def test_command(self):
    # Команды вызываются через .callback()
    await moderation.ban.callback(
        moderation,      # self
        interaction,     # interaction
        member,          # target
        "test reason"    # reason
    )
    
    member.ban.assert_called_once_with(reason="test reason")
```

### Проверка иерархии ролей

```python
# Настройка сравнения ролей
member.top_role.__ge__ = lambda self, other: self.position >= other.position
user.top_role.__ge__ = lambda self, other: self.position >= other.position

# Или через dataclass
@dataclass
class RoleStub:
    position: int
    
    def __ge__(self, other: "RoleStub") -> bool:
        return self.position >= other.position
```

## Важные замечания

### AsyncMock vs MagicMock

**Критически важно**: Используйте `AsyncMock` для всех async методов, иначе получите `TypeError: 'MagicMock' object can't be awaited`.

```python
# ❌ Неправильно
service.migrate_to_db = MagicMock()

# ✅ Правильно
service.migrate_to_db = AsyncMock()
```

### Read-only свойства Discord.py

Некоторые свойства Discord.py (например, `bot.user`) являются read-only и не могут быть замокированы. Вместо мокирования проверяйте наличие атрибута:

```python
# ❌ Не работает
bot.user = MagicMock()

# ✅ Работает
assert hasattr(bot, 'user')
```

### RuntimeError в фоновых задачах

При запуске тестов бота вы увидите `RuntimeError` от фоновых задач Discord - это нормально, так как бот не подключается к Discord API в тестах. Эти ошибки не влияют на результаты тестов.

### DeprecationWarning

Некоторые тесты показывают `DeprecationWarning` для `datetime.utcnow()`. Это можно исправить, заменив на `datetime.now(datetime.UTC)` в исходном коде.

## Покрытие кода

Текущее покрытие тестами: **100% core функционала**

- ✅ Инициализация бота и DI Container
- ✅ Все команды модерации (ban, kick, mute, clear)
- ✅ Автомодерация (запрещенные слова, спам, упоминания)
- ✅ Система уровней (XP, level up, leaderboard)
- ✅ Система предупреждений (добавление, удаление, наказания)
- ✅ Репозитории БД (levels, warnings, tickets)
- ✅ Миграция данных из JSON в SQLite
- ✅ Вспомогательные функции Discord

## Добавление новых тестов

### Шаблон для нового теста

```python
"""Тесты для новой функциональности."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord

from src.new_feature import NewFeature


class TestNewFeature:
    """Тесты новой функциональности."""

    @pytest.fixture
    def feature(self):
        """Фикстура для создания экземпляра."""
        bot = MagicMock()
        return NewFeature(bot)

    @pytest.mark.asyncio
    async def test_async_method(self, feature):
        """Тест асинхронного метода."""
        # Arrange
        message = MagicMock(spec=discord.Message)
        message.content = "test"
        
        # Act
        result = await feature.process(message)
        
        # Assert
        assert result is True

    def test_sync_method(self, feature):
        """Тест синхронного метода."""
        # Arrange
        value = 42
        
        # Act
        result = feature.calculate(value)
        
        # Assert
        assert result == 84
```

### Рекомендации

1. **Один тест - одна проверка**: Каждый тест должен проверять одну конкретную функциональность
2. **Arrange-Act-Assert**: Структурируйте тесты по паттерну AAA
3. **Понятные имена**: Имя теста должно четко описывать что проверяется
4. **Изоляция**: Тесты не должны зависеть друг от друга
5. **Моки для внешних зависимостей**: Мокируйте Discord API, БД, внешние сервисы
6. **Проверка граничных случаев**: Тестируйте не только happy path, но и ошибки

## Continuous Integration

Тесты автоматически запускаются при каждом коммите через GitHub Actions (если настроено).

Пример конфигурации `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - run: pip install -e .[dev]
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Отладка тестов

### Запуск с отладочной информацией

```bash
pytest tests/test_bot.py -v -s --log-cli-level=DEBUG
```

### Остановка на первой ошибке

```bash
pytest tests/ -x
```

### Запуск только упавших тестов

```bash
pytest --lf
```

### Профилирование тестов

```bash
pytest tests/ --durations=10
```

## Полезные ссылки

- [pytest документация](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [discord.py документация](https://discordpy.readthedocs.io/)
