"""
纯逻辑单元测试 — 不依赖任何外部 API / 网络 / 数据库。
覆盖范围：
  - ResearchOrchestrator._event
  - ResearchConductor section evidence pipeline
  - VerifierService._deterministic_verify / _parse_json
  - ContentExtractionService._extract_content_sync (HTML 清洗，本地字符串)
  - DeepSeekService._truncate_prompt / _build_payload
  - CostTracker / estimate_tokens
  - SourceCurator 可信度评分
"""
from __future__ import annotations

import os
import sqlite3
from unittest.mock import MagicMock

import requests

# ── 避免导入时触发真实 DB / env 初始化 ──────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_logic.db")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

# ── 被测模块 ─────────────────────────────────────────────────────────────────
from backend.app.core.orchestrator import ResearchOrchestrator
from backend.app.models.research_task import Citation
from backend.app.models.research_task import ResearchSection
from backend.app.research.agent import ResearchAgent
from backend.app.research.config import ResearchConfig
from backend.app.research.conductor import ResearchConductor
from backend.app.research.retriever import ResearchRetriever
from backend.app.research.writer import ResearchWriter
from backend.app.research.source_curator import SourceCurator, _score_source
from backend.app.research.models import DeepResearchDecision
from backend.app.research.models import ResearchPlanItem
from backend.app.research.models import ResearchSource
from backend.app.research.models import SubQueryContext
from backend.app.research.query_planner import QueryPlanner
from backend.app.services.content_extraction_service import ContentExtractionService
from backend.app.services.deepseek_service import DeepSeekService
from backend.app.services.evidence_store import EvidenceStore
from backend.app.services.research_repository import ResearchRepository
from backend.app.services.search_tools import SearchTools
from backend.app.services.verifier_service import VerifierService
from backend.app.research.cost_tracker import CostTracker
from backend.app.research.cost_tracker import estimate_tokens


# ═══════════════════════════════════════════════════════════════════
# ResearchOrchestrator
# ═══════════════════════════════════════════════════════════════════

class TestEventHelper:
    orch = ResearchOrchestrator()

    def test_event_contains_all_keys(self):
        event = self.orch._event("planning", "开始规划", {"key": "value"})
        assert event == {"type": "planning", "message": "开始规划", "data": {"key": "value"}}

    def test_event_data_can_be_none(self):
        event = self.orch._event("done", "完成", None)
        assert event["data"] is None

    def test_run_starts_with_task_created_event(self, tmp_path):
        repository = ResearchRepository(str(tmp_path / "research.db"))
        orch = ResearchOrchestrator()
        orch.repository = repository

        import asyncio

        async def first_event():
            stream = orch.run("AI 产业趋势", guest_id="guest-1")
            try:
                return await stream.__anext__()
            finally:
                await stream.aclose()

        event = asyncio.run(first_event())

        assert event["type"] == "task_created"
        assert event["message"] == "研究任务已创建"
        assert event["data"]["status"] == "planning"


class TestResearchConfig:
    def test_config_can_be_loaded_from_environment(self, monkeypatch):
        monkeypatch.setenv("RESEARCH_MAX_SUB_QUERIES", "2")
        monkeypatch.setenv("RESEARCH_MAX_CONCURRENCY", "1")
        monkeypatch.setenv("RESEARCH_MAX_READ_PAGES_PER_SECTION", "4")
        monkeypatch.setenv("RESEARCH_DEEP_RESEARCH_BREADTH", "2")
        monkeypatch.setenv("RESEARCH_DEEP_RESEARCH_DEPTH", "3")
        monkeypatch.setenv("RESEARCH_RETRIEVER", "duckduckgo")
        monkeypatch.setenv("RESEARCH_REPORT_TYPE", "detailed_report")
        monkeypatch.setenv("RESEARCH_TONE", "analytical")
        monkeypatch.setenv("RESEARCH_SOURCE", "web")
        monkeypatch.setenv("RESEARCH_QUERY_DOMAINS", "example.com, docs.example.com")
        monkeypatch.setenv("RESEARCH_SOURCE_URLS", "https://example.com/a")

        config = ResearchConfig.from_env()

        assert config.max_sub_queries == 2
        assert config.max_concurrency == 1
        assert config.max_read_pages_per_section == 4
        assert config.deep_research_breadth == 2
        assert config.deep_research_depth == 3
        assert config.retriever == "duckduckgo"
        assert config.report_type == "detailed_report"
        assert config.tone == "analytical"
        assert config.source == "web"
        assert config.query_domains == ["example.com", "docs.example.com"]
        assert config.source_urls == ["https://example.com/a"]

    def test_agent_uses_environment_config_by_default(self, monkeypatch):
        monkeypatch.setenv("RESEARCH_MAX_SUB_QUERIES", "2")
        monkeypatch.setenv("RESEARCH_MAX_CONCURRENCY", "1")
        monkeypatch.setenv("RESEARCH_RETRIEVER", "duckduckgo")
        monkeypatch.setenv("RESEARCH_REPORT_TYPE", "detailed_report")
        monkeypatch.setenv("RESEARCH_TONE", "analytical")

        agent = ResearchAgent(query="DeepSeek 企业应用")

        assert agent.max_sub_queries == 2
        assert agent.max_concurrency == 1
        assert agent.config.deep_research_depth == 2
        assert agent.config.retriever == "duckduckgo"
        assert agent.config.report_type == "detailed_report"
        assert agent.config.tone == "analytical"


