"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.app.settings import clear_settings_cache


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    clear_settings_cache()

    from backend.app.db import init_db, rebind_engine

    rebind_engine()
    init_db()

    from backend.app.main import app

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()

    clear_settings_cache()
