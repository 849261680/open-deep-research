from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from ..models.research_task import Citation
from ..models.research_task import ResearchSection
from ..models.research_task import ResearchTask
from ..models.research_task import ResearchTaskStatus
from ..models.research_task import utc_now
from ..services.evidence_store import EvidenceStore
from ..services.research_repository import ResearchRepository
from .conductor import ResearchConductor
from .cost_tracker import CostTracker
from .models import ResearchSource
from .models import SubQueryContext
from .writer import ResearchWriter


class ResearchAgent:
    """Stateful GPT Researcher-style agent for one research task."""

    def __init__(
        self,
        *,
        query: str,
        repository: ResearchRepository | None = None,
        max_sub_queries: int = 5,
        max_concurrency: int = 3,
    ) -> None:
        self.query = query
        self.role = "专业、客观、重视来源证据的研究分析师"
        self.max_sub_queries = max_sub_queries
        self.max_concurrency = max_concurrency
        self.sub_queries: list[str] = []
        self.context: list[SubQueryContext] = []
        self.research_sources: list[ResearchSource] = []
        self.visited_urls: set[str] = set()
        self.repository = repository
        self.task_id: str | None = None
        self.evidence_store = EvidenceStore()
        self.cost_tracker = CostTracker()
        self.conductor = ResearchConductor(self)
        self.writer = ResearchWriter(self.cost_tracker)

    async def run(self, task: ResearchTask) -> AsyncGenerator[dict[str, object], None]:
        event_queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

        async def collect_event(event: dict[str, object]) -> None:
            await event_queue.put(event)

        self.task_id = task.id
        task.status = ResearchTaskStatus.PLANNING
        conduct_task = asyncio.create_task(
            self.conductor.conduct_research(on_event=collect_event)
        )
        try:
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                except TimeoutError:
                    if conduct_task.done():
                        break
                    continue
                if event["type"] == "plan":
                    event_data = event.get("data", {})
                    sub_queries = (
                        event_data.get("sub_queries", [])
                        if isinstance(event_data, dict)
                        else event_data
                    )
                    if isinstance(sub_queries, list):
                        task.sections = self._sub_queries_to_sections(
                            [str(item) for item in sub_queries]
                        )
                        task.status = ResearchTaskStatus.RESEARCHING
                        task.touch()
                        yield {
                            "type": "plan",
                            "message": str(event["message"]),
                            "data": [section.model_dump() for section in task.sections],
                        }
                        yield {
                            "type": "cost_update",
                            "message": "成本统计已更新",
                            "data": self.cost_tracker.summary(),
                        }
                    else:
                        yield event
                elif event["type"] == "step_complete":
                    event_data = event.get("data")
                    if isinstance(event_data, dict):
                        self._apply_step_complete(task, event_data)
                    yield event
                else:
                    yield event

            contexts = await conduct_task
            task.sections = self._contexts_to_sections(contexts)
            task.touch()

            task.status = ResearchTaskStatus.REPORTING
            task.touch()
            yield {
                "type": "report_generating",
                "message": "正在生成最终研究报告...",
                "data": None,
            }

            report = await self.writer.write_report(
                query=task.query,
                sections=task.sections,
                context=contexts,
                sources=self.research_sources,
            )
            task.final_report = report
            task.cost_summary = self.cost_tracker.summary()
            task.status = ResearchTaskStatus.COMPLETED
            task.touch()
            task.completed_at = task.updated_at

            yield {
                "type": "cost_update",
                "message": "成本统计已完成",
                "data": task.cost_summary,
            }

            yield {
                "type": "report_complete",
                "message": "研究完成",
                "data": {
                    "id": task.id,
                    "user_id": task.user_id,
                    "query": task.query,
                    "status": task.status.value,
                    "architecture": "gpt_researcher",
                    "cost_summary": task.cost_summary,
                    "plan": [
                        {
                            "step": section.step,
                            "title": section.title,
                            "description": section.description,
                            "tool": section.tool,
                            "search_queries": section.search_queries,
                            "expected_outcome": section.expected_outcome,
                        }
                        for section in task.sections
                    ],
                    "sections": [section.model_dump() for section in task.sections],
                    "results": self.writer.to_legacy_results(contexts),
                    "report": report,
                    "timestamp": task.completed_at,
                },
            }
        finally:
            if not conduct_task.done():
                conduct_task.cancel()
                try:
                    await conduct_task
                except asyncio.CancelledError:
                    pass

    def _contexts_to_sections(
        self, contexts: list[SubQueryContext]
    ) -> list[ResearchSection]:
        sections: list[ResearchSection] = []
        for context in contexts:
            sections.append(
                ResearchSection(
                    id=f"subquery-{context.step}",
                    step=context.step,
                    title=context.query,
                    description="GPT Researcher sub-query",
                    tool="research_conductor",
                    search_queries=[context.query],
                    expected_outcome="收集并压缩与该子查询相关的上下文",
                    status="completed",
                    analysis=context.context,
                    citations=context.citations,
                    evidence_ids=context.evidence_ids,
                    compressed_evidence=context.compressed_evidence,
                    verification=context.verification,
                    completed_at=utc_now(),
                )
            )
        return sections

    def _sub_queries_to_sections(self, sub_queries: list[str]) -> list[ResearchSection]:
        return [
            ResearchSection(
                id=f"subquery-{index}",
                step=index,
                title=sub_query,
                description="GPT Researcher sub-query",
                tool="research_conductor",
                search_queries=[sub_query],
                expected_outcome="收集并压缩与该子查询相关的上下文",
            )
            for index, sub_query in enumerate(sub_queries, start=1)
        ]

    def _apply_step_complete(self, task: ResearchTask, event_data: dict[str, object]) -> None:
        step = event_data.get("step")
        if not isinstance(step, int):
            return

        section = next((item for item in task.sections if item.step == step), None)
        if section is None:
            return

        section.status = str(event_data.get("status", "completed"))
        section.analysis = str(event_data.get("analysis", section.analysis))
        section.evidence_ids = [
            str(item) for item in event_data.get("evidence_ids", section.evidence_ids)
        ]
        section.compressed_evidence = str(
            event_data.get("compressed_evidence", section.compressed_evidence)
        )
        verification = event_data.get("verification", section.verification)
        if isinstance(verification, dict):
            section.verification = verification
        citations = event_data.get("citations", [])
        if isinstance(citations, list):
            section.citations = [
                Citation.model_validate(item)
                for item in citations
                if isinstance(item, dict)
            ]
        section.completed_at = utc_now()
        task.touch()