class TestResearchConductor:
    def test_conductor_persists_evidence_and_verification(self, monkeypatch, tmp_path):
        repository = ResearchRepository(str(tmp_path / "research.db"))

        class ResearcherStub:
            def __init__(self, repository: ResearchRepository) -> None:
                self.query = "DeepSeek 企业应用"
                self.max_sub_queries = 1
                self.max_concurrency = 1
                self.cost_tracker = CostTracker()
                self.visited_urls = set()
                self.sub_queries = []
                self.context = []
                self.research_sources = []
                self.plan_items = []
                self.evidence_store = EvidenceStore()
                self.task_id = "task-1"
                self.repository = repository

        conductor = ResearchConductor(ResearcherStub(repository))
        source = ResearchSource(
            title="DeepSeek Case Study",
            link="https://example.com/case-study",
            source="web",
            query="DeepSeek 企业应用案例",
            snippet="DeepSeek 被用于企业知识库和客服自动化。",
            extracted_content="DeepSeek 被用于企业知识库和客服自动化，提升响应速度和准确率。",
        )

        async def fake_search(query: str, max_results: int = 8):  # noqa: ARG001
            return [source]

        async def fake_plan_detailed(**kwargs):  # noqa: ANN003
            return [
                ResearchPlanItem(
                    step=1,
                    title="DeepSeek 企业应用案例",
                    dimension="案例研究",
                    rationale="验证企业应用场景。",
                    search_queries=["DeepSeek 企业应用案例"],
                    expected_outcome="获得企业应用案例。",
                    evidence_targets=["案例研究"],
                )
            ]

        async def fake_scrape(sources, visited_urls, max_sources: int = 8):  # noqa: ANN001, ARG001
            return sources

        async def fake_context(query: str, sources):  # noqa: ANN001, ARG001
            return "企业落地集中在知识库、客服和内部助手场景。"

        async def fake_verify(**kwargs):  # noqa: ANN003
            return {
                "passed": True,
                "score": 0.9,
                "issues": [],
                "summary": "证据足以支持分析",
            }

        monkeypatch.setattr(conductor.retriever, "search", fake_search)
        monkeypatch.setattr(conductor.query_planner, "plan_detailed", fake_plan_detailed)
        monkeypatch.setattr(conductor.scraper, "scrape", fake_scrape)
        monkeypatch.setattr(conductor.context_manager, "get_context", fake_context)
        monkeypatch.setattr(
            "backend.app.research.conductor.verifier_service.verify_section",
            fake_verify,
        )

        import asyncio

        events = []

        async def collect_event(event):  # noqa: ANN001
            events.append(event)

        contexts = asyncio.run(conductor.conduct_research(on_event=collect_event))

        assert len(contexts) == 2
        sub_query_context = contexts[0]
        assert sub_query_context.evidence_ids
        assert sub_query_context.citations[0].title == "DeepSeek Case Study"
        assert "DeepSeek Case Study" in sub_query_context.compressed_evidence
        assert sub_query_context.verification["passed"] is True
        event_types = [event["type"] for event in events]
        assert "workflow_start" in event_types
        assert "search_result" in event_types
        assert "step_start" in event_types
        assert "analysis_progress" in event_types
        assert "step_complete" in event_types

        with sqlite3.connect(repository.db_path) as conn:
            evidence_count = conn.execute(
                "SELECT COUNT(*) FROM evidence_items WHERE task_id = ?",
                ("task-1",),
            ).fetchone()[0]
        assert evidence_count == 2

    def test_conductor_emits_structured_plan_items(self, monkeypatch, caplog):
        class ResearcherStub:
            def __init__(self) -> None:
                self.query = "AI 产业趋势"
                self.max_sub_queries = 1
                self.max_concurrency = 1
                self.cost_tracker = CostTracker()
                self.visited_urls = set()
                self.sub_queries = []
                self.context = []
                self.research_sources = []
                self.evidence_store = EvidenceStore()
                self.task_id = "task-plan"
                self.request_id = "req-plan"
                self.repository = None

        conductor = ResearchConductor(ResearcherStub())
        plan_item = ResearchPlanItem(
            step=1,
            title="AI 产业采用率有哪些最新数据？",
            dimension="数据趋势",
            rationale="需要量化判断市场变化。",
            search_queries=["AI adoption rate 2026 enterprise survey"],
            expected_outcome="获得企业采用率、样本和时间范围。",
            evidence_targets=["统计数据", "行业报告"],
        )

        async def fake_search(query: str, max_results: int = 8):  # noqa: ARG001
            return []

        async def fake_plan_detailed(**kwargs):  # noqa: ANN003
            return [plan_item]

        async def fake_process(step: int, sub_query: str, on_event=None, **kwargs):  # noqa: ANN001, ARG001
            return SubQueryContext(step=step, query=sub_query, context="分析")

        monkeypatch.setattr(conductor.retriever, "search", fake_search)
        monkeypatch.setattr(conductor.query_planner, "plan_detailed", fake_plan_detailed)
        monkeypatch.setattr(conductor, "_process_sub_query", fake_process)

        import asyncio

        events = []

        async def collect_event(event):  # noqa: ANN001
            events.append(event)

        caplog.set_level("INFO", logger="backend.app.research.conductor")
        contexts = asyncio.run(conductor.conduct_research(on_event=collect_event))
        plan_event = next(event for event in events if event["type"] == "plan")
        workflow_event = next(event for event in events if event["type"] == "workflow_start")
        step_start = next(event for event in events if event["type"] == "step_start")
        plan_log = next(
            record
            for record in caplog.records
            if record.getMessage() == "research_plan_created"
        )

        assert contexts[0].query == plan_item.title
        assert workflow_event["data"]["workflow_engine"] == "langgraph"
        assert workflow_event["data"]["nodes"] == [
            "plan_queries",
            "research_queries",
            "curate_sources",
        ]
        assert plan_event["data"]["plan_items"][0]["dimension"] == "数据趋势"
        assert plan_event["data"]["plan_items"][0]["evidence_targets"] == [
            "统计数据",
            "行业报告",
        ]
        assert step_start["data"]["description"] == "数据趋势：需要量化判断市场变化。"
        assert step_start["data"]["queries"] == plan_item.search_queries
        assert plan_log.task_id == "task-plan"
        assert plan_log.request_id == "req-plan"
        assert plan_log.query == "AI 产业趋势"
        assert plan_log.plan_items_count == 2
        assert plan_log.dimensions == ["数据趋势", "核心问题"]
        assert plan_log.search_queries_count == 2

    def test_process_sub_query_searches_planned_queries(self, monkeypatch):
        class ResearcherStub:
            def __init__(self) -> None:
                self.query = "AI 产业采用率有哪些最新数据？"
                self.cost_tracker = CostTracker()
                self.visited_urls = set()
                self.evidence_store = EvidenceStore()
                self.task_id = "task-search-strategy"
                self.repository = None
                self.plan_items = [
                    ResearchPlanItem(
                        step=1,
                        title="AI 产业采用率有哪些最新数据？",
                        search_queries=[
                            "AI adoption rate 2026 enterprise survey",
                            "AI 企业采用率 调研 2026",
                        ],
                    )
                ]
                self.config = ResearchConfig(max_read_pages_per_section=2)

        conductor = ResearchConductor(ResearcherStub())
        searched_queries: list[str] = []

        async def fake_search(query: str, max_results: int = 8):  # noqa: ARG001
            searched_queries.append(query)
            return [
                ResearchSource(
                    title=f"Source {query}",
                    link=f"https://example.com/{len(searched_queries)}",
                    source="web",
                    query=query,
                    snippet="snippet",
                    extracted_content="content",
                )
            ]

        async def fake_scrape(sources, visited_urls, max_sources: int = 8):  # noqa: ANN001, ARG001
            return sources

        async def fake_context(query: str, sources):  # noqa: ANN001, ARG001
            return "压缩后的上下文"

        async def fake_verify(**kwargs):  # noqa: ANN003
            return {"passed": True, "score": 1.0, "issues": [], "summary": "ok"}

        monkeypatch.setattr(conductor.retriever, "search", fake_search)
        monkeypatch.setattr(conductor.scraper, "scrape", fake_scrape)
        monkeypatch.setattr(conductor.context_manager, "get_context", fake_context)
        monkeypatch.setattr(
            "backend.app.research.conductor.verifier_service.verify_section",
            fake_verify,
        )

        import asyncio

        context = asyncio.run(
            conductor._process_sub_query(
                1,
                "AI 产业采用率有哪些最新数据？",
            )
        )

        assert searched_queries == [
            "AI adoption rate 2026 enterprise survey",
            "AI 企业采用率 调研 2026",
        ]
        assert [source.query for source in context.sources] == searched_queries
        assert context.source_summary["read_count"] == 2
        assert context.source_summary["cited_count"] == 2
        assert all(source.status == "cited" for source in context.sources)

    def test_process_sub_query_emits_process_metrics(self, monkeypatch):
        class ResearcherStub:
            def __init__(self) -> None:
                self.query = "AI 产业采用率有哪些最新数据？"
                self.cost_tracker = CostTracker()
                self.visited_urls = set()
                self.evidence_store = EvidenceStore()
                self.task_id = "task-process-metrics"
                self.repository = None
                self.plan_items = [
                    ResearchPlanItem(
                        step=1,
                        title="AI 产业采用率有哪些最新数据？",
                        search_queries=["AI adoption rate", "AI adoption survey"],
                    )
                ]
                self.config = ResearchConfig(max_read_pages_per_section=3)

        conductor = ResearchConductor(ResearcherStub())
        events: list[dict[str, object]] = []

        async def collect_event(event: dict[str, object]) -> None:
            events.append(event)

        async def fake_search(query: str, max_results: int = 8):  # noqa: ARG001
            return [
                ResearchSource(
                    title=f"Source {query}",
                    link=f"https://example.com/{query.replace(' ', '-')}",
                    source="web",
                    query=query,
                    snippet="snippet",
                    extracted_content="content",
                )
            ]

        async def fake_scrape(sources, visited_urls, max_sources: int = 8):  # noqa: ANN001, ARG001
            for source in sources:
                source.status = "read"
            return sources

        async def fake_context(query: str, sources):  # noqa: ANN001, ARG001
            return "压缩后的上下文"

        async def fake_verify(**kwargs):  # noqa: ANN003
            return {"passed": True, "score": 1.0, "issues": [], "summary": "ok"}

        monkeypatch.setattr(conductor.retriever, "search", fake_search)
        monkeypatch.setattr(conductor.scraper, "scrape", fake_scrape)
        monkeypatch.setattr(conductor.context_manager, "get_context", fake_context)
        monkeypatch.setattr(
            "backend.app.research.conductor.verifier_service.verify_section",
            fake_verify,
        )

        import asyncio

        context = asyncio.run(
            conductor._process_sub_query(
                1,
                "AI 产业采用率有哪些最新数据？",
                collect_event,
            )
        )

        metric_events = [event for event in events if event["type"] == "metrics_update"]
        assert metric_events
        final_metrics = metric_events[-1]["data"]
        assert isinstance(final_metrics, dict)
        assert final_metrics["search_count"] == 2
        assert final_metrics["selected_source_count"] == 2
        assert final_metrics["read_count"] == 2
        assert final_metrics["cited_source_count"] == len(context.citations)
        assert final_metrics["elapsed_seconds"] >= 0
        assert "estimated_cost_usd" in final_metrics

    def test_conductor_uses_confirmed_plan_items(self, monkeypatch):
        class ResearcherStub:
            def __init__(self) -> None:
                self.query = "AI 产业趋势"
                self.max_sub_queries = 3
                self.max_concurrency = 1
                self.config = ResearchConfig()
                self.cost_tracker = CostTracker()
                self.visited_urls = set()
                self.sub_queries = []
                self.context = []
                self.research_sources = []
                self.evidence_store = EvidenceStore()
                self.task_id = "task-confirmed-plan"
                self.repository = None
                self.confirmed_plan_items = [
                    ResearchPlanItem(
                        step=9,
                        title="AI 产业采用率",
                        dimension="数据趋势",
                        rationale="需要量化趋势。",
                        search_queries=["AI adoption survey"],
                        expected_outcome="获得采用率数据。",
                        evidence_targets=["统计数据"],
                    )
                ]

        conductor = ResearchConductor(ResearcherStub())
        monkeypatch.setattr(
            conductor.retriever,
            "search",
            MagicMock(side_effect=AssertionError("confirmed plan should skip planning search")),
        )

        async def fake_process_query_tree(**kwargs):  # noqa: ANN003
            return [
                SubQueryContext(
                    step=kwargs["step"],
                    query=kwargs["query"],
                    context="confirmed context",
                )
            ]

        monkeypatch.setattr(conductor, "_process_query_tree", fake_process_query_tree)

        import asyncio

        contexts = asyncio.run(conductor.conduct_research())

        plan_items = getattr(conductor.researcher, "plan_items")
        assert [item.title for item in plan_items] == [
            "AI 产业采用率",
            "AI 产业趋势",
        ]
        assert plan_items[0].step == 1
        assert contexts[0].query == "AI 产业采用率"

    def test_process_sub_query_honors_read_budget_and_reports_failures(self, monkeypatch):
        class ResearcherStub:
            """Minimal researcher for source lifecycle tests."""

            def __init__(self) -> None:
                self.query = "AI evidence quality"
                self.cost_tracker = CostTracker()
                self.visited_urls = set()
                self.evidence_store = EvidenceStore()
                self.task_id = "task-source-summary"
                self.repository = None
                self.config = ResearchConfig(max_read_pages_per_section=1)
                self.plan_items = [
                    ResearchPlanItem(
                        step=1,
                        title="AI evidence quality",
                        search_queries=["AI evidence quality"],
                    )
                ]

        conductor = ResearchConductor(ResearcherStub())

        async def fake_search(query: str, max_results: int = 8):  # noqa: ARG001
            return [
                ResearchSource(
                    title="Readable source",
                    link="https://example.com/readable",
                    source="web",
                    query=query,
                    snippet="source with enough useful evidence",
                    extracted_content="",
                ),
                ResearchSource(
                    title="Over budget source",
                    link="https://example.com/over-budget",
                    source="web",
                    query=query,
                    snippet="source outside read budget",
                    extracted_content="",
                ),
            ]

        async def fake_extract(link: str):
            return "" if link.endswith("readable") else "unexpected"

        async def fake_context(query: str, sources):  # noqa: ANN001, ARG001
            return "压缩后的上下文"

        async def fake_verify(**kwargs):  # noqa: ANN003
            return {"passed": False, "score": 0.5, "issues": ["empty"], "summary": "gap"}

        monkeypatch.setattr(conductor.retriever, "search", fake_search)
        monkeypatch.setattr(
            "backend.app.research.scraper.content_extraction_service.extract_content",
            fake_extract,
        )
        monkeypatch.setattr(conductor.context_manager, "get_context", fake_context)
        monkeypatch.setattr(
            "backend.app.research.conductor.verifier_service.verify_section",
            fake_verify,
        )

        import asyncio

        context = asyncio.run(conductor._process_sub_query(1, "AI evidence quality"))

        assert len(context.sources) == 1
        assert context.sources[0].status == "failed"
        assert context.sources[0].failure_reason == "empty_content"
        assert context.source_summary["failed_count"] == 1
        assert context.source_summary["read_count"] == 0

    def test_process_sub_query_filters_sources_by_evidence_targets(self, monkeypatch):
        class ResearcherStub:
            def __init__(self) -> None:
                self.query = "AI 产业趋势"
                self.cost_tracker = CostTracker()
                self.visited_urls = set()
                self.evidence_store = EvidenceStore()
                self.task_id = "task-target-quality"
                self.repository = None
                self.plan_items = [
                    ResearchPlanItem(
                        step=1,
                        title="AI 产业采用率有哪些最新数据？",
                        search_queries=["AI adoption rate"],
                        evidence_targets=["统计数据", "行业报告"],
                    )
                ]

        conductor = ResearchConductor(ResearcherStub())
        scraped_titles: list[str] = []

        async def fake_search(query: str, max_results: int = 8):  # noqa: ARG001
            return [
                ResearchSource(
                    title="Personal hot take",
                    link="https://random-blog.xyz/ai-opinion",
                    snippet="AI adoption feels faster this year.",
                    extracted_content="Opinion " * 80,
                ),
                ResearchSource(
                    title="Enterprise AI adoption survey report 2026",
                    link="https://example.org/reports/ai-adoption-survey-2026.pdf",
                    snippet="Survey data from 2,000 enterprises reports adoption rate and sample size.",
                    extracted_content="statistics data adoption rate sample size " * 40,
                ),
            ]

        async def fake_scrape(sources, visited_urls, max_sources: int = 8):  # noqa: ANN001, ARG001
            scraped_titles.extend(source.title for source in sources)
            return sources

        async def fake_context(query: str, sources):  # noqa: ANN001, ARG001
            return "压缩后的上下文"

        async def fake_verify(**kwargs):  # noqa: ANN003
            return {"passed": True, "score": 1.0, "issues": [], "summary": "ok"}

        monkeypatch.setattr(conductor.retriever, "search", fake_search)
        monkeypatch.setattr(conductor.scraper, "scrape", fake_scrape)
        monkeypatch.setattr(conductor.context_manager, "get_context", fake_context)
        monkeypatch.setattr(
            "backend.app.research.conductor.verifier_service.verify_section",
            fake_verify,
        )

        import asyncio

        context = asyncio.run(
            conductor._process_sub_query(
                1,
                "AI 产业采用率有哪些最新数据？",
            )
        )

        assert scraped_titles == ["Enterprise AI adoption survey report 2026"]
        assert [source.title for source in context.sources] == scraped_titles

    def test_conductor_runs_deeper_query_when_evidence_has_gaps(
        self,
        monkeypatch,
        caplog,
    ):
        class ResearcherStub:
            def __init__(self) -> None:
                self.query = "AI 产业采用率有哪些最新数据？"
                self.max_sub_queries = 1
                self.max_concurrency = 1
                self.config = ResearchConfig(
                    deep_research_breadth=1,
                    deep_research_depth=2,
                )
                self.cost_tracker = CostTracker()
                self.visited_urls = set()
                self.sub_queries = []
                self.context = []
                self.research_sources = []
                self.evidence_store = EvidenceStore()
                self.task_id = "task-deep"
                self.request_id = "req-deep"
                self.repository = None

        conductor = ResearchConductor(ResearcherStub())
        caplog.set_level("INFO", logger="backend.app.research.conductor")
        plan_item = ResearchPlanItem(
            step=1,
            title="AI 产业采用率有哪些最新数据？",
            dimension="数据趋势",
            rationale="需要量化判断市场变化。",
            search_queries=["AI adoption rate 2026 enterprise survey"],
            expected_outcome="获得企业采用率、样本和时间范围。",
            evidence_targets=["统计数据", "行业报告"],
        )
        searched_queries: list[str] = []

        async def fake_initial_plan(**kwargs):  # noqa: ANN003
            return [plan_item]

        async def fake_deeper_plan(**kwargs):  # noqa: ANN003
            return DeepResearchDecision(
                should_continue=True,
                reason="缺少分行业样本。",
                evidence_gaps=["缺少制造业样本"],
                follow_up_queries=["AI adoption manufacturing survey 2026"],
                stop_condition="补足分行业样本或达到最大深度",
            )

        async def fake_search(query: str, max_results: int = 8):  # noqa: ARG001
            searched_queries.append(query)
            return [
                ResearchSource(
                    title=f"Survey {query}",
                    link=f"https://example.com/{len(searched_queries)}",
                    source="web",
                    query=query,
                    snippet="survey data sample size adoption rate",
                    extracted_content="survey data sample size adoption rate " * 20,
                )
            ]

        async def fake_scrape(sources, visited_urls, max_sources: int = 8):  # noqa: ANN001, ARG001
            return sources

        async def fake_context(query: str, sources):  # noqa: ANN001, ARG001
            return f"分析：{query}"

        async def fake_verify(**kwargs):  # noqa: ANN003
            return {"passed": False, "score": 0.5, "issues": ["缺少行业细分"], "summary": "gap"}

        monkeypatch.setattr(conductor.retriever, "search", fake_search)
        monkeypatch.setattr(conductor.query_planner, "plan_detailed", fake_initial_plan)
        monkeypatch.setattr(conductor.query_planner, "plan_deeper_research", fake_deeper_plan)
        monkeypatch.setattr(conductor.scraper, "scrape", fake_scrape)
        monkeypatch.setattr(conductor.context_manager, "get_context", fake_context)
        monkeypatch.setattr(
            "backend.app.research.conductor.verifier_service.verify_section",
            fake_verify,
        )

        import asyncio

        events = []

        async def collect_event(event):  # noqa: ANN001
            events.append(event)

        contexts = asyncio.run(conductor.conduct_research(on_event=collect_event))

        assert [context.query for context in contexts] == [
            "AI 产业采用率有哪些最新数据？",
            "AI adoption manufacturing survey 2026",
        ]
        assert contexts[0].deep_research.reason == "缺少分行业样本。"
        assert contexts[1].depth == 2
        assert contexts[1].parent_query == "AI 产业采用率有哪些最新数据？"
        decision_event = next(
            event for event in events if event["type"] == "deep_research_decision"
        )
        assert decision_event["data"]["reason"] == "缺少分行业样本。"
        assert decision_event["data"]["evidence_gaps"] == ["缺少制造业样本"]
        assert decision_event["data"]["follow_up_queries"] == [
            "AI adoption manufacturing survey 2026"
        ]
        logged_messages = [record.getMessage() for record in caplog.records]
        assert "step_start" in logged_messages
        assert "deep_research_decision" in logged_messages
        assert "step_complete" in logged_messages
        decision_log = next(
            record
            for record in caplog.records
            if record.getMessage() == "deep_research_decision"
        )
        assert decision_log.task_id == "task-deep"
        assert decision_log.request_id == "req-deep"
        assert decision_log.should_continue is True
        assert decision_log.evidence_gaps == ["缺少制造业样本"]
        assert decision_log.follow_up_queries == [
            "AI adoption manufacturing survey 2026"
        ]
        child_start_log = next(
            record
            for record in caplog.records
            if record.getMessage() == "step_start" and record.step == 101
        )
        assert child_start_log.parent_query == "AI 产业采用率有哪些最新数据？"
        assert child_start_log.request_id == "req-deep"


