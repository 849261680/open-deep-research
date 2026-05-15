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
from ..research.cost_tracker import CostTracker
from ..research.models import ResearchPlanItem
from ..research.query_planner import QueryPlanner
from ..research.retriever import ResearchRetriever
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
        plan_items: list[ResearchPlanItem] | None = None,
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
        async for update in self.run_task(task, config=config, plan_items=plan_items):
            yield update

    async def run_task(
        self,
        task: ResearchTask,
        config: ResearchConfig | None = None,
        plan_items: list[ResearchPlanItem] | None = None,
    ) -> AsyncGenerator[dict[str, object], None]:
        """Run an existing task and persist stream progress."""
        research_agent = ResearchAgent(
            query=task.query,
            repository=self.repository,
            config=config,
            plan_items=plan_items,
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

    async def preview_plan(
        self,
        query: str,
        config: ResearchConfig | None = None,
    ) -> dict[str, object]:
        """Generate a user-confirmable research plan without creating a task."""
        resolved_config = config or ResearchConfig.from_env()
        cost_tracker = CostTracker()
        retriever = ResearchRetriever(resolved_config)
        initial_results = await retriever.search(query)
        planner = QueryPlanner(cost_tracker)
        plan_items = await planner.plan_detailed(
            query=query,
            initial_results=initial_results,
            max_sub_queries=resolved_config.max_sub_queries,
        )
        plan_items = self._ensure_original_query_plan(query, plan_items)
        return {
            "query": query,
            "plan_items": self._serialize_plan_items(plan_items),
            "sub_queries": [item.title for item in plan_items],
            "cost_summary": cost_tracker.summary(),
        }

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

        yield self._event("resume", "正在从持久化检查点继续研究任务...", {"task_id": task.id})
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

    def _ensure_original_query_plan(
        self,
        query: str,
        plan_items: list[ResearchPlanItem],
    ) -> list[ResearchPlanItem]:
        """Append the original query as a plan item when absent."""
        if query in {item.title for item in plan_items}:
            return plan_items
        return [
            *plan_items,
            ResearchPlanItem(
                step=len(plan_items) + 1,
                title=query,
                dimension="核心问题",
                rationale="保留原始问题作为主线，确保最终报告直接回答用户问题。",
                search_queries=[query],
                expected_outcome="形成对原始问题的直接回答和证据汇总。",
                evidence_targets=["综合资料", "权威来源"],
            ),
        ]

    def _serialize_plan_items(
        self,
        plan_items: list[ResearchPlanItem],
    ) -> list[dict[str, object]]:
        """Serialize structured plan items for API responses."""
        return [item.model_dump() for item in plan_items]

    def _persist_stream_update(
        self, task: ResearchTask, update: object
    ) -> dict[str, object]:
        """Persist task freshness when the queued update is streamable."""
        if not isinstance(update, dict):
            raise TypeError("ResearchAgent emitted a non-dict update")
        task.stream_events.append(update)
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
