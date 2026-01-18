"""Совместимый входной модуль (re-export)."""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from app.bot import Bot, main


__all__ = ["Bot", "main"]


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