class TestQueryPlanner:
    def test_plan_detailed_parses_structured_research_strategy(self, monkeypatch):
        planner = QueryPlanner()
        initial_results = [
            ResearchSource(
                title="AI Market Report",
                link="https://example.com/report",
                source="web",
                query="AI 产业趋势",
                snippet="报告提到企业采用、成本和风险。",
            )
        ]

        async def fake_llm_call(self, prompt: str):  # noqa: ANN001, ARG001
            return """
            {
              "plan_items": [
                {
                  "title": "AI 产业采用率有哪些最新数据？",
                  "dimension": "数据趋势",
                  "rationale": "需要量化判断市场变化。",
                  "search_queries": ["AI adoption rate 2026 enterprise survey"],
                  "expected_outcome": "获得企业采用率、样本和时间范围。",
                  "evidence_targets": ["统计数据", "行业报告"]
                }
              ]
            }
            """

        monkeypatch.setattr(planner.llm.__class__, "_acall", fake_llm_call)

        import asyncio

        plan_items = asyncio.run(
            planner.plan_detailed(
                query="AI 产业趋势",
                initial_results=initial_results,
                max_sub_queries=3,
            )
        )
        legacy_queries = asyncio.run(
            planner.plan(
                query="AI 产业趋势",
                initial_results=initial_results,
                max_sub_queries=3,
            )
        )

        assert plan_items == [
            ResearchPlanItem(
                step=1,
                title="AI 产业采用率有哪些最新数据？",
                dimension="数据趋势",
                rationale="需要量化判断市场变化。",
                search_queries=["AI adoption rate 2026 enterprise survey"],
                expected_outcome="获得企业采用率、样本和时间范围。",
                evidence_targets=["统计数据", "行业报告"],
            )
        ]
        assert legacy_queries == ["AI 产业采用率有哪些最新数据？"]

    def test_plan_deeper_research_parses_reason_gaps_and_stop_condition(self, monkeypatch):
        planner = QueryPlanner()
        plan_item = ResearchPlanItem(
            step=1,
            title="AI 产业采用率有哪些最新数据？",
            dimension="数据趋势",
            rationale="需要量化判断市场变化。",
            search_queries=["AI adoption rate 2026 enterprise survey"],
            expected_outcome="获得企业采用率、样本和时间范围。",
            evidence_targets=["统计数据", "行业报告"],
        )
        response = """
        {
          "should_continue": true,
          "reason": "现有资料缺少分行业采用率。",
          "evidence_gaps": ["缺少制造业样本", "缺少金融业样本"],
          "follow_up_queries": [
            "2026 AI adoption rate manufacturing survey",
            "2026 AI adoption rate financial services survey"
          ],
          "stop_condition": "拿到分行业样本数据或达到最大深度"
        }
        """

        async def fake_acall(self, prompt: str, temperature: float = 0.2):  # noqa: ARG001
            return response

        monkeypatch.setattr(
            "backend.app.llms.deepseek_llm.DeepSeekLLM._acall",
            fake_acall,
        )

        import asyncio

        decision = asyncio.run(
            planner.plan_deeper_research(
                query=plan_item.title,
                plan_item=plan_item,
                compressed_evidence="报告只给出了总体采用率。",
                verification={"passed": False, "issues": ["缺少行业细分"]},
                max_follow_up_queries=2,
            )
        )

        assert decision.should_continue is True
        assert decision.reason == "现有资料缺少分行业采用率。"
        assert decision.evidence_gaps == ["缺少制造业样本", "缺少金融业样本"]
        assert decision.follow_up_queries == [
            "2026 AI adoption rate manufacturing survey",
            "2026 AI adoption rate financial services survey",
        ]
        assert decision.stop_condition == "拿到分行业样本数据或达到最大深度"


