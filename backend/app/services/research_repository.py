from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from ..models.research_task import EvidenceItem
from ..models.research_task import ResearchTask


class ResearchRepository:
    """SQLite persistence for research tasks and evidence."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv(
            "RESEARCH_DB_PATH",
            str(Path("backend/data/research.db")),
        )
        self._ensure_db()

    def _ensure_db(self) -> None:
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_tasks (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_items (
                    id TEXT PRIMARY KEY,
                    section_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_task(self, task: ResearchTask) -> None:
        payload = json.dumps(task.model_dump(), ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO research_tasks (id, query, status, payload, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    query=excluded.query,
                    status=excluded.status,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (task.id, task.query, task.status.value, payload, task.updated_at),
            )
            conn.commit()

    def save_evidence(self, task_id: str, evidence: EvidenceItem) -> None:
        payload = json.dumps(evidence.model_dump(), ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO evidence_items (id, section_id, task_id, payload, captured_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    section_id=excluded.section_id,
                    task_id=excluded.task_id,
                    payload=excluded.payload,
                    captured_at=excluded.captured_at
                """,
                (
                    evidence.id,
                    evidence.section_id,
                    task_id,
                    payload,
                    evidence.captured_at,
                ),
            )
            conn.commit()

    def load_tasks(self) -> list[dict[str, object]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT payload FROM research_tasks ORDER BY updated_at DESC"
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def load_task(self, task_id: str) -> ResearchTask | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT payload FROM research_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return ResearchTask.model_validate(json.loads(row[0]))

    def load_task_payload(self, task_id: str) -> dict[str, object] | None:
        task = self.load_task(task_id)
        return task.model_dump() if task is not None else None

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM evidence_items")
            conn.execute("DELETE FROM research_tasks")
            conn.commit()
