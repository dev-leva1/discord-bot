"""DI-контейнер приложения."""

from __future__ import annotations

import os
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


@dataclass(frozen=True)
class BotServices:
    """Контейнер зависимостей, требующих экземпляр бота."""

    moderation: Moderation
    welcome: Welcome
    role_rewards: RoleRewards
    leveling: leveling_system.LevelingSystem
    automod: AutoMod
    logging: LoggingSystem
    tickets: TicketSystem
    temp_voice: TempVoice
    warnings: WarningSystem


class Container:
    """Простой DI-контейнер с фабриками."""

    def __init__(self) -> None:
        self.use_metrics = os.getenv("USE_METRICS", "False").lower() == "true"
        self.metrics_port = int(os.getenv("METRICS_PORT", "8000"))
        self.db = Database()
        self.image_generator = ImageGenerator()
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

        return BotServices(
            moderation=Moderation(bot),
            welcome=Welcome(bot),
            role_rewards=RoleRewards(bot),
            leveling=leveling_system.init_leveling(bot),
            automod=AutoMod(bot),
            logging=LoggingSystem(bot),
            tickets=TicketSystem(bot),
            temp_voice=TempVoice(bot),
            warnings=WarningSystem(bot),
        )