class TestResearchWriter:
    def test_writer_includes_report_type_and_tone_in_prompt(self, monkeypatch):
        captured_prompt = ""
        writer = ResearchWriter(
            config=ResearchConfig(
                report_type="detailed_report",
                tone="analytical",
            )
        )

        async def fake_llm_call(self, prompt: str, **kwargs):  # noqa: ANN001, ARG001
            nonlocal captured_prompt
            captured_prompt = prompt
            return "# report"

        monkeypatch.setattr(writer.llm.__class__, "_acall", fake_llm_call)

        import asyncio

        report = asyncio.run(
            writer.write_report(
                query="DeepSeek",
                sections=[],
                context=[],
                sources=[],
            )
        )

        assert report == "# report\n\n## 8. 参考来源\n\n无可引用来源。"
        assert "报告类型：detailed_report" in captured_prompt
        assert "语气：analytical" in captured_prompt

    def test_format_context_prefers_sections_with_verification_and_evidence(self):
        writer = ResearchWriter()
        sections = [
            ResearchSection(
                id="subquery-1",
                step=1,
                title="DeepSeek 企业应用案例",
                description="desc",
                status="completed",
                analysis="企业应用集中在知识库和客服。",
                compressed_evidence="研究主题: DeepSeek 企业应用案例\n- [web] DeepSeek Case Study",
                verification={
                    "passed": True,
                    "score": 0.92,
                    "summary": "证据充分",
                },
                citations=[
                    Citation(
                        title="DeepSeek Case Study",
                        link="https://example.com/case",
                        source="web",
                    )
                ],
            )
        ]
        reference_entries = writer._collect_reference_entries([], sections, [])
        formatted = writer._format_context(
            sections,
            [],
            writer._build_source_index(reference_entries),
        )

        assert "校验: 通过 | score=0.92 | 证据充分" in formatted
        assert "证据压缩" in formatted
        assert "[1] DeepSeek Case Study: https://example.com/case" in formatted
        assert "企业应用集中在知识库和客服。" in formatted

    def test_collect_reference_entries_merges_sources_and_section_citations(self):
        writer = ResearchWriter()
        sections = [
            ResearchSection(
                id="subquery-1",
                step=1,
                title="DeepSeek 企业应用案例",
                description="desc",
                citations=[
                    Citation(
                        title="Section Source",
                        link="https://example.com/section",
                        source="web",
                    )
                ],
            )
        ]
        sources = [
            ResearchSource(
                title="Primary Source",
                link="https://example.com/primary",
            )
        ]

        entries = writer._collect_reference_entries(sources, sections, [])
        index = writer._build_source_index(entries)

        assert entries == [
            {
                "title": "Primary Source",
                "link": "https://example.com/primary",
            },
            {
                "title": "Section Source",
                "link": "https://example.com/section",
            },
        ]
        assert index["https://example.com/primary"] == 1
        assert index["https://example.com/section"] == 2

    def test_writer_replaces_hallucinated_reference_section(self, monkeypatch):
        writer = ResearchWriter()
        sources = [
            ResearchSource(
                title="国家数据局区块链供应链金融案例",
                link="https://www.nda.gov.cn/sjj/ywpd/zcgh/0708/case.html",
            ),
            ResearchSource(
                title="IBM Food Trust documentation",
                link="https://www.ibm.com/food-trust",
            ),
        ]
        malformed_report = """# 区块链供应链研究

## 7. 结论与建议
区块链供应链项目需要重点核验落地案例。

## 8. 参考来源
[6] 国家数据局区块链供应链金融案例 - https://www.nda.gov.cn/sjj/ywpd/zcgh/0708/case.html
[6] 2024-2025年全球区块链供应链金融平台的实际落地案例与风险事件 - 研究上下文
[6] 供应链区块链联盟失败的原因与教训 - 研究上下文
"""

        async def fake_llm_call(self, prompt: str, **kwargs):  # noqa: ANN001, ARG001
            return malformed_report

        monkeypatch.setattr(writer.llm.__class__, "_acall", fake_llm_call)

        import asyncio

        report = asyncio.run(
            writer.write_report(
                query="区块链供应链",
                sections=[],
                context=[],
                sources=sources,
            )
        )

        assert "- [1] 国家数据局区块链供应链金融案例 - https://www.nda.gov.cn/sjj/ywpd/zcgh/0708/case.html" in report
        assert "- [2] IBM Food Trust documentation - https://www.ibm.com/food-trust" in report
        assert "[6] 2024-2025年全球区块链供应链金融平台的实际落地案例与风险事件 - 研究上下文" not in report
        assert report.count("[6]") == 0

    def test_fallback_report_separates_source_lines(self):
        writer = ResearchWriter()
        report = writer._fallback_report(
            query="DeepSeek",
            sections=[],
            context=[],
            sources=[
                ResearchSource(title="A", link="https://example.com/a"),
                ResearchSource(title="B", link="https://example.com/b"),
            ],
        )

        assert "- [1] A: https://example.com/a\n- [2] B: https://example.com/b" in report

    def test_evaluate_claim_support_flags_unsupported_claims(self):
        writer = ResearchWriter()
        report = "\n".join(
            [
                "# 报告",
                "企业 AI 采用率在样本企业中持续上升 [1]。",
                "该趋势已经覆盖所有行业。",
                "预算增长来自缺失的引用 [9]。",
                "## 8. 参考来源",
                "- [1] Enterprise AI Survey - https://example.com/survey",
            ]
        )

        import asyncio

        result = asyncio.run(writer.evaluate_claim_support(
            report,
            [{"title": "Enterprise AI Survey", "link": "https://example.com/survey"}],
        ))
        summary = result["summary"]
        claims = result["claims"]

        assert isinstance(summary, dict)
        assert isinstance(claims, list)
        assert summary["claim_count"] == 3
        assert summary["supported_claim_count"] == 1
        assert summary["unsupported_claim_count"] == 2
        assert summary["citation_support_rate"] == 0.3333
        assert claims[0]["citation_support"] == "supported"
        assert claims[1]["citation_support"] == "unsupported"
        assert claims[2]["reason"] == "缺少有效引用编号"

    def test_evaluate_claim_support_marks_partial_citations(self):
        writer = ResearchWriter()
        import asyncio

        result = asyncio.run(writer.evaluate_claim_support(
            "国产量子计算原型机公开了阶段性指标 [1][3]。",
            [{"title": "Quantum Source", "link": "https://example.com/quantum"}],
        ))
        summary = result["summary"]
        claims = result["claims"]

        assert isinstance(summary, dict)
        assert isinstance(claims, list)
        assert summary["partially_supported_claim_count"] == 1
        assert summary["citation_support_rate"] == 0.5
        assert claims[0]["citation_support"] == "partially_supported"
        assert claims[0]["citation_numbers"] == [1, 3]

    def test_evaluate_claim_support_uses_semantic_llm_judgment(self, monkeypatch):
        writer = ResearchWriter()
        prompts: list[str] = []

        async def fake_acall(prompt: str, **kwargs):  # noqa: ANN003, ARG001
            prompts.append(prompt)
            return (
                '{"claims": ['
                '{"claim_index": 0, "citation_support": "unsupported", '
                '"reason": "来源只说明收入下降，不能支撑收入增长。"}'
                ']}'
            )

        monkeypatch.setattr(writer.llm, "_acall", fake_acall)

        import asyncio

        result = asyncio.run(writer.evaluate_claim_support(
            "公司收入同比增长 30% [1]。",
            [
                {
                    "title": "财报",
                    "link": "https://example.com/report",
                    "source_text": "财报显示，公司收入同比下降 10%。",
                }
            ],
        ))
        claims = result["claims"]

        assert prompts
        assert isinstance(claims, list)
        assert claims[0]["citation_support"] == "unsupported"
        assert claims[0]["reason"] == "来源只说明收入下降，不能支撑收入增长。"


