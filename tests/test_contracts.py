"""Smoke тесты на доступность контрактов application слоя."""

from application import (
    AutomodServiceContract,
    LevelingServiceContract,
    LoggingServiceContract,
    LevelsRepositoryContract,
    TicketsRepositoryContract,
    TicketsServiceContract,
    WarningsRepositoryContract,
    WarningsServiceContract,
)


def test_application_contracts_importable() -> None:
    assert AutomodServiceContract is not None
    assert LevelingServiceContract is not None
    assert LoggingServiceContract is not None
    assert LevelsRepositoryContract is not None
    assert TicketsRepositoryContract is not None
    assert TicketsServiceContract is not None
    assert WarningsRepositoryContract is not None
    assert WarningsServiceContract is not None
