"""Configure logs, metrics, and traces for the local backend runtime."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Awaitable
from collections.abc import Callable

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import Counter
from prometheus_client import Histogram
from prometheus_client import generate_latest
from starlette.requests import Request
from starlette.responses import Response

SERVICE_NAME = "open-deepresearch-backend"
_STANDARD_LOG_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}

HTTP_REQUESTS = Counter(
    "open_deepresearch_http_requests_total",
    "Total backend HTTP requests.",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "open_deepresearch_http_request_duration_seconds",
    "Backend HTTP request latency in seconds.",
    ["method", "path", "status"],
)
http_logger = logging.getLogger("backend.http")


class JsonLogFormatter(logging.Formatter):
    """Format Python log records as single-line JSON for Loki ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        """Render one log record with service, level, message, and extras."""
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
        }
        payload.update(_trace_fields())
        payload.update(_extra_log_fields(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure structured stdout logging for local file and Loki collection."""
    if not _env_enabled("OBSERVABILITY_JSON_LOGS"):
        return

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


def instrument_app(app: FastAPI) -> None:
    """Attach observability middleware and scrape endpoints to one FastAPI app."""

    @app.middleware("http")
    async def record_http_metrics(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Record Prometheus metrics for every completed HTTP request."""
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started_at
        labels = _request_labels(request, response.status_code)
        HTTP_REQUESTS.labels(**labels).inc()
        HTTP_LATENCY.labels(**labels).observe(elapsed)
        http_logger.info(
            "http_request",
            extra={**labels, "duration_seconds": round(elapsed, 6)},
        )
        return response

    @app.get("/metrics")
    async def metrics() -> Response:
        """Expose Prometheus text metrics for local scraping."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def configure_tracing(app: FastAPI) -> None:
    """Enable OTLP tracing for FastAPI when local tracing is explicitly enabled."""
    if not _env_enabled("OBSERVABILITY_TRACING_ENABLED"):
        return

    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=_otlp_url())))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)


def _request_labels(request: Request, status_code: int) -> dict[str, str]:
    """Build low-cardinality labels for one HTTP request."""
    return {
        "method": request.method,
        "path": request.url.path,
        "status": str(status_code),
    }


def _extra_log_fields(record: logging.LogRecord) -> dict[str, object]:
    """Extract user-provided logging extras from one log record."""
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _STANDARD_LOG_ATTRS and not key.startswith("_")
    }


def _trace_fields() -> dict[str, str]:
    """Read the current OpenTelemetry trace identifiers when present."""
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return {}
    return {
        "trace_id": f"{span_context.trace_id:032x}",
        "span_id": f"{span_context.span_id:016x}",
    }


def _env_enabled(name: str) -> bool:
    """Read a boolean environment flag using common truthy strings."""
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


def _otlp_url() -> str:
    """Return the OTLP HTTP traces endpoint for the local collector."""
    return os.getenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "http://localhost:4318/v1/traces",
    )