class TestSearchTools:
    def test_google_search_uses_thread_offload(self, monkeypatch):
        search_tools = SearchTools()
        search_tools.serpapi_key = "test-serpapi"

        async def fake_to_thread(func, *args, **kwargs):  # noqa: ANN001
            return func(*args, **kwargs)

        monkeypatch.setattr("backend.app.services.search_tools.asyncio.to_thread", fake_to_thread)
        monkeypatch.setattr(
            search_tools,
            "_sync_google_search",
            MagicMock(return_value=[{"title": "A", "link": "https://a.com"}]),
        )

        import asyncio

        result = asyncio.run(search_tools.google_search("DeepSeek"))

        search_tools._sync_google_search.assert_called_once_with("DeepSeek", 10)
        assert result == [{"title": "A", "link": "https://a.com"}]

    def test_tavily_transport_failure_logs_warning_without_traceback(
        self, monkeypatch, caplog
    ):
        search_tools = SearchTools()
        search_tools.tavily_api_key = "test-tavily"

        async def fake_to_thread(func, *args, **kwargs):  # noqa: ANN001
            return func(*args, **kwargs)

        def fail_search(query: str, num_results: int):  # noqa: ARG001
            raise requests.exceptions.SSLError("tls eof")

        import asyncio

        monkeypatch.setattr("backend.app.services.search_tools.asyncio.to_thread", fake_to_thread)
        monkeypatch.setattr(search_tools, "_sync_tavily_search", fail_search)
        caplog.set_level("WARNING", logger="backend.app.services.search_tools")

        result = asyncio.run(search_tools.tavily_search("DeepSeek"))

        assert result == []
        warning_logs = [
            record
            for record in caplog.records
            if record.getMessage().startswith("Tavily search failed")
        ]
        assert len(warning_logs) == 1
        assert warning_logs[0].exc_info is None

    def test_comprehensive_search_falls_back_when_tavily_returns_empty(
        self, monkeypatch
    ):
        search_tools = SearchTools()
        search_tools.tavily_api_key = "test-tavily"
        search_tools.serpapi_key = None

        async def empty_tavily(query: str, num_results: int = 10):  # noqa: ARG001
            return []

        async def fake_duckduckgo(query: str, num_results: int = 10):  # noqa: ARG001
            return [
                {
                    "title": "Fallback",
                    "link": "https://example.com/fallback",
                    "snippet": "fallback result",
                    "source": "duckduckgo",
                }
            ]

        import asyncio

        monkeypatch.setattr(search_tools, "tavily_search", empty_tavily)
        monkeypatch.setattr(search_tools, "duckduckgo_search", fake_duckduckgo)

        result = asyncio.run(search_tools.comprehensive_search("DeepSeek"))

        assert result["web"] == [
            {
                "title": "Fallback",
                "link": "https://example.com/fallback",
                "snippet": "fallback result",
                "source": "duckduckgo",
            }
        ]


