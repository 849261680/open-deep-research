from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{(Path('backend/data/test_app.db').resolve())}",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from backend.app.main import app


class FakeQueryResponse:
    """Provide the small requests.Response surface used by query endpoints."""

    status_code = 200

    def json(self) -> dict[str, object]:
        """Return a Prometheus-compatible query payload."""
        return {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        }

    def raise_for_status(self) -> None:
        """Represent a successful upstream response."""
        return None


def test_promql_query_proxies_to_prometheus(monkeypatch) -> None:
    """Agents can submit PromQL through the backend to local Prometheus."""
    captured: dict[str, object] = {}

    def fake_get(url: str, params: dict[str, str], timeout: float) -> FakeQueryResponse:
        """Capture the upstream request made by the observability API."""
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return FakeQueryResponse()

    monkeypatch.setenv("OBSERVABILITY_PROMETHEUS_URL", "http://prometheus.test")
    monkeypatch.setattr("requests.get", fake_get)

    with TestClient(app) as client:
        response = client.post(
            "/api/observability/promql",
            json={"query": "up{job=\"open-deepresearch-backend\"}"},
        )

    assert response.status_code == 200
    assert response.json()["source"] == "prometheus"
    assert response.json()["query"] == 'up{job="open-deepresearch-backend"}'
    assert captured == {
        "url": "http://prometheus.test/api/v1/query",
        "params": {"query": 'up{job="open-deepresearch-backend"}'},
        "timeout": 10.0,
    }


def test_logql_query_proxies_to_loki(monkeypatch) -> None:
    """Agents can submit LogQL through the backend to local Loki."""
    captured: dict[str, object] = {}

    def fake_get(url: str, params: dict[str, str], timeout: float) -> FakeQueryResponse:
        """Capture the upstream Loki request made by the observability API."""
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return FakeQueryResponse()

    monkeypatch.setenv("OBSERVABILITY_LOKI_URL", "http://loki.test")
    monkeypatch.setattr("requests.get", fake_get)

    with TestClient(app) as client:
        response = client.post(
            "/api/observability/logql",
            json={"query": '{service="open-deepresearch-backend"}'},
        )

    assert response.status_code == 200
    assert response.json()["source"] == "loki"
    assert response.json()["query"] == '{service="open-deepresearch-backend"}'
    assert captured == {
        "url": "http://loki.test/loki/api/v1/query_range",
        "params": {"query": '{service="open-deepresearch-backend"}', "limit": "100"},
        "timeout": 10.0,
    }


def test_metrics_endpoint_exports_http_request_counter() -> None:
    """Prometheus can scrape backend HTTP request metrics."""
    with TestClient(app) as client:
        client.get("/api/health")
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "open_deepresearch_http_requests_total" in body
    assert 'path="/api/health"' in body
