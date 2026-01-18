# Конфигурация

Конфигурационные файлы и данные находятся в `data/`.

## Переменные окружения

Файл: `data/.env`

- `DISCORD_TOKEN` — токен бота
- `DB_POOL_SIZE` — размер пула SQLite
- `REDIS_URL` — URL Redis (опционально)
- `USE_METRICS` — включить метрики Prometheus
- `METRICS_PORT` — порт метрик
- `SENTRY_DSN` — DSN Sentry

## JSON конфиги

Сюда входят:

- `data/levels.json`
- `data/automod_config.json`
- `data/tickets_config.json`
- `data/warnings.json`
- `data/warnings_config.json`
- `data/voice_config.json`
- `data/role_rewards.json`
- `data/logging_config.json`
- `data/welcome_config.json`
