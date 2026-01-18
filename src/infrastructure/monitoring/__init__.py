"""Инфраструктурный слой мониторинга."""

from __future__ import annotations

import os
import logging

from utils.monitoring import init_sentry

logger = logging.getLogger(__name__)


def init_monitoring() -> None:
    """Явная инициализация мониторинга приложения."""

    dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "production")
    init_sentry(dsn, environment)
    logger.info("Мониторинг инициализирован")
