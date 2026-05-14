from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{(Path('backend/data/test_app.db').resolve())}",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from backend.app.main import app


def test_health_request_writes_http_log(caplog) -> None:
    """Backend requests are observable through application logs."""
    caplog.set_level(logging.INFO, logger="backend.http")

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200

    request_logs = [
        record for record in caplog.records if record.name == "backend.http"
    ]
    assert len(request_logs) == 1
    record = request_logs[0]
    assert record.getMessage() == "http_request"
    assert record.method == "GET"
    assert record.path == "/api/health"
    assert record.status == "200"
    assert isinstance(record.duration_seconds, float)


def test_metrics_endpoint_is_removed() -> None:
    """The Prometheus scrape endpoint is no longer exposed."""
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 404


def test_observability_query_api_is_removed() -> None:
    """The old PromQL and LogQL proxy API is no longer exposed."""
    with TestClient(app) as client:
        response = client.post(
            "/api/observability/promql",
            json={"query": "up"},
        )

    assert response.status_code == 404
