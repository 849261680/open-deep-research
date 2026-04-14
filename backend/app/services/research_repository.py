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
                    user_id INTEGER,
                    query TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(research_tasks)").fetchall()
            }
            if "user_id" not in columns:
                conn.execute("ALTER TABLE research_tasks ADD COLUMN user_id INTEGER")
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
                INSERT INTO research_tasks (id, user_id, query, status, payload, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id=excluded.user_id,
                    query=excluded.query,
                    status=excluded.status,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (
                    task.id,
                    task.user_id,
                    task.query,
                    task.status.value,
                    payload,
                    task.updated_at,
                ),
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

    def load_tasks(self, user_id: int | None = None) -> list[dict[str, object]]:
        with sqlite3.connect(self.db_path) as conn:
            if user_id is None:
                rows = conn.execute(
                    """
                    SELECT payload FROM research_tasks
                    WHERE user_id IS NULL
                    ORDER BY updated_at DESC
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT payload FROM research_tasks
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                    """,
                    (user_id,),
                ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def load_task(self, task_id: str, user_id: int | None = None) -> ResearchTask | None:
        with sqlite3.connect(self.db_path) as conn:
            if user_id is None:
                row = conn.execute(
                    """
                    SELECT payload FROM research_tasks
                    WHERE id = ? AND user_id IS NULL
                    """,
                    (task_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT payload FROM research_tasks WHERE id = ? AND user_id = ?",
                    (task_id, user_id),
                ).fetchone()
        if row is None:
            return None
        return ResearchTask.model_validate(json.loads(row[0]))

    def load_task_payload(
        self, task_id: str, user_id: int | None = None
    ) -> dict[str, object] | None:
        task = self.load_task(task_id, user_id=user_id)
        return task.model_dump() if task is not None else None

    def assign_anonymous_tasks_to_user(
        self, task_ids: list[str], user_id: int
    ) -> int:
        normalized_task_ids = [task_id for task_id in task_ids if task_id]
        if not normalized_task_ids:
            return 0

        placeholders = ",".join("?" for _ in normalized_task_ids)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"""
                UPDATE research_tasks
                SET user_id = ?
                WHERE user_id IS NULL AND id IN ({placeholders})
                """,
                [user_id, *normalized_task_ids],
            )
            conn.commit()
            return cursor.rowcount

    def clear(self, user_id: int | None = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            if user_id is None:
                deleted = conn.execute("SELECT COUNT(*) FROM research_tasks").fetchone()[0]
                conn.execute("DELETE FROM evidence_items")
                conn.execute("DELETE FROM research_tasks")
                conn.commit()
                return int(deleted)

            task_ids = [
                row[0]
                for row in conn.execute(
                    "SELECT id FROM research_tasks WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            ]
            if not task_ids:
                return 0

            placeholders = ",".join("?" for _ in task_ids)
            conn.execute(
                f"DELETE FROM evidence_items WHERE task_id IN ({placeholders})",
                task_ids,
            )
            conn.execute(
                f"DELETE FROM research_tasks WHERE id IN ({placeholders})",
                task_ids,
            )
            conn.commit()
            return len(task_ids)
