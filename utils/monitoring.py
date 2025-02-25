import sentry_sdk
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import time
import os
from functools import wraps

# Инициализация Sentry
sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

# Метрики Prometheus
COMMANDS_TOTAL = Counter('bot_commands_total', 'Total commands processed', ['command'])
COMMANDS_FAILED = Counter('bot_commands_failed', 'Failed commands', ['command'])
MESSAGES_PROCESSED = Counter('bot_messages_processed', 'Total messages processed')
ACTIVE_USERS = Gauge('bot_active_users', 'Number of active users')
COMMAND_LATENCY = Histogram('bot_command_latency_seconds', 'Command processing time in seconds')

def start_metrics_server(port=8000):
    start_http_server(port)

def monitor_command(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        command_name = func.__name__
        start_time = time.time()
        
        try:
            COMMANDS_TOTAL.labels(command=command_name).inc()
            result = await func(*args, **kwargs)
            COMMAND_LATENCY.observe(time.time() - start_time)
            return result
        except Exception as e:
            COMMANDS_FAILED.labels(command=command_name).inc()
            sentry_sdk.capture_exception(e)
            raise
    
    return wrapper

def track_message():
    MESSAGES_PROCESSED.inc()

def update_active_users(count):
    ACTIVE_USERS.set(count)

def capture_error(error, context=None):
    sentry_sdk.capture_exception(error, extra=context) 