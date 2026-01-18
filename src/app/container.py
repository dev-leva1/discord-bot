"""DI-контейнер приложения."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass

import leveling_system
from automod import AutoMod
from database.db import Database
from image_generator import ImageGenerator
from logging_system import LoggingSystem
from moderation import Moderation
from roles import RoleRewards
from temp_voice import TempVoice
from tickets import TicketSystem
from warning_system import WarningSystem
from welcome import Welcome

from infrastructure.config import (
    AutomodConfigStore,
    LevelsStore,
    TicketsConfigStore,
    WarningsConfigStore,
    WarningsStore,
)
from infrastructure.monitoring import init_monitoring
from infrastructure.db import LevelsRepository, TicketsRepository, WarningsRepository

from application.contracts import (
    AutomodServiceContract,
    LevelingServiceContract,
    LoggingServiceContract,
    TicketsServiceContract,
    WarningsServiceContract,
)


@dataclass(frozen=True)
class BotServices:
    """Контейнер зависимостей, требующих экземпляр бота."""

    moderation: Moderation
    welcome: Welcome
    role_rewards: RoleRewards
    leveling: LevelingServiceContract
    automod: AutomodServiceContract
    logging: LoggingServiceContract
    tickets: TicketsServiceContract
    temp_voice: TempVoice
    warnings: WarningsServiceContract


class Container:
    """Простой DI-контейнер с фабриками."""

    def __init__(self) -> None:
        init_monitoring()
        os.environ.setdefault("DB_PATH", str(Path("data") / "bot.db"))
        self.use_metrics = os.getenv("USE_METRICS", "False").lower() == "true"
        self.metrics_port = int(os.getenv("METRICS_PORT", "8000"))
        self.db = Database()
        self.image_generator = ImageGenerator()
        self.levels_store = LevelsStore()
        self.tickets_store = TicketsConfigStore()
        self.automod_store = AutomodConfigStore()
        self.warnings_store = WarningsStore()
        self.warnings_config_store = WarningsConfigStore()
        self.initial_extensions = [
            "cogs.events",
            "cogs.commands",
            "presentation.automod",
            "presentation.moderation",
        ]

    def build_cogs(self) -> list:
        """Создать коги, требующие независимой инициализации."""

        return [
            TicketSystem,
            WarningSystem,
        ]

    def build_services(self, bot) -> BotServices:
        """Создать сервисы, которым нужен экземпляр бота."""

        levels_repository = LevelsRepository(self.db)
        tickets_repository = TicketsRepository(self.db)
        warnings_repository = WarningsRepository(self.db)

        return BotServices(
            moderation=Moderation(bot),
            welcome=Welcome(bot),
            role_rewards=RoleRewards(bot),
            leveling=leveling_system.init_leveling(
                bot,
                levels_repository,
                self.levels_store,
            ),
            automod=AutoMod(bot, self.automod_store),
            logging=LoggingSystem(bot),
            tickets=TicketSystem(
                bot,
                tickets_repository,
                self.tickets_store,
            ),
            temp_voice=TempVoice(bot),
            warnings=WarningSystem(
                bot,
                warnings_repository,
                self.warnings_store,
                self.warnings_config_store,
            ),
        )
