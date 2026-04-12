from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{(Path('backend/data/test_app.db').resolve())}",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from backend.app.main import app
from backend.app.db.base import init_db
from backend.app.core import security
from backend.app.services.research_repository import ResearchRepository
from backend.app.models.research_task import ResearchTask
from backend.app.models.research_task import ResearchTaskStatus


TEST_DB_PATH = Path("backend/data/test_app.db").resolve()


@pytest.fixture(autouse=True)
def reset_users_table() -> None:
    asyncio.run(init_db())
    with sqlite3.connect(TEST_DB_PATH) as conn:
        conn.execute("DELETE FROM users")
        conn.commit()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_register_returns_token(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert isinstance(payload["access_token"], str)
    assert payload["access_token"]


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    first = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    second = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["detail"] == "该邮箱已被注册"


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "12345"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "密码长度至少 6 位"


def test_login_returns_token_for_registered_user(client: TestClient) -> None:
    register = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "secret123"},
    )

    assert register.status_code == 201
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert isinstance(payload["access_token"], str)
    assert payload["access_token"]


def test_login_rejects_invalid_password(client: TestClient) -> None:
    register = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "wrongpass"},
    )

    assert register.status_code == 201
    assert response.status_code == 401
    assert response.json()["detail"] == "邮箱或密码错误"


def test_get_me_returns_current_user(client: TestClient) -> None:
    register = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    token = register.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "user@example.com"
    assert isinstance(payload["id"], int)


def test_get_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_claim_history_assigns_anonymous_tasks_to_current_user(client: TestClient) -> None:
    register = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    token = register.json()["access_token"]
    user = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    repository = ResearchRepository()
    repository.save_task(
        ResearchTask(
            id="anon-task-1",
            user_id=None,
            query="public 1",
            status=ResearchTaskStatus.COMPLETED,
        )
    )
    repository.save_task(
        ResearchTask(
            id="anon-task-2",
            user_id=None,
            query="public 2",
            status=ResearchTaskStatus.COMPLETED,
        )
    )

    response = client.post(
        "/api/auth/claim-history",
        json={"task_ids": ["anon-task-1", "anon-task-2"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["claimed"] == 2
    assert repository.load_task("anon-task-1", user_id=user["id"]) is not None
    assert repository.load_task("anon-task-2", user_id=user["id"]) is not None


def test_claim_history_only_claims_anonymous_tasks(client: TestClient) -> None:
    first = client.post(
        "/api/auth/register",
        json={"email": "first@example.com", "password": "secret123"},
    )
    second = client.post(
        "/api/auth/register",
        json={"email": "second@example.com", "password": "secret123"},
    )

    first_token = first.json()["access_token"]
    second_token = second.json()["access_token"]
    second_user = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {second_token}"},
    ).json()

    repository = ResearchRepository()
    repository.save_task(
        ResearchTask(
            id="already-owned",
            user_id=second_user["id"],
            query="private",
            status=ResearchTaskStatus.COMPLETED,
        )
    )

    response = client.post(
        "/api/auth/claim-history",
        json={"task_ids": ["already-owned"]},
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert response.status_code == 200
    assert response.json()["claimed"] == 0
    assert repository.load_task("already-owned", user_id=second_user["id"]) is not None


def test_create_access_token_requires_secret_key(monkeypatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        security.create_access_token(1)
