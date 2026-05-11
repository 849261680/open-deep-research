"""Expose local observability query endpoints for automation agents."""

import os

import requests
from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field

router = APIRouter(prefix="/observability", tags=["observability"])


class ObservabilityQueryRequest(BaseModel):
    """Describe one PromQL or LogQL instant query submitted by an agent."""

    query: str = Field(min_length=1, max_length=2000)


class ObservabilityQueryResponse(BaseModel):
    """Return upstream observability data with source metadata."""

    source: str
    query: str
    result: dict[str, object]


@router.post("/promql", response_model=ObservabilityQueryResponse)
def query_prometheus(
    request: ObservabilityQueryRequest,
) -> ObservabilityQueryResponse:
    """Proxy a PromQL instant query to the configured local Prometheus."""
    result = _query_upstream(
        base_url=_prometheus_url(),
        path="/api/v1/query",
        query=request.query,
    )
    return ObservabilityQueryResponse(
        source="prometheus",
        query=request.query,
        result=result,
    )


@router.post("/logql", response_model=ObservabilityQueryResponse)
def query_loki(request: ObservabilityQueryRequest) -> ObservabilityQueryResponse:
    """Proxy a LogQL range query to the configured local Loki."""
    result = _query_upstream(
        base_url=_loki_url(),
        path="/loki/api/v1/query_range",
        query=request.query,
        extra_params={"limit": "100"},
    )
    return ObservabilityQueryResponse(source="loki", query=request.query, result=result)


def _prometheus_url() -> str:
    """Return the Prometheus base URL used by local observability queries."""
    return os.getenv("OBSERVABILITY_PROMETHEUS_URL", "http://localhost:9091").rstrip("/")


def _loki_url() -> str:
    """Return the Loki base URL used by local observability queries."""
    return os.getenv("OBSERVABILITY_LOKI_URL", "http://localhost:3100").rstrip("/")


def _query_upstream(
    base_url: str,
    path: str,
    query: str,
    extra_params: dict[str, str] | None = None,
) -> dict[str, object]:
    """Execute a query against one observability backend."""
    params = {"query": query}
    if extra_params:
        params.update(extra_params)

    try:
        response = requests.get(
            f"{base_url}{path}",
            params=params,
            timeout=10.0,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail="观测性后端查询失败",
        ) from exc

    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="观测性后端返回格式无效")
    return payload
