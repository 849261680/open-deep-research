"""Run and translate the multi-step research workflow."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import cast

from ..models.research_task import Citation
from ..models.research_task import ResearchSection
from ..models.research_task import ResearchTask
from ..models.research_task import ResearchTaskStatus
from ..models.research_task import utc_now
from ..services.evidence_store import EvidenceStore
from ..services.research_repository import ResearchRepository
from .conductor import ResearchConductor
from .config import ResearchConfig
from .cost_tracker import CostTracker
from .models import DeepResearchDecision
from .models import ResearchPlanItem
from .models import ResearchSource
from .models import SubQueryContext
from .writer import ResearchWriter

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Stateful GPT Researcher-style agent for one research task."""

    def __init__(
        self,
        *,
        query: str,
        repository: ResearchRepository | None = None,
        max_sub_queries: int = 5,
        max_concurrency: int = 3,
        config: ResearchConfig | None = None,
        plan_items: list[ResearchPlanItem] | None = None,
    ) -> None:
        """Create one agent instance for a single research query."""
        resolved_config = config or self._config_from_defaults(
            max_sub_queries=max_sub_queries,
            max_concurrency=max_concurrency,
        )
        self.query = query
        self.role = "专业、客观、重视来源证据的研究分析师"
        self.config = resolved_config
        self.max_sub_queries = resolved_config.max_sub_queries
        self.max_concurrency = resolved_config.max_concurrency
        self.sub_queries: list[str] = []
        self.context: list[SubQueryContext] = []
        self.checkpoint_contexts: list[SubQueryContext] = []
        self.research_sources: list[ResearchSource] = []
        self.visited_urls: set[str] = set()
        self.plan_items: list[ResearchPlanItem] = []
        self.confirmed_plan_items = plan_items or []
        self.repository = repository
        self.task_id: str | None = None
        self.evidence_store = EvidenceStore()
        self.cost_tracker = CostTracker()
        self.conductor = ResearchConductor(self)
        self.writer = ResearchWriter(self.cost_tracker, config=resolved_config)

    def _config_from_defaults(
        self,
        *,
        max_sub_queries: int,
        max_concurrency: int,
    ) -> ResearchConfig:
        """Resolve env defaults while honoring explicit constructor limits."""
        config = ResearchConfig.from_env()
        updates: dict[str, int] = {}
        if max_sub_queries != 5:
            updates["max_sub_queries"] = max_sub_queries
        if max_concurrency != 3:
            updates["max_concurrency"] = max_concurrency
        return config.model_copy(update=updates) if updates else config

    async def run(self, task: ResearchTask) -> AsyncGenerator[dict[str, object], None]:
        """Stream planning, research progress, cost, and final report events."""
        event_queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

        async def collect_event(event: dict[str, object]) -> None:
            """Bridge conductor callbacks into the run loop queue."""
            await event_queue.put(event)

        self.task_id = task.id
        self.checkpoint_contexts = self._sections_to_contexts(task.sections)
        task.status = ResearchTaskStatus.PLANNING
        conduct_task = asyncio.create_task(
            self.conductor.conduct_research(on_event=collect_event)
        )
        try:
            while True:
                event = await self._next_conductor_event(event_queue, conduct_task)
                if event is None:
                    break
                for update in self._updates_from_stream_event(task, event):
                    yield update

            contexts = await conduct_task
            contexts = self._merge_checkpoint_contexts(contexts)
            self.research_sources = self.conductor.source_curator.curate(
                [source for context in contexts for source in context.sources]
            )
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
            reference_entries = self.writer._collect_reference_entries(
                self.research_sources,
                task.sections,
                contexts,
            )
            quality_result = self.writer.evaluate_claim_support(report, reference_entries)
            task.claim_checks = cast(
                list[dict[str, object]],
                quality_result["claims"],
            )
            task.quality_summary = cast(
                dict[str, object],
                quality_result["summary"],
            )
            task.status = ResearchTaskStatus.COMPLETED
            task.touch()
            task.completed_at = task.updated_at

            yield {
                "type": "cost_update",
                "message": "成本统计已完成",
                "data": task.cost_summary,
            }

            report_payload = {
                "type": "report_complete",
                "message": "研究完成",
                "data": {
                    "id": task.id,
                    "user_id": task.user_id,
                    "query": task.query,
                    "status": task.status.value,
                    "architecture": "gpt_researcher",
                    "cost_summary": task.cost_summary,
                    "quality_summary": task.quality_summary,
                    "claim_checks": task.claim_checks,
                    "plan": [
                        {
                            "step": section.step,
                            "title": section.title,
                            "dimension": section.dimension,
                            "rationale": section.rationale,
                            "description": section.description,
                            "tool": section.tool,
                            "search_queries": section.search_queries,
                            "expected_outcome": section.expected_outcome,
                            "evidence_targets": section.evidence_targets,
                            "depth": section.depth,
                            "parent_query": section.parent_query,
                            "deep_research_reason": section.deep_research_reason,
                            "deep_research_stop_condition": section.deep_research_stop_condition,
                            "evidence_gaps": section.evidence_gaps,
                            "follow_up_queries": section.follow_up_queries,
                            "source_summary": section.source_summary,
                        }
                        for section in task.sections
                    ],
                    "sections": [section.model_dump() for section in task.sections],
                    "results": self.writer.to_legacy_results(contexts),
                    "report": report,
                    "timestamp": task.completed_at,
                },
            }
            self._log_report_complete(task, contexts)
            yield report_payload
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
        """Convert finished context objects into persisted report sections."""
        sections: list[ResearchSection] = []
        for context in contexts:
            plan_item = self._plan_item_for_query(context.query)
            sections.append(
                ResearchSection(
                    id=f"subquery-{context.step}",
                    step=context.step,
                    title=context.query,
                    description=(
                        plan_item.rationale if plan_item else "GPT Researcher sub-query"
                    ),
                    dimension=plan_item.dimension if plan_item else "",
                    rationale=plan_item.rationale if plan_item else "",
                    tool="research_conductor",
                    search_queries=(
                        plan_item.search_queries if plan_item else [context.query]
                    ),
                    expected_outcome=(
                        plan_item.expected_outcome
                        if plan_item else "收集并压缩与该子查询相关的上下文"
                    ),
                    evidence_targets=plan_item.evidence_targets if plan_item else [],
                    depth=context.depth,
                    parent_query=context.parent_query,
                    deep_research_reason=context.deep_research.reason,
                    deep_research_stop_condition=context.deep_research.stop_condition,
                    evidence_gaps=context.deep_research.evidence_gaps,
                    follow_up_queries=context.deep_research.follow_up_queries,
                    status="completed",
                    analysis=context.context,
                    citations=context.citations,
                    search_sources=[
                        {
                            "title": source.title,
                            "link": source.link,
                            "source": source.source,
                            "query": source.query,
                            "status": source.status,
                            "failure_reason": source.failure_reason,
                        }
                        for source in context.sources
                    ],
                    evidence_ids=context.evidence_ids,
                    compressed_evidence=context.compressed_evidence,
                    verification=context.verification,
                    source_summary=context.source_summary,
                    completed_at=utc_now(),
                )
            )
        return sections

    def _sections_to_contexts(
        self,
        sections: list[ResearchSection],
    ) -> list[SubQueryContext]:
        """Restore completed checkpoint sections as reusable research contexts."""
        contexts: list[SubQueryContext] = []
        for section in sections:
            if section.status != "completed":
                continue
            contexts.append(
                SubQueryContext(
                    step=section.step,
                    query=section.title,
                    depth=section.depth,
                    parent_query=section.parent_query,
                    sources=[
                        ResearchSource(
                            title=str(source.get("title", "")),
                            link=str(source.get("link", "")),
                            source=str(source.get("source", "web")),
                            query=str(source.get("query", "")),
                            status=str(source.get("status", "cited")),
                            failure_reason=str(source.get("failure_reason", "")),
                        )
                        for source in section.search_sources
                        if isinstance(source, dict)
                    ],
                    citations=section.citations,
                    evidence_ids=section.evidence_ids,
                    compressed_evidence=section.compressed_evidence,
                    verification=section.verification,
                    deep_research=DeepResearchDecision(
                        reason=section.deep_research_reason,
                        evidence_gaps=section.evidence_gaps,
                        follow_up_queries=section.follow_up_queries,
                        stop_condition=section.deep_research_stop_condition,
                    ),
                    context=section.analysis,
                    source_summary=section.source_summary,
                )
            )
        return contexts

    def _merge_checkpoint_contexts(
        self,
        contexts: list[SubQueryContext],
    ) -> list[SubQueryContext]:
        """Combine restored checkpoint contexts with newly completed contexts."""
        merged = {context.step: context for context in self.checkpoint_contexts}
        for context in contexts:
            merged[context.step] = context
        return sorted(merged.values(), key=lambda item: item.step)

    def _sections_from_plan_event(self, data: object) -> list[ResearchSection]:
        """Build task sections from detailed or legacy plan event payloads."""
        plan_items = self._plan_items_from_event_data(data)
        if plan_items:
            self.plan_items = plan_items
            return self._plan_items_to_sections(plan_items)

        sub_queries = self._sub_queries_from_event_data(data)
        if sub_queries:
            return self._sub_queries_to_sections(sub_queries)
        return []

    def _plan_items_from_event_data(self, data: object) -> list[ResearchPlanItem]:
        """Read detailed plan items from a stream event payload."""
        if not isinstance(data, dict):
            return []
        raw_items = data.get("plan_items")
        if not isinstance(raw_items, list):
            return []
        plan_items = []
        for raw_item in raw_items:
            if isinstance(raw_item, ResearchPlanItem):
                plan_items.append(raw_item)
            elif isinstance(raw_item, dict):
                plan_items.append(ResearchPlanItem.model_validate(raw_item))
        return plan_items

    def _sub_queries_from_event_data(self, data: object) -> list[str]:
        """Read legacy sub-query strings from a stream event payload."""
        raw_items = data.get("sub_queries", []) if isinstance(data, dict) else data
        if not isinstance(raw_items, list):
            return []
        return [str(item) for item in raw_items]

    def _plan_items_to_sections(
        self,
        plan_items: list[ResearchPlanItem],
    ) -> list[ResearchSection]:
        """Convert detailed plan items into user-visible research sections."""
        return [
            ResearchSection(
                id=f"subquery-{item.step}",
                step=item.step,
                title=item.title,
                description=item.rationale or "GPT Researcher sub-query",
                dimension=item.dimension,
                rationale=item.rationale,
                tool="research_conductor",
                search_queries=item.search_queries or [item.title],
                expected_outcome=(
                    item.expected_outcome or "收集并压缩与该子查询相关的上下文"
                ),
                evidence_targets=item.evidence_targets,
            )
            for item in plan_items
        ]

    def _sub_queries_to_sections(self, sub_queries: list[str]) -> list[ResearchSection]:
        """Convert legacy sub-query strings into user-visible sections."""
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
        """Merge one completed research step into the matching task section."""
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
        section.depth = int(event_data.get("depth", section.depth))
        section.parent_query = str(event_data.get("parent_query", section.parent_query))
        deep_research = event_data.get("deep_research", {})
        if isinstance(deep_research, dict):
            section.deep_research_reason = str(
                deep_research.get("reason", section.deep_research_reason)
            )
            section.deep_research_stop_condition = str(
                deep_research.get(
                    "stop_condition",
                    section.deep_research_stop_condition,
                )
            )
            evidence_gaps = deep_research.get("evidence_gaps", [])
            if isinstance(evidence_gaps, list):
                section.evidence_gaps = [str(item) for item in evidence_gaps]
            follow_up_queries = deep_research.get("follow_up_queries", [])
            if isinstance(follow_up_queries, list):
                section.follow_up_queries = [str(item) for item in follow_up_queries]
        citations = event_data.get("citations", [])
        if isinstance(citations, list):
            section.citations = [
                Citation.model_validate(item)
                for item in citations
                if isinstance(item, dict)
            ]
        search_sources = event_data.get("search_sources", [])
        if isinstance(search_sources, list):
            section.search_sources = [
                item for item in search_sources if isinstance(item, dict)
            ]
        section.completed_at = utc_now()
        task.touch()

    def _plan_item_for_query(self, query: str) -> ResearchPlanItem | None:
        """Find the detailed plan item that produced one sub-query."""
        for item in self.plan_items:
            if item.title == query:
                return item
        return None

    async def _next_conductor_event(
        self,
        event_queue: asyncio.Queue[dict[str, object]],
        conduct_task: asyncio.Task[list[SubQueryContext]],
    ) -> dict[str, object] | None:
        """Read the next conductor event or stop once the conductor is done."""
        try:
            return await asyncio.wait_for(event_queue.get(), timeout=0.1)
        except TimeoutError:
            return None if conduct_task.done() else {}

    def _updates_from_stream_event(
        self,
        task: ResearchTask,
        event: dict[str, object],
    ) -> list[dict[str, object]]:
        """Translate a conductor event into API stream updates."""
        if event == {}:
            return []
        if event["type"] == "plan":
            return self._updates_from_plan_event(task, event)
        if event["type"] == "step_complete":
            self._apply_step_event(task, event)
        return [event]

    def _updates_from_plan_event(
        self,
        task: ResearchTask,
        event: dict[str, object],
    ) -> list[dict[str, object]]:
        """Translate a plan event into plan and cost updates."""
        sections = self._sections_from_plan_event(event.get("data", {}))
        if not sections:
            return [event]
        task.sections = self._merge_checkpoint_sections(task.sections, sections)
        task.status = ResearchTaskStatus.RESEARCHING
        task.touch()
        return [
            {
                "type": "plan",
                "message": str(event["message"]),
                "data": [section.model_dump() for section in task.sections],
            },
            {
                "type": "cost_update",
                "message": "成本统计已更新",
                "data": self.cost_tracker.summary(),
            },
        ]

    def _merge_checkpoint_sections(
        self,
        existing_sections: list[ResearchSection],
        planned_sections: list[ResearchSection],
    ) -> list[ResearchSection]:
        """Keep completed checkpoint sections when a resume emits a plan event."""
        completed_by_step = {
            section.step: section
            for section in existing_sections
            if section.status == "completed"
        }
        return [
            completed_by_step.get(section.step, section)
            for section in planned_sections
        ]

    def _apply_step_event(
        self,
        task: ResearchTask,
        event: dict[str, object],
    ) -> None:
        """Apply step-complete payloads when the payload shape is valid."""
        event_data = event.get("data")
        if isinstance(event_data, dict):
            self._apply_step_complete(task, event_data)

    def _log_report_complete(
        self,
        task: ResearchTask,
        contexts: list[SubQueryContext],
    ) -> None:
        """Write final report metadata as a structured backend log."""
        root_sections = [context for context in contexts if context.depth == 1]
        deeper_sections = [context for context in contexts if context.depth > 1]
        logger.info(
            "report_complete",
            extra={
                "task_id": task.id,
                "research_event_type": "report_complete",
                "query": task.query,
                "status": task.status.value,
                "section_count": len(contexts),
                "root_section_count": len(root_sections),
                "deep_section_count": len(deeper_sections),
                "max_depth": max((context.depth for context in contexts), default=0),
                "source_count": len(self.research_sources),
                "total_tokens": task.cost_summary.get("total_tokens", 0),
                "estimated_cost_usd": task.cost_summary.get("estimated_cost_usd", 0),
            },
        )
