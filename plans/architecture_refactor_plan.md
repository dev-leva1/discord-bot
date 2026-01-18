# План комплексного рефакторинга архитектуры

Цель: перейти к слоистой структуре с четкими границами ответственности и единым слоем доступа к данным, без микросервисов.

## Текущее положение

- Точка входа и оркестрация в [`app/bot.py`](../app/bot.py:1) с совместимым re-export через [`bot.py`](../bot.py:1)
- Команды частично в когах ([`cogs/commands.py`](../cogs/commands.py:1), [`cogs/events.py`](../cogs/events.py:1)), частично в новых когах presentation ([`presentation/automod.py`](../presentation/automod.py:1), [`presentation/moderation.py`](../presentation/moderation.py:1))
- Данные: SQLite через [`database/db.py`](../database/db.py:1), JSON-конфиги централизуются в `infrastructure/config` (добавлен [`infrastructure/config/automod_store.py`](../infrastructure/config/automod_store.py:1), используются сторы в [`infrastructure/config/__init__.py`](../infrastructure/config/__init__.py:1))
- Инициализация мониторинга перенесена в инфраструктурный init и вызывается из контейнера ([`infrastructure/monitoring/__init__.py`](../infrastructure/monitoring/__init__.py:1), [`app/container.py`](../app/container.py:1)); сайд-эффекты импорта убраны из [`utils/monitoring.py`](../utils/monitoring.py:1)

## Целевая модель слоев

```mermaid
flowchart TD
  A[Presentation Cogs] --> B[Application Services]
  B --> C[Domain Logic]
  B --> D[Infrastructure Adapters]
  D --> E[Storage DB Redis Files]
  D --> F[Discord Gateway]
```

## Целевая структура пакетов

```
mee6/
├── app/                     # Точка входа, DI-контейнер
│   ├── bot.py
│   └── container.py
├── presentation/            # Коги и команды Discord
│   ├── commands.py
│   ├── events.py
│   ├── moderation.py
│   ├── automod.py
│   ├── tickets.py
│   └── voice.py
├── application/             # Сервисы и use-cases
│   ├── moderation_service.py
│   ├── automod_service.py
│   ├── leveling_service.py
│   ├── tickets_service.py
│   └── logging_service.py
├── domain/                  # Чистая логика и политики
│   ├── automod_policy.py
│   ├── leveling_rules.py
│   └── ticket_rules.py
├── infrastructure/          # Адаптеры БД/Redis/Файлы/Discord
│   ├── db/                  # SQLite + репозитории
│   ├── cache/               # Redis адаптер
│   ├── config/              # Единый конфиг и хранилище
│   └── monitoring/          # Инициализация метрик
└── utils/
```

## TODO план по этапам

### Этап 1. Базовая структура и DI
- [x] Создать пакеты `app`, `presentation`, `application`, `domain`, `infrastructure`.
- [x] Вынести запуск бота в [`app/bot.py`](../app/bot.py:1) и добавить контейнер зависимостей в [`app/container.py`](../app/container.py:1).
- [x] Перевести ленивые свойства `Bot` на явную инициализацию через контейнер.

### Этап 2. Команды только в когах
- [x] Перенести регистрацию команд из [`automod.py`](../automod.py:1) и [`moderation.py`](../moderation.py:1) в коги `presentation`.
- [x] Сервисы оставить чистыми: без `bot.tree` и без `discord.Interaction`.

### Этап 3. Единый слой данных
- [x] Ввести репозитории (LevelsRepository, TicketsRepository, WarningsRepository) в `infrastructure/db` ([`infrastructure/db/__init__.py`](../infrastructure/db/__init__.py:1)).
- [x] Перенести SQL-логику из [`leveling_system.py`](../leveling_system.py:1) в инфраструктурный слой (LevelsRepository).
- [x] Оставить JSON только как миграционный fallback, вынести в `infrastructure/config` ([`infrastructure/config/__init__.py`](../infrastructure/config/__init__.py:1)).

### Этап 4. Конфиг и мониторинг
- [x] Централизовать конфиги (automod, tickets, env) в `infrastructure/config`.
- [x] Отложить инициализацию Sentry/Prometheus до запуска приложения (убрать сайд-эффекты импорта).

### Этап 5. Контракты и критерии готовности
- [x] Определить интерфейсы сервисов и репозиториев в [`application/contracts.py`](../application/contracts.py:1).
- [x] Обновить импорты и тесты (добавлен smoke-тест в [`test_contracts.py`](../test_contracts.py:1)).
- [x] Критерии: бот стартует, команды регистрируются, уровни/тикеты/логирование работают, JSON fallback сохранен.

## Риски и меры

- Риск: разрыв старых импортов. Мера: временные адаптеры и re-export модули (сейчас: [`bot.py`](../bot.py:1), [`moderation.py`](../moderation.py:1)).
- Риск: расхождение данных JSON и SQLite. Мера: однонаправленная миграция при старте.

