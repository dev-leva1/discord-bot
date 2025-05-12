"""Модуль для мониторинга и отслеживания метрик бота."""

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from prometheus_client import start_http_server, Counter, Gauge, Histogram, Summary
import time
import os
import platform
import sys
import logging
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast
import socket

# Настройка логгера
logger = logging.getLogger(__name__)

# Конфигурация Sentry
SENTRY_DSN: Optional[str] = os.getenv('SENTRY_DSN')
ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'production')

if SENTRY_DSN:
    try:
        # Настраиваем интеграцию с логгером
        logging_integration = LoggingIntegration(
            level=logging.INFO,        # Захват логов уровня INFO и выше
            event_level=logging.ERROR  # Отправка в Sentry только ошибок уровня ERROR и выше
        )
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=ENVIRONMENT,
            traces_sample_rate=1.0,
            profiles_sample_rate=0.5,
            release=os.getenv('VERSION', '1.0.0'),
            integrations=[logging_integration],
            # Добавляем информацию о системе
            before_send=lambda event, hint: {
                **event,
                'contexts': {
                    **event.get('contexts', {}),
                    'os': {'name': platform.system(), 'version': platform.version()},
                    'runtime': {'name': 'python', 'version': platform.python_version()},
                }
            },
        )
        logger.info("Sentry успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации Sentry: {e}")
else:
    logger.info("Sentry отключен (DSN не настроен)")

# Prometheus метрики
COMMANDS_TOTAL = Counter(
    'bot_commands_total',
    'Total commands processed',
    ['command', 'guild_id', 'success']
)
COMMANDS_LATENCY = Histogram(
    'bot_command_latency_seconds',
    'Command processing time in seconds',
    ['command'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
)
MESSAGES_PROCESSED = Counter(
    'bot_messages_processed',
    'Total messages processed',
    ['guild_id']
)
MESSAGES_LATENCY = Histogram(
    'bot_message_latency_seconds',
    'Message processing time in seconds',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, float('inf'))
)
ACTIVE_USERS = Gauge(
    'bot_active_users',
    'Number of active users',
    ['guild_id']
)
GUILDS_COUNT = Gauge(
    'bot_guilds_count',
    'Number of guilds the bot is connected to'
)
ERRORS_COUNT = Counter(
    'bot_errors_total',
    'Total errors encountered',
    ['type', 'module']
)
AUTOMOD_ACTIONS = Counter(
    'bot_automod_actions_total',
    'Total automod actions taken',
    ['action_type', 'guild_id']
)
API_REQUESTS = Counter(
    'bot_api_requests_total',
    'Total API requests made to Discord',
    ['endpoint', 'method', 'status_code']
)
API_LATENCY = Histogram(
    'bot_api_latency_seconds',
    'API request latency in seconds',
    ['endpoint'],
    buckets=(0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0, float('inf'))
)
DB_OPERATIONS = Counter(
    'bot_db_operations_total',
    'Total database operations performed',
    ['operation', 'table']
)
DB_LATENCY = Histogram(
    'bot_db_latency_seconds',
    'Database operation latency in seconds',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, float('inf'))
)
MEMORY_USAGE = Gauge(
    'bot_memory_usage_bytes',
    'Memory usage in bytes'
)
CPU_USAGE = Gauge(
    'bot_cpu_usage_percent',
    'CPU usage percentage'
)
VOICE_CONNECTIONS = Gauge(
    'bot_voice_connections',
    'Number of active voice connections'
)

T = TypeVar('T')

def start_metrics_server(port: int = 8000) -> None:
    """Запуск сервера метрик Prometheus.
    
    Args:
        port: Порт для сервера метрик
    """
    try:
        # Проверяем, что порт свободен
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            logger.warning(f"Порт {port} уже используется, пробуем порт {port+1}")
            port += 1
        sock.close()
        
        start_http_server(port)
        logger.info(f"Метрики Prometheus доступны на порту {port}")
    except Exception as e:
        logger.error(f"Ошибка запуска сервера метрик: {e}")

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
        
        # Определяем контекст команды
        ctx = args[1] if len(args) > 1 else None
        guild_id = str(ctx.guild.id) if ctx and hasattr(ctx, 'guild') and ctx.guild else 'dm'
        
        # Установка контекста для Sentry
        with sentry_sdk.configure_scope() as scope:
            if ctx:
                scope.set_tag('command', command_name)
                if hasattr(ctx, 'guild') and ctx.guild:
                    scope.set_tag('guild_id', guild_id)
                if hasattr(ctx, 'channel') and ctx.channel:
                    scope.set_tag('channel_id', ctx.channel.id)
                if hasattr(ctx, 'author') and ctx.author:
                    scope.set_user({'id': ctx.author.id, 'username': str(ctx.author)})
        
        try:
            # Выполнение команды
            result = await func(*args, **kwargs)
            
            # Фиксация метрик
            execution_time = time.time() - start_time
            COMMANDS_LATENCY.labels(command=command_name).observe(execution_time)
            COMMANDS_TOTAL.labels(command=command_name, guild_id=guild_id, success='true').inc()
            
            return result
        except Exception as e:
            # Фиксация ошибки
            COMMANDS_TOTAL.labels(command=command_name, guild_id=guild_id, success='false').inc()
            ERRORS_COUNT.labels(type=type(e).__name__, module=func.__module__).inc()
            
            # Отправка ошибки в Sentry
            if SENTRY_DSN:
                extra_data = {
                    'command': command_name,
                    'guild_id': guild_id,
                    'execution_time': time.time() - start_time
                }
                if ctx:
                    if hasattr(ctx, 'message') and ctx.message:
                        extra_data['message_content'] = ctx.message.content
                    if hasattr(ctx, 'channel') and ctx.channel:
                        extra_data['channel_name'] = ctx.channel.name
                
                sentry_sdk.capture_exception(
                    error=e,
                    extra=extra_data
                )
            
            # Логирование ошибки
            logger.error(
                f"Ошибка при выполнении команды {command_name}: {str(e)}",
                exc_info=True
            )
            
            raise
    
    return cast(Callable[..., Any], wrapper)

