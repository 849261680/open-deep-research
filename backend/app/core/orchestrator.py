from __future__ import annotations

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
        research_agent = ResearchAgent(query=task.query)
        try:
            async for update in research_agent.run(task):
                task.touch()
                self.repository.save_task(task)
                yield update
        except Exception as exc:  # noqa: BLE001
            task.status = ResearchTaskStatus.FAILED
            task.error = str(exc)
            task.touch()
            self.repository.save_task(task)
            yield self._event("error", f"报告生成失败: {exc}", None)

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

    def clear(self) -> None:
        self.repository.clear()

    def _event(self, event_type: str, message: str, data: object) -> dict[str, object]:
        return {"type": event_type, "message": message, "data": data}


research_orchestrator = ResearchOrchestrator()