class TestResearchRetriever:
    def test_retriever_uses_selected_backend_and_filters_domains(self, monkeypatch):
        retriever = ResearchRetriever(
            config=ResearchConfig(
                retriever="duckduckgo",
                query_domains=["allowed.com"],
            )
        )

        async def fake_duckduckgo_search(query: str, num_results: int = 10):  # noqa: ARG001
            return [
                {
                    "title": "Allowed",
                    "link": "https://allowed.com/article",
                    "snippet": "allowed result",
                    "source": "duckduckgo",
                },
                {
                    "title": "Blocked",
                    "link": "https://blocked.com/article",
                    "snippet": "blocked result",
                    "source": "duckduckgo",
                },
            ]

        async def fail_comprehensive_search(query: str):  # noqa: ARG001
            raise AssertionError("comprehensive search should not run")

        monkeypatch.setattr(
            "backend.app.research.retriever.search_tools.duckduckgo_search",
            fake_duckduckgo_search,
        )
        monkeypatch.setattr(
            "backend.app.research.retriever.search_tools.comprehensive_search",
            fail_comprehensive_search,
        )

        import asyncio

        results = asyncio.run(retriever.search("DeepSeek"))

        assert [source.link for source in results] == ["https://allowed.com/article"]
        assert results[0].source == "duckduckgo"

    def test_retriever_uses_configured_source_urls_without_search(self, monkeypatch):
        retriever = ResearchRetriever(
            config=ResearchConfig(
                source_urls=["https://example.com/a"],
            )
        )

        async def fail_comprehensive_search(query: str):  # noqa: ARG001
            raise AssertionError("search should not run when explicit sources fill limit")

        monkeypatch.setattr(
            "backend.app.research.retriever.search_tools.comprehensive_search",
            fail_comprehensive_search,
        )

        import asyncio

        results = asyncio.run(retriever.search("DeepSeek", max_results=1))

        assert len(results) == 1
        assert results[0].link == "https://example.com/a"
        assert results[0].source == "configured_url"


