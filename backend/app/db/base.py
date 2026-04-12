import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DEFAULT_DB_PATH = Path("backend/data/app.db").resolve()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}",
)

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def resolve_sqlite_db_path(database_url: str) -> Path | None:
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        return None

    raw_path = database_url.removeprefix(prefix)
    if not raw_path:
        return None

    # `sqlite+aiosqlite:///foo.db` is a project-relative path, while
    # `sqlite+aiosqlite:////tmp/foo.db` should remain absolute.
    if raw_path.startswith("/"):
        return Path(raw_path)
    return Path(raw_path).resolve()


async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """创建所有表"""
    from backend.app.models.user import User  # noqa: F401

    if DATABASE_URL.startswith("sqlite"):
        sqlite_path = resolve_sqlite_db_path(DATABASE_URL)
        if sqlite_path:
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
