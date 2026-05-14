from __future__ import annotations

import sys
import asyncio
from collections.abc import Generator
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)


@pytest.fixture(autouse=True)
def dispose_async_db_engine_after_test() -> Generator[None, None, None]:
    """Close SQLAlchemy async connections so aiosqlite worker threads exit."""
    yield

    from backend.app.db.base import engine

    asyncio.run(engine.dispose())