# ═══════════════════════════════════════════════════════════════════
# SourceCurator — 可信度评分
# ═══════════════════════════════════════════════════════════════════

class TestScoreSource:
    def test_gov_domain_gets_high_score(self):
        source = ResearchSource(title="T", link="https://data.gov.cn/report", snippet="s" * 60, extracted_content="c" * 300)
        score = _score_source(source)
        assert score >= 0.7

    def test_academic_domain_gets_high_score(self):
        source = ResearchSource(title="T", link="https://arxiv.org/abs/1234", snippet="s" * 60, extracted_content="c" * 300)
        score = _score_source(source)
        assert score >= 0.7

    def test_social_media_gets_low_score(self):
        source = ResearchSource(title="T", link="https://reddit.com/r/test", snippet="s" * 60, extracted_content="c" * 300)
        score = _score_source(source)
        assert score < 0.5

    def test_empty_link_returns_zero(self):
        source = ResearchSource(title="T", link="", snippet="s")
        assert _score_source(source) == 0.0

    def test_authoritative_media_gets_bonus(self):
        source = ResearchSource(title="T", link="https://www.reuters.com/article/123", snippet="s" * 60, extracted_content="c" * 300)
        score = _score_source(source)
        assert score >= 0.7

    def test_no_content_slightly_lower(self):
        source_with = ResearchSource(title="T", link="https://example.com/a", snippet="s" * 60, extracted_content="c" * 300)
        source_without = ResearchSource(title="T", link="https://example.com/b", snippet="short", extracted_content="")
        assert _score_source(source_with) > _score_source(source_without)


class TestSourceCurator:
    curator = SourceCurator()

    def test_deduplicates_by_link(self):
        sources = [
            ResearchSource(title="A", link="https://a.com", snippet="content"),
            ResearchSource(title="A2", link="https://a.com", snippet="other"),
        ]
        result = self.curator.curate(sources)
        assert len(result) == 1

    def test_filters_empty_link(self):
        sources = [
            ResearchSource(title="A", link="", snippet="content"),
        ]
        result = self.curator.curate(sources)
        assert len(result) == 0

    def test_respects_max_sources(self):
        sources = [
            ResearchSource(title=f"T{i}", link=f"https://{i}.com", snippet="s" * 60, extracted_content="c" * 300)
            for i in range(20)
        ]
        result = self.curator.curate(sources, max_sources=5)
        assert len(result) == 5

    def test_sorts_by_credibility(self):
        sources = [
            ResearchSource(title="Reddit", link="https://reddit.com/r/test", snippet="s" * 60, extracted_content="c" * 300),
            ResearchSource(title="Gov", link="https://stats.gov.cn/data", snippet="s" * 60, extracted_content="c" * 300),
            ResearchSource(title="Random", link="https://random-blog.xyz/post", snippet="s" * 60, extracted_content="c" * 300),
        ]
        result = self.curator.curate(sources)
        # Gov should be first
        assert "gov.cn" in result[0].link

    def test_evidence_targets_prefer_matching_source_types(self):
        sources = [
            ResearchSource(
                title="Personal hot take",
                link="https://random-blog.xyz/ai-opinion",
                snippet="AI adoption feels faster this year.",
                extracted_content="Opinion " * 80,
            ),
            ResearchSource(
                title="Enterprise AI adoption survey report 2026",
                link="https://example.org/reports/ai-adoption-survey-2026.pdf",
                snippet="Survey data from 2,000 enterprises reports adoption rate and sample size.",
                extracted_content="statistics data adoption rate sample size " * 40,
            ),
            ResearchSource(
                title="Social thread",
                link="https://reddit.com/r/ai/comments/1",
                snippet="People discuss AI adoption.",
                extracted_content="discussion " * 80,
            ),
        ]

        result = self.curator.curate(
            sources,
            max_sources=2,
            evidence_targets=["统计数据", "行业报告"],
        )

        assert [source.title for source in result] == [
            "Enterprise AI adoption survey report 2026"
        ]


# ═══════════════════════════════════════════════════════════════════
# VerifierService
# ═══════════════════════════════════════════════════════════════════

class TestDeterministicVerify:
    svc = VerifierService()

    def _verify(self, analysis="ok", citations=None, evidence="ev " * 30):
        if citations is None:
            citations = [
                Citation(title="A", link="https://a.com", source="web"),
                Citation(title="B", link="https://b.com", source="web"),
            ]
        return self.svc._deterministic_verify(
            analysis=analysis, citations=citations, compressed_evidence=evidence
        )

    def test_passes_when_all_conditions_met(self):
        result = self._verify()
        assert result["passed"] is True
        assert result["issues"] == []
        assert result["score"] == 1.0
        assert result["method"] == "deterministic_fallback"

    def test_fails_on_empty_analysis(self):
        result = self._verify(analysis="")
        assert result["passed"] is False
        assert any("分析" in issue for issue in result["issues"])

    def test_fails_on_fewer_than_two_citations(self):
        result = self._verify(citations=[Citation(title="A", link="https://a.com", source="web")])
        assert result["passed"] is False
        assert any("来源" in issue for issue in result["issues"])

    def test_fails_on_short_evidence(self):
        result = self._verify(evidence="short")
        assert result["passed"] is False
        assert any("证据" in issue for issue in result["issues"])

    def test_score_decreases_with_more_issues(self):
        r_zero = self._verify()
        r_one  = self._verify(analysis="")
        r_two  = self._verify(analysis="", citations=[])
        assert r_zero["score"] > r_one["score"] > r_two["score"]


