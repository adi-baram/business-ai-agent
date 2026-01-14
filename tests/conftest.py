"""
Pytest fixtures for business analytics tests.

Provides shared fixtures for:
- DataManager instance
- Date context
- Sample data
"""
from __future__ import annotations

import pytest

from src.data_loader import DataManager, get_data_manager


@pytest.fixture(scope="session", autouse=True)
def reset_data_manager():
    """Reset DataManager before test session."""
    DataManager.reset()
    yield
    DataManager.reset()


@pytest.fixture(scope="session")
def data_manager() -> DataManager:
    """Provide DataManager instance for tests."""
    return get_data_manager()


@pytest.fixture(scope="session")
def date_context(data_manager: DataManager) -> dict[str, str]:
    """Provide date context from data."""
    return data_manager.get_date_context()


@pytest.fixture(scope="session")
def transactions(data_manager: DataManager):
    """Provide transactions DataFrame for tests."""
    return data_manager.transactions


@pytest.fixture(scope="session")
def customers(data_manager: DataManager):
    """Provide customers DataFrame for tests."""
    return data_manager.customers
