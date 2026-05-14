"""Coordinate research task persistence and agent streaming."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from collections.abc import AsyncGenerator
from uuid import uuid4

from ..models.research_task import ResearchTask
from ..models.research_task import ResearchTaskStatus
from ..research.agent import ResearchAgent
from ..research.config import ResearchConfig
from ..services.research_repository import ResearchRepository


class ResearchOrchestrator:
    """Thin persistence and API orchestration layer for ResearchAgent."""

    def __init__(self) -> None:
        """Create the repository-backed orchestrator state."""
        self.repository = ResearchRepository()
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

    async def run(
        self,
        query: str,
        user_id: int | None = None,
        guest_id: str | None = None,
        config: ResearchConfig | None = None,
    ) -> AsyncGenerator[dict[str, object], None]:
        """Create and stream a new research task."""
        task = ResearchTask(
            id=str(uuid4()),
            user_id=user_id,
            guest_id=None if user_id is not None else guest_id,
            query=query,
        )
        task.status = ResearchTaskStatus.PLANNING
        task.touch()
        self.repository.save_task(task)
        yield self._event(
            "task_created",
            "研究任务已创建",
            {
                "id": task.id,
                "task_id": task.id,
                "user_id": task.user_id,
                "guest_id": task.guest_id,
                "query": task.query,
                "status": task.status.value,
                "timestamp": task.updated_at,
            },
        )
        async for update in self.run_task(task, config=config):
            yield update

    async def run_task(
        self, task: ResearchTask, config: ResearchConfig | None = None
    ) -> AsyncGenerator[dict[str, object], None]:
        """Run an existing task and persist stream progress."""
        research_agent = ResearchAgent(
            query=task.query,
            repository=self.repository,
            config=config,
        )
        update_queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

        async def produce_updates() -> None:
            """Forward agent updates into a queue owned by the orchestrator."""
            try:
                async for update in research_agent.run(task):
                    await update_queue.put({"type": "update", "data": update})
            except asyncio.CancelledError:
                await update_queue.put({"type": "cancelled", "data": None})
                raise
            except Exception as exc:  # noqa: BLE001
                await update_queue.put({"type": "exception", "data": exc})
            finally:
                await update_queue.put({"type": "done", "data": None})

        runner = asyncio.create_task(produce_updates())
        self._active_tasks[task.id] = runner
        try:
            while True:
                queued = await update_queue.get()
                event_type = queued["type"]

                if event_type == "update":
                    update = queued["data"]
                    yield self._persist_stream_update(task, update)
                    continue

                if event_type == "exception":
                    exc = queued["data"]
                    raise exc if isinstance(exc, Exception) else RuntimeError(str(exc))

                if event_type == "cancelled":
                    self._mark_stopped(task)
                    await self._await_cancelled(runner)
                    return

                if event_type == "done":
                    return
        except asyncio.CancelledError:
            runner.cancel()
            await self._await_cancelled(runner)
            self._mark_stopped(task)
            raise
        except Exception as exc:  # noqa: BLE001
            task.status = ResearchTaskStatus.FAILED
            task.error = str(exc)
            task.touch()
            self.repository.save_task(task)
            yield self._event("error", f"报告生成失败: {exc}", None)
        finally:
            if self._active_tasks.get(task.id) is runner:
                self._active_tasks.pop(task.id, None)

    def get_history(
        self,
        user_id: int | None = None,
        guest_id: str | None = None,
    ) -> list[dict[str, object]]:
        """Load research task summaries for one owner scope."""
        return self.repository.load_tasks(user_id=user_id, guest_id=guest_id)

    def get_task(
        self,
        task_id: str,
        user_id: int | None = None,
        guest_id: str | None = None,
    ) -> dict[str, object] | None:
        """Load one task payload if it belongs to the owner scope."""
        return self.repository.load_task_payload(
            task_id,
            user_id=user_id,
            guest_id=guest_id,
        )

    async def resume_task(
        self,
        task_id: str,
        user_id: int | None = None,
        guest_id: str | None = None,
    ) -> AsyncGenerator[dict[str, object], None]:
        """Restart an unfinished task from its saved query."""
        task = self.repository.load_task(task_id, user_id=user_id, guest_id=guest_id)
        if task is None:
            yield self._event("error", f"任务不存在: {task_id}", None)
            return
        if task.status == ResearchTaskStatus.COMPLETED:
            yield self._event(
                "report_complete",
                "研究已完成",
                task.model_dump(),
            )
            return

        self.repository.delete_evidence_for_task(task.id)
        yield self._event("resume", "正在重新运行未完成研究任务...", {"task_id": task.id})
        async for update in self.run_task(task):
            yield update

    def clear(
        self,
        user_id: int | None = None,
        guest_id: str | None = None,
    ) -> int:
        """Clear saved tasks and cancel active work in the owner scope."""
        if user_id is None:
            if guest_id is not None:
                return self.repository.clear(guest_id=guest_id)
            for task in self._active_tasks.values():
                task.cancel()
            self._active_tasks.clear()
            return self.repository.clear()

        owned_task_ids = {
            item["id"]
            for item in self.repository.load_tasks(user_id=user_id)
            if isinstance(item, dict) and item.get("id")
        }
        for task_id in owned_task_ids:
            active_task = self._active_tasks.get(task_id)
            if active_task is not None and not active_task.done():
                active_task.cancel()
            self._active_tasks.pop(task_id, None)

        return self.repository.clear(user_id=user_id)

    def stop_task(
        self,
        task_id: str,
        user_id: int | None = None,
        guest_id: str | None = None,
    ) -> dict[str, object] | None:
        """Cancel active work and mark one task as stopped."""
        task = self.repository.load_task(task_id, user_id=user_id, guest_id=guest_id)
        if task is None:
            return None

        active_task = self._active_tasks.get(task_id)
        if active_task is not None and not active_task.done():
            active_task.cancel()

        self._mark_stopped(task)
        return task.model_dump()

    def _event(self, event_type: str, message: str, data: object) -> dict[str, object]:
        """Build one API stream event."""
        return {"type": event_type, "message": message, "data": data}

    def _persist_stream_update(
        self, task: ResearchTask, update: object
    ) -> dict[str, object]:
        """Persist task freshness when the queued update is streamable."""
        if not isinstance(update, dict):
            raise TypeError("ResearchAgent emitted a non-dict update")
        task.touch()
        self.repository.save_task(task)
        return update

    async def _await_cancelled(self, runner: asyncio.Task[None]) -> None:
        """Wait for a cancelled runner without leaking cancellation."""
        with suppress(asyncio.CancelledError):
            await runner

    def _mark_stopped(self, task: ResearchTask) -> None:
        """Persist a task as stopped by the user or cancellation."""
        task.status = ResearchTaskStatus.FAILED
        task.error = "研究已停止"
        task.touch()
        self.repository.save_task(task)


research_orchestrator = ResearchOrchestrator()