class TestParseJson:
    svc = VerifierService()

    def test_parses_plain_json(self):
        raw = '{"passed": true, "score": 0.9}'
        result = self.svc._parse_json(raw)
        assert result["passed"] is True

    def test_parses_fenced_json(self):
        raw = "```json\n{\"passed\": false}\n```"
        result = self.svc._parse_json(raw)
        assert result["passed"] is False

    def test_returns_none_on_invalid_json(self):
        assert self.svc._parse_json("not json") is None

    def test_returns_none_when_root_is_list(self):
        assert self.svc._parse_json("[1, 2, 3]") is None


# ═══════════════════════════════════════════════════════════════════
# EvidenceStore
# ═══════════════════════════════════════════════════════════════════

class TestEvidenceStore:
    def test_add_many_uses_configurable_extraction_limit(self, monkeypatch):
        """Missing source content is fetched only within the read budget."""
        store = EvidenceStore()
        extracted_links: list[str] = []

        async def fake_extract(link: str):
            extracted_links.append(link)
            return f"content for {link}"

        monkeypatch.setattr(
            "backend.app.services.evidence_store.content_extraction_service.extract_content",
            fake_extract,
        )

        import asyncio

        evidence_ids = asyncio.run(
            store.add_many(
                section_id="section-1",
                query="AI evidence",
                source_type="web",
                extraction_limit=1,
                items=[
                    {"title": "A", "link": "https://a.com", "snippet": "a"},
                    {"title": "B", "link": "https://b.com", "snippet": "b"},
                ],
            )
        )
        evidence = store.get_many(evidence_ids)

        assert extracted_links == ["https://a.com"]
        assert evidence[0].extracted_content == "content for https://a.com"
        assert evidence[1].extracted_content == ""


# ═══════════════════════════════════════════════════════════════════
# ContentExtractionService — HTML 清洗（无网络）
# ═══════════════════════════════════════════════════════════════════

class TestContentExtraction:
    svc = ContentExtractionService()

    def _mock_response(self, monkeypatch, html: str, content_type: str = "text/html"):
        import requests

        class FakeResponse:
            status_code = 200
            text = html
            headers = {"Content-Type": content_type}

            def raise_for_status(self):
                pass

        monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())

    def test_strips_script_tags(self, monkeypatch):
        html = "<html><body>Hello<script>alert(1)</script> World</body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert "alert" not in result
        assert "Hello" in result

    def test_strips_style_tags(self, monkeypatch):
        html = "<html><body>Text<style>.foo{color:red}</style></body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert "color" not in result

    def test_strips_html_tags(self, monkeypatch):
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert "<h1>" not in result
        assert "Title" in result
        assert "Content" in result

    def test_decodes_html_entities(self, monkeypatch):
        html = "<html><body>&lt;b&gt;bold&lt;/b&gt;</body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert "<b>" in result

    def test_truncates_to_3000_chars(self, monkeypatch):
        html = "<html><body>" + "x" * 5000 + "</body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert len(result) <= 3000

    def test_non_html_content_returned_as_text(self, monkeypatch):
        self._mock_response(monkeypatch, "plain text content", content_type="text/plain")
        result = self.svc._extract_content_sync("https://example.com")
        assert result == "plain text content"

    def test_request_exception_returns_empty_string(self, monkeypatch):
        import requests

        monkeypatch.setattr(requests, "get", lambda *a, **kw: (_ for _ in ()).throw(
            requests.exceptions.ConnectionError("fail")
        ))
        result = self.svc._extract_content_sync("https://example.com")
        assert result == ""


# ═══════════════════════════════════════════════════════════════════
# DeepSeekService
# ═══════════════════════════════════════════════════════════════════

class TestTruncatePrompt:
    svc = DeepSeekService()

    def test_short_prompt_is_unchanged(self):
        text = "hello"
        assert self.svc._truncate_prompt(text) == text

    def test_research_context_sized_prompt_is_unchanged(self):
        text = "x" * 12_000
        assert self.svc._truncate_prompt(text) == text

    def test_configured_prompt_limit_truncates(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MAX_PROMPT_CHARS", "3000")
        svc = DeepSeekService()
        text = "x" * 5000
        result = svc._truncate_prompt(text)
        assert len(result) <= 3100  # 3000 + suffix
        assert "请基于以上内容生成简洁摘要" in result

    def test_truncation_can_be_disabled(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MAX_PROMPT_CHARS", "0")
        svc = DeepSeekService()
        text = "x" * 100_000
        assert svc._truncate_prompt(text) == text


class TestBuildPayload:
    svc = DeepSeekService()

    def test_payload_has_required_keys(self):
        payload = self.svc._build_payload("hello", max_tokens=500, stream=False)
        assert payload["model"] == "deepseek-chat"
        assert payload["stream"] is False
        assert payload["messages"][0]["content"] == "hello"

    def test_max_tokens_is_capped_at_default_limit(self):
        payload = self.svc._build_payload("x", max_tokens=9999, stream=False)
        assert payload["max_tokens"] == 4000

    def test_max_tokens_cap_can_be_configured(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MAX_OUTPUT_TOKENS", "1200")
        svc = DeepSeekService()
        payload = svc._build_payload("x", max_tokens=9999, stream=False)
        assert payload["max_tokens"] == 1200

    def test_max_tokens_defaults_to_configured_limit(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MAX_OUTPUT_TOKENS", "1200")
        svc = DeepSeekService()
        payload = svc._build_payload("x", max_tokens=None, stream=False)
        assert payload["max_tokens"] == 1200

    def test_model_and_temperature_default_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
        monkeypatch.setenv("DEEPSEEK_TEMPERATURE", "0.2")
        svc = DeepSeekService()
        payload = svc._build_payload("hello", max_tokens=500, stream=False)
        assert payload["model"] == "deepseek-reasoner"
        assert payload["temperature"] == 0.2

    def test_model_and_temperature_can_be_overridden_per_call(self):
        payload = self.svc._build_payload(
            "hello",
            max_tokens=500,
            stream=False,
            model="custom-model",
            temperature=0.1,
        )
        assert payload["model"] == "custom-model"
        assert payload["temperature"] == 0.1

    def test_stream_flag_is_forwarded(self):
        payload = self.svc._build_payload("x", max_tokens=100, stream=True)
        assert payload["stream"] is True


# ═══════════════════════════════════════════════════════════════════
# CostTracker
# ═══════════════════════════════════════════════════════════════════

class TestCostTracker:
    def test_estimates_tokens_from_characters(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("a" * 40) == 10

    def test_tracks_llm_call_with_configured_rates(self):
        tracker = CostTracker(
            input_cost_per_1m_tokens=1.0,
            output_cost_per_1m_tokens=2.0,
        )
        tracker.track_llm_call(
            step="query_planning",
            prompt="a" * 400,
            response="b" * 200,
        )
        summary = tracker.summary()
        assert summary["pricing_source"] == "defaults_or_env"
        assert summary["total_input_tokens"] == 100
        assert summary["total_output_tokens"] == 50
        assert summary["estimated_cost_usd"] == 0.0002
        assert summary["calls"][0]["step"] == "query_planning"

    def test_model_defaults_to_deepseek_config(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
        tracker = CostTracker()
        assert tracker.summary()["model"] == "deepseek-reasoner"
