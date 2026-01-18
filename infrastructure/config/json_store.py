"""Утилита для хранения JSON конфигураций."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class JsonStore(Generic[T]):
    """Хранилище JSON с ленивым созданием по умолчанию."""

    def __init__(self, path: str, default_factory: Callable[[], T]) -> None:
        self.path = Path(path)
        self.default_factory = default_factory

    def load(self) -> T:
        """Загрузить данные или создать дефолтный файл."""

        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as file:
                return json.load(file)

        data = self.default_factory()
        self.save(data)
        return data

    def save(self, data: T) -> None:
        """Сохранить данные в JSON файл."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
