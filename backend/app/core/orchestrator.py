from __future__ import annotations

import asyncio
from contextlib import suppress
from collections.abc import AsyncGenerator
from uuid import uuid4

from ..models.research_task import ResearchTask
from ..models.research_task import ResearchTaskStatus
from ..research.agent import ResearchAgent
from ..services.research_repository import ResearchRepository


class ResearchOrchestrator:
    """Thin persistence and API orchestration layer for ResearchAgent."""

    def __init__(self) -> None:
        self.repository = ResearchRepository()
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

    async def run(
        self, query: str, user_id: int | None = None
    ) -> AsyncGenerator[dict[str, object], None]:
        task = ResearchTask(id=str(uuid4()), user_id=user_id, query=query)
        task.status = ResearchTaskStatus.PLANNING
        task.touch()
        self.repository.save_task(task)
        yield self._event(
            "planning",
            "研究任务已创建，正在规划研究...",
            {
                "id": task.id,
                "task_id": task.id,
                "user_id": task.user_id,
                "query": task.query,
                "status": task.status.value,
                "timestamp": task.updated_at,
            },
        )
        async for update in self.run_task(task):
            yield update

    async def run_task(
        self, task: ResearchTask
    ) -> AsyncGenerator[dict[str, object], None]:
        research_agent = ResearchAgent(query=task.query, repository=self.repository)
        update_queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

        async def produce_updates() -> None:
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
                    if isinstance(update, dict):
                        task.touch()
                        self.repository.save_task(task)
                        yield update
                    continue

                if event_type == "exception":
                    exc = queued["data"]
                    raise exc if isinstance(exc, Exception) else RuntimeError(str(exc))

                if event_type == "cancelled":
                    self._mark_stopped(task)
                    with suppress(asyncio.CancelledError):
                        await runner
                    return

                if event_type == "done":
                    return
        except asyncio.CancelledError:
            runner.cancel()
            with suppress(asyncio.CancelledError):
                await runner
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

    def get_history(self, user_id: int | None = None) -> list[dict[str, object]]:
        return self.repository.load_tasks(user_id=user_id)

    def get_task(self, task_id: str, user_id: int | None = None) -> dict[str, object] | None:
        return self.repository.load_task_payload(task_id, user_id=user_id)

    async def resume_task(
        self, task_id: str, user_id: int | None = None
    ) -> AsyncGenerator[dict[str, object], None]:
        task = self.repository.load_task(task_id, user_id=user_id)
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

        yield self._event("resume", "正在重新运行未完成研究任务...", {"task_id": task.id})
        async for update in self.run_task(task):
            yield update

    def clear(self, user_id: int | None = None) -> int:
        if user_id is None:
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
        self, task_id: str, user_id: int | None = None
    ) -> dict[str, object] | None:
        task = self.repository.load_task(task_id, user_id=user_id)
        if task is None:
            return None

        active_task = self._active_tasks.get(task_id)
        if active_task is not None and not active_task.done():
            active_task.cancel()

        self._mark_stopped(task)
        return task.model_dump()

    def _event(self, event_type: str, message: str, data: object) -> dict[str, object]:
        return {"type": event_type, "message": message, "data": data}

    def _mark_stopped(self, task: ResearchTask) -> None:
        task.status = ResearchTaskStatus.FAILED
        task.error = "研究已停止"
        task.touch()
        self.repository.save_task(task)


research_orchestrator = ResearchOrchestrator()
