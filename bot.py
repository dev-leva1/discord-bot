"""Совместимый входной модуль (re-export)."""

from app.bot import Bot, main


__all__ = ["Bot", "main"]


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
