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
from backend.app.core.logging import KeyValueFormatter


def test_key_value_formatter_renders_extra_fields() -> None:
    """Formatter keeps readable logs while exposing searchable context."""
    formatter = KeyValueFormatter("%(levelname)s [%(name)s] %(message)s")
    record = logging.LogRecord(
        name="backend.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="step_complete",
        args=(),
        exc_info=None,
    )
    record.task_id = "task-123"
    record.source_count = 0
    record.query = "quantum computing"
    record.should_continue = False

    formatted = formatter.format(record)

    assert formatted.startswith("INFO [backend.test] step_complete")
    assert "task_id=task-123" in formatted
    assert "source_count=0" in formatted
    assert 'query="quantum computing"' in formatted
    assert "should_continue=false" in formatted


def test_health_request_writes_http_log(caplog) -> None:
    """Backend requests are observable through application logs."""
    caplog.set_level(logging.INFO, logger="backend.http")

    with TestClient(app) as client:
        response = client.get(
            "/api/health",
            headers={"X-Request-ID": "req-health"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-health"

    request_logs = [
        record for record in caplog.records if record.name == "backend.http"
    ]
    assert len(request_logs) == 1
    record = request_logs[0]
    assert record.getMessage() == "http_request"
    assert record.request_id == "req-health"
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
