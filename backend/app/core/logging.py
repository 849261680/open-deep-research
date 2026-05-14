"""Configure application logging for the backend runtime."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Awaitable
from collections.abc import Callable

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

http_logger = logging.getLogger("backend.http")


def configure_logging() -> None:
    """Set a readable default log format for local and deployed runs."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logging.getLogger().setLevel(level)


def log_http_requests(app: FastAPI) -> None:
    """Attach middleware that logs every completed HTTP request."""

    @app.middleware("http")
    async def log_http_request(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Log request method, path, status, and duration."""
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - started_at
            http_logger.info(
                "http_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": str(status_code),
                    "duration_seconds": round(elapsed, 6),
                },
            )
