"""Модуль для мониторинга и отслеживания метрик бота."""

import sentry_sdk
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import time
import os
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

SENTRY_DSN: Optional[str] = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        print("Sentry успешно инициализирован")
    except Exception as e:
        print(f"Ошибка инициализации Sentry: {e}")
else:
    print("Sentry отключен (DSN не настроен)")

COMMANDS_TOTAL = Counter(
    'bot_commands_total',
    'Total commands processed',
    ['command']
)
COMMANDS_FAILED = Counter(
    'bot_commands_failed',
    'Failed commands',
    ['command']
)
MESSAGES_PROCESSED = Counter(
    'bot_messages_processed',
    'Total messages processed'
)
ACTIVE_USERS = Gauge(
    'bot_active_users',
    'Number of active users'
)
COMMAND_LATENCY = Histogram(
    'bot_command_latency_seconds',
    'Command processing time in seconds'
)

T = TypeVar('T')

def start_metrics_server(port: int = 8000) -> None:
    """Запуск сервера метрик Prometheus.
    
    Args:
        port: Порт для сервера метрик
    """
    try:
        start_http_server(port)
        print(f"Метрики Prometheus доступны на порту {port}")
    except Exception as e:
        print(f"Ошибка запуска сервера метрик: {e}")

def monitor_command(func: Callable[..., Any]) -> Callable[..., Any]:
    """Декоратор для мониторинга выполнения команд.
    
    Args:
        func: Функция команды
        
    Returns:
        Callable[..., Any]: Обернутая функция
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        command_name = func.__name__
        start_time = time.time()
        
        try:
            COMMANDS_TOTAL.labels(command=command_name).inc()
            result = await func(*args, **kwargs)
            COMMAND_LATENCY.observe(time.time() - start_time)
            return result
        except Exception as e:
            COMMANDS_FAILED.labels(command=command_name).inc()
            if SENTRY_DSN:
                sentry_sdk.capture_exception(e)
            raise
    
    return cast(Callable[..., Any], wrapper)

def track_message() -> None:
    """Отслеживание обработанных сообщений."""
    MESSAGES_PROCESSED.inc()

def update_active_users(count: int) -> None:
    """Обновление количества активных пользователей.
    
    Args:
        count: Количество активных пользователей
    """
    ACTIVE_USERS.set(count)

def capture_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Захват и логирование ошибок.
    
    Args:
        error: Объект ошибки
        context: Дополнительный контекст
    """
    if SENTRY_DSN:
        sentry_sdk.capture_exception(error, extra=context)
    print(
        f"Ошибка: {error}",
        f"Контекст: {context}" if context else ""
    ) 