def track_message(guild_id: Optional[str] = None) -> None:
    """Отслеживание обработанных сообщений.
    
    Args:
        guild_id: ID гильдии, в которой было отправлено сообщение
    """
    MESSAGES_PROCESSED.labels(guild_id=guild_id or 'unknown').inc()

def measure_message_processing_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """Декоратор для измерения времени обработки сообщения.
    
    Args:
        func: Функция обработки сообщения
        
    Returns:
        Callable[..., Any]: Обернутая функция
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            MESSAGES_LATENCY.observe(time.time() - start_time)
    
    return cast(Callable[..., Any], wrapper)

def track_db_operation(operation: str, table: str) -> None:
    """Отслеживание операций с базой данных.
    
    Args:
        operation: Тип операции (select, insert, update, delete)
        table: Название таблицы
    """
    DB_OPERATIONS.labels(operation=operation, table=table).inc()

def measure_db_operation_time(operation: str) -> Callable:
    """Декоратор для измерения времени операции с базой данных.
    
    Args:
        operation: Тип операции
        
    Returns:
        Callable: Декоратор
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                DB_LATENCY.labels(operation=operation).observe(time.time() - start_time)
        
        return cast(Callable[..., Any], wrapper)
    
    return decorator

def update_active_users(count: int, guild_id: Optional[str] = None) -> None:
    """Обновление количества активных пользователей.
    
    Args:
        count: Количество активных пользователей
        guild_id: ID гильдии (если указано)
    """
    ACTIVE_USERS.labels(guild_id=guild_id or 'all').set(count)

def update_guilds_count(count: int) -> None:
    """Обновление количества серверов.
    
    Args:
        count: Количество серверов
    """
    GUILDS_COUNT.set(count)

def track_automod_action(action: str, guild_id: str) -> None:
    """Отслеживание действий автомодерации.
    
    Args:
        action: Тип действия
        guild_id: ID гильдии
    """
    AUTOMOD_ACTIONS.labels(action_type=action, guild_id=guild_id).inc()

def track_api_request(endpoint: str, method: str, status_code: int) -> None:
    """Отслеживание запросов к API Discord.
    
    Args:
        endpoint: Конечная точка API
        method: HTTP метод
        status_code: Код ответа
    """
    API_REQUESTS.labels(endpoint=endpoint, method=method, status_code=status_code).inc()

def measure_api_request_time(endpoint: str) -> Callable:
    """Декоратор для измерения времени запроса к API Discord.
    
    Args:
        endpoint: Конечная точка API
        
    Returns:
        Callable: Декоратор
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                API_LATENCY.labels(endpoint=endpoint).observe(time.time() - start_time)
        
        return cast(Callable[..., Any], wrapper)
    
    return decorator

def update_memory_usage(usage: int) -> None:
    """Обновление использования памяти.
    
    Args:
        usage: Использование памяти в байтах
    """
    MEMORY_USAGE.set(usage)

def update_cpu_usage(usage: float) -> None:
    """Обновление использования CPU.
    
    Args:
        usage: Использование CPU в процентах
    """
    CPU_USAGE.set(usage)

def update_voice_connections(count: int) -> None:
    """Обновление количества голосовых подключений.
    
    Args:
        count: Количество голосовых подключений
    """
    VOICE_CONNECTIONS.set(count)

def capture_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Захват и логирование ошибок.
    
    Args:
        error: Объект ошибки
        context: Дополнительный контекст
    """
    try:
        # Обновление метрики ошибок
        error_type = type(error).__name__
        error_module = error.__class__.__module__
        ERRORS_COUNT.labels(type=error_type, module=error_module).inc()
        
        # Получение трассировки
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = ''.join(tb)
        
        # Логирование ошибки
        log_message = f"Ошибка: {error_type}: {str(error)}"
        if context:
            log_message += f"\nКонтекст: {context}"
        logger.error(f"{log_message}\nТрассировка:\n{tb_str}")
        
        # Отправка в Sentry если настроен
        if SENTRY_DSN:
            with sentry_sdk.configure_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)
                
                # Захват исключения с трассировкой
                sentry_sdk.capture_exception(error)
            
    except Exception as e:
        # Если что-то пошло не так при обработке ошибки
        logger.error(f"Ошибка при обработке исключения: {e}")
        print(
            f"Критическая ошибка при логировании исключения: {e}",
            f"Исходная ошибка: {error}"
        ) 