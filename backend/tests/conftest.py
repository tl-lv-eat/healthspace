"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.app.settings import clear_settings_cache

# Pin user passwords for auth tests so local config.yaml cannot break isolation.
_TEST_APP_CONFIG = """\
app:
  users:
    - id: dragon
      password: dragon-pass
      display_name: "🐉"
      default_water_ml: 2000
      role: member
    - id: leaf
      password: leaf-pass
      display_name: "🍃"
      default_water_ml: 2000
      role: member
"""


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_file = tmp_path / "test.db"
    config_file = tmp_path / "test-config.yaml"
    config_file.write_text(_TEST_APP_CONFIG, encoding="utf-8")

    upload_dir = tmp_path / "uploads" / "meals"
    prior_db_url = os.environ.get("DATABASE_URL")
    prior_config = os.environ.get("JIANFEI_CONFIG")
    prior_upload = os.environ.get("UPLOAD_DIR")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    os.environ["JIANFEI_CONFIG"] = str(config_file)
    os.environ["UPLOAD_DIR"] = str(upload_dir)
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

        if prior_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prior_db_url
        if prior_config is None:
            os.environ.pop("JIANFEI_CONFIG", None)
        else:
            os.environ["JIANFEI_CONFIG"] = prior_config
        if prior_upload is None:
            os.environ.pop("UPLOAD_DIR", None)
        else:
            os.environ["UPLOAD_DIR"] = prior_upload
        clear_settings_cache()


@pytest.fixture
def db_session(client) -> Generator:
    from backend.app.db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_header(client) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"user_id": "dragon", "password": "dragon-pass"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def leaf_auth_header(client) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"user_id": "leaf", "password": "leaf-pass"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
