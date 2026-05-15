"""SQLAlchemy records for persisted research tasks and evidence."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class ResearchTaskRecord(Base):
    """Database row for one persisted research task payload."""

    __tablename__ = "research_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    guest_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class EvidenceItemRecord(Base):
    """Database row for one captured evidence payload."""

    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    section_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
