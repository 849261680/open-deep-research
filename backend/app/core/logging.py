"""Configure application logging for the backend runtime."""

from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from contextvars import Token
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

http_logger = logging.getLogger("backend.http")
REQUEST_ID_HEADER = "X-Request-ID"
_current_request_id: ContextVar[str | None] = ContextVar(
    "current_request_id",
    default=None,
)
RESERVED_LOG_RECORD_KEYS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}


class KeyValueFormatter(logging.Formatter):
    """Append LogRecord extra fields as readable key=value pairs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the normal message and append non-standard record fields."""
        message = super().format(record)
        extras = self._extra_fields(record)
        if not extras:
            return message
        key_values = " ".join(
            f"{key}={self._format_value(value)}" for key, value in extras.items()
        )
        return f"{message} {key_values}"

    def _extra_fields(self, record: logging.LogRecord) -> dict[str, object]:
        """Return sorted custom fields added through logging extra."""
        fields = {}
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in RESERVED_LOG_RECORD_KEYS:
                continue
            fields[key] = value
        return dict(sorted(fields.items()))

    def _format_value(self, value: object) -> str:
        """Render values so terminal logs remain readable and grep-friendly."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, int | float):
            return str(value)
        if isinstance(value, str):
            return self._format_text(value)
        if isinstance(value, list | tuple | set):
            return "[" + ",".join(self._format_value(item) for item in value) + "]"
        if isinstance(value, dict):
            return self._format_mapping(value)
        return self._format_text(str(value))

    def _format_mapping(self, value: dict[Any, Any]) -> str:
        """Render mapping values without switching the full log line to JSON."""
        items = [
            f"{self._format_value(str(key))}:{self._format_value(item)}"
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        ]
        return "{" + ",".join(items) + "}"

    def _format_text(self, value: str) -> str:
        """Quote only text values that would otherwise split across fields."""
        if value and not any(char.isspace() or char in '="' for char in value):
            return value
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'


def configure_logging() -> None:
    """Set a readable default log format for local and deployed runs."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(
        KeyValueFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def bind_request_id(request_id: str) -> Token[str | None]:
    """Bind one request id to the current async context."""
    return _current_request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous async-context request id."""
    _current_request_id.reset(token)


def current_request_id() -> str | None:
    """Return the request id bound to the current async context."""
    return _current_request_id.get()


def get_request_id(request: Request) -> str:
    """Read or create the request id attached to one FastAPI request."""
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    request_id = _request_id_from_header(request) or uuid4().hex
    request.state.request_id = request_id
    return request_id


def _request_id_from_header(request: Request) -> str | None:
    """Use the caller-provided request id when it is short and non-empty."""
    raw = request.headers.get(REQUEST_ID_HEADER, "").strip()
    if not raw:
        return None
    return raw[:128]


def log_http_requests(app: FastAPI) -> None:
    """Attach middleware that logs every completed HTTP request."""

    @app.middleware("http")
    async def log_http_request(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Log request method, path, status, and duration."""
        request_id = get_request_id(request)
        token = bind_request_id(request_id)
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - started_at
            http_logger.info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": str(status_code),
                    "duration_seconds": round(elapsed, 6),
                },
            )
            reset_request_id(token)
