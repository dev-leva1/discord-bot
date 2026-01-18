"""Совместимый модуль модерации (команды перенесены в presentation слой)."""

from __future__ import annotations

import logging

from presentation.moderation import ModerationCog

logger = logging.getLogger(__name__)
logger.debug("Imported compatibility moderation module; using ModerationCog alias")

__all__ = ["ModerationCog", "Moderation"]

# Backward compatibility alias
Moderation = ModerationCog
