from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

from ..agents.report_generator import ReportGenerator
from ..agents.research_executor import ResearchExecutor
from ..agents.research_planner import ResearchPlanner
from ..models.research_task import ResearchSection
from ..models.research_task import ResearchTask
from ..models.research_task import ResearchTaskStatus
from ..services.compression_service import compression_service
from ..services.evidence_store import EvidenceStore
from ..services.research_repository import ResearchRepository
from ..services.verifier_service import verifier_service


class ResearchOrchestrator:
    """Coordinates research tasks across planning, evidence gathering, and reporting."""

    def __init__(self) -> None:
        self.planner = ResearchPlanner()
        self.executor = ResearchExecutor()
        self.report_generator = ReportGenerator()
        self.evidence_store = EvidenceStore()
        self.repository = ResearchRepository()
        self.max_section_retries = 1

    async def run(
        self, query: str, user_id: int | None = None
    ) -> AsyncGenerator[dict[str, object], None]:
        task = ResearchTask(id=str(uuid4()), user_id=user_id, query=query)
        async for update in self.run_task(task):
            yield update

    async def run_task(
        self, task: ResearchTask
    ) -> AsyncGenerator[dict[str, object], None]:
        task.status = ResearchTaskStatus.PLANNING
        task.touch()
        self.repository.save_task(task)

        yield self._event("planning", "正在制定研究计划...", {"task_id": task.id})

        if not task.sections:
            plan = await self.planner.plan_research(task.query)
            sections = self._build_sections(plan)
            task.sections = sections
            task.touch()
            self.repository.save_task(task)

        yield self._event(
            "plan",
            "研究计划制定完成",
            [section.model_dump() for section in task.sections],
        )

        task.status = ResearchTaskStatus.RESEARCHING
        task.touch()

        section_results: list[dict[str, object]] = []
        for section in task.sections:
            async for update in self._run_section(task, section):
                if update.get("type") == "step_complete" and update.get("data"):
                    section_results.append(dict(update["data"]))
                yield update

        task.status = ResearchTaskStatus.REPORTING
        task.touch()
        self.repository.save_task(task)
        yield self._event("report_generating", "正在生成最终研究报告...", None)

        try:
            final_report = await self.report_generator.generate_final_report(
                section_results,
                task.query,
            )
            task.final_report = final_report
            task.status = ResearchTaskStatus.COMPLETED
            task.touch()
            task.completed_at = task.updated_at
            self.repository.save_task(task)

            yield self._event(
                "report_complete",
                "研究完成",
                {
                    "id": task.id,
                    "query": task.query,
                    "status": task.status.value,
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
                    "results": section_results,
                    "report": final_report,
                    "timestamp": task.completed_at,
                },
            )
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
        async for update in self._resume_task(task):
            yield update

    def clear(self) -> None:
        self.evidence_store.clear()
        self.repository.clear()

    async def _capture_evidence(
        self, task_id: str, section: ResearchSection, data: object | None
    ) -> None:
        if not isinstance(data, dict):
            return
        query = data.get("query")
        sources = data.get("sources")
        if not isinstance(query, str) or not isinstance(sources, list):
            return
        evidence_ids = await self.evidence_store.add_many(
            section_id=section.id,
            query=query,
            source_type="web",
            task_id=task_id,
            items=[
                source
                for source in sources
                if isinstance(source, dict)
            ],
        )
        section.evidence_ids.extend(evidence_ids)
        section.citations = self.evidence_store.get_citations(section.evidence_ids)
        for evidence in self.evidence_store.get_many(evidence_ids):
            self.repository.save_evidence(task_id, evidence)

    async def _run_section(
        self, task: ResearchTask, section: ResearchSection
    ) -> AsyncGenerator[dict[str, object], None]:
        section.status = "executing"
        section.started_at = task.updated_at
        yield self._event(
            "step_start",
            f"开始执行：{section.title}",
            section.model_dump(),
        )

        while section.retry_count <= self.max_section_retries:
            failed = False
            async for update in self.executor.execute_research_step_with_updates(
                section.model_dump(), task.query
            ):
                if update.get("type") == "search_result":
                    await self._capture_evidence(task.id, section, update.get("data"))
                    update = {
                        **update,
                        "data": {
                            **(update.get("data") or {}),
                            "section_id": section.id,
                        },
                    }

                if update.get("type") == "step_complete" and update.get("data"):
                    step_data = dict(update["data"])
                    section.status = str(step_data.get("status", "completed"))
                    section.analysis = str(step_data.get("analysis", ""))
                    section.completed_at = task.updated_at
                    section.citations = self.evidence_store.get_citations(
                        section.evidence_ids
                    )
                    section.compressed_evidence = compression_service.compress_evidence(
                        section.title,
                        self.evidence_store.get_many(section.evidence_ids),
                    )
                    section.verification = await verifier_service.verify_section(
                        analysis=section.analysis,
                        citations=section.citations,
                        compressed_evidence=section.compressed_evidence,
                    )
                    step_data["section_id"] = section.id
                    step_data["compressed_evidence"] = section.compressed_evidence
                    step_data["verification"] = section.verification
                    step_data["citations"] = [
                        citation.model_dump() for citation in section.citations
                    ]
                    if section.status == "failed" and section.retry_count < self.max_section_retries:
                        failed = True
                        section.retry_count += 1
                        task.touch()
                        self.repository.save_task(task)
                        yield self._event(
                            "step_retry",
                            f"重试步骤：{section.title}",
                            {
                                "section_id": section.id,
                                "retry_count": section.retry_count,
                            },
                        )
                    else:
                        update = {**update, "data": step_data}
                        task.touch()
                        self.repository.save_task(task)
                        yield update

                elif update.get("type") != "step_complete":
                    task.touch()
                    self.repository.save_task(task)
                    yield update

            if not failed:
                break

    async def _resume_task(
        self, task: ResearchTask
    ) -> AsyncGenerator[dict[str, object], None]:
        yield self._event("resume", "正在恢复研究任务...", {"task_id": task.id})

        if not task.sections:
            async for update in self.run_task(task):
                yield update
            return

        yield self._event(
            "plan",
            "已加载已有研究计划",
            [section.model_dump() for section in task.sections],
        )

        task.status = ResearchTaskStatus.RESEARCHING
        task.touch()
        self.repository.save_task(task)

        section_results = [
            {
                "step": section.step,
                "title": section.title,
                "status": section.status,
                "analysis": section.analysis,
                "citations": [citation.model_dump() for citation in section.citations],
                "compressed_evidence": section.compressed_evidence,
                "verification": section.verification,
                "section_id": section.id,
            }
            for section in task.sections
            if section.status == "completed"
        ]

        for section in task.sections:
            if section.status == "completed":
                continue
            async for update in self._run_section(task, section):
                if update.get("type") == "step_complete" and update.get("data"):
                    section_results.append(dict(update["data"]))
                yield update

        task.status = ResearchTaskStatus.REPORTING
        task.touch()
        self.repository.save_task(task)
        yield self._event("report_generating", "正在生成最终研究报告...", None)

        try:
            final_report = await self.report_generator.generate_final_report(
                section_results,
                task.query,
            )
            task.final_report = final_report
            task.status = ResearchTaskStatus.COMPLETED
            task.touch()
            task.completed_at = task.updated_at
            self.repository.save_task(task)
            yield self._event(
                "report_complete",
                "研究完成",
                {
                    "id": task.id,
                    "user_id": task.user_id,
                    "query": task.query,
                    "status": task.status.value,
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
                    "results": section_results,
                    "report": final_report,
                    "timestamp": task.completed_at,
                },
            )
        except Exception as exc:  # noqa: BLE001
            task.status = ResearchTaskStatus.FAILED
            task.error = str(exc)
            task.touch()
            self.repository.save_task(task)
            yield self._event("error", f"报告生成失败: {exc}", None)

    def _build_sections(self, plan: list[dict[str, object]]) -> list[ResearchSection]:
        sections: list[ResearchSection] = []
        for index, raw_step in enumerate(plan, start=1):
            step = raw_step if isinstance(raw_step, dict) else {}
            search_queries = step.get("search_queries")
            normalized_queries = [
                item for item in search_queries if isinstance(item, str)
            ] if isinstance(search_queries, list) else []
            sections.append(
                ResearchSection(
                    id=str(uuid4()),
                    step=int(step.get("step", index)),
                    title=str(step.get("title", f"研究步骤 {index}")),
                    description=str(step.get("description", "")),
                    tool=str(step.get("tool", "comprehensive_search")),
                    search_queries=normalized_queries,
                    expected_outcome=str(step.get("expected_outcome", "")),
                )
            )
        return sections

    def _event(self, event_type: str, message: str, data: object) -> dict[str, object]:
        return {"type": event_type, "message": message, "data": data}


research_orchestrator = ResearchOrchestrator()
