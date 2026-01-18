# Установка и запуск

## Требования

- Python 3.10+
- uv

## Установка

```
uv pip install -e .[dev]
```

## Конфигурация

Создайте файл `data/.env`:

```
DISCORD_TOKEN=your_discord_token_here
DB_POOL_SIZE=5
REDIS_URL=redis://localhost:6379/0
USE_METRICS=true
METRICS_PORT=8000
SENTRY_DSN=your_sentry_dsn_here
ENVIRONMENT=development
VERSION=1.0.0
```

## Запуск

```
python bot.py
```
