"""
Test fixtures shared across all test modules.

Provides:
1. sqlite_path - Temporary database path for each test
2. storage - SQLiteStorage instance (auto-cleanup after test)
3. engine - Engine instance with test storage

All fixtures use pytest's tmp_path for isolation.
Storage fixture automatically closes connection after each test.

Usage in tests:
    def test_something(engine, storage):
        # engine and storage are ready to use
        # no manual cleanup needed
"""

from __future__ import annotations

import pytest

from src.engine import Engine
from src.storage import SQLiteStorage


@pytest.fixture()
def sqlite_path(tmp_path) -> str:
    return str(tmp_path / "test.sqlite")


@pytest.fixture()
def storage(sqlite_path: str) -> SQLiteStorage:
    s = SQLiteStorage(sqlite_path)
    yield s
    s.close()


@pytest.fixture()
def engine(storage: SQLiteStorage) -> Engine:
    return Engine(storage)
