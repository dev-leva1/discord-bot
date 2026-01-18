# Contributing

Спасибо за интерес к проекту. Ниже — минимальные правила, чтобы изменения легко принимались.

## Основной процесс

1. Создайте issue или обсудите идею в Discussions.
2. Форкните репозиторий, создайте ветку.
3. Внесите изменения и откройте PR.

## Conventional Commits

Используйте формат:

```
type(scope): summary
```

Примеры:

- `feat(commands): add ticket close reason`
- `fix(logging): handle missing config file`
- `docs(readme): update setup steps`

## Структура проекта

Код находится в `src/`, документация — в `docs/`, данные и конфиги — в `data/`.

## Запуск локально

Установка зависимостей:

```
uv pip install -e .[dev]
```

Запуск:

```
python bot.py
```
