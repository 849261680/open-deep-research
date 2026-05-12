from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse
from collections.abc import Awaitable
from collections.abc import Callable

from ..services.compression_service import compression_service
from ..services.verifier_service import verifier_service
from .context_manager import ResearchContextManager
from .models import ResearchPlanItem
from .models import SubQueryContext
from .query_planner import QueryPlanner
from .retriever import ResearchRetriever
from .scraper import ResearchScraper
from .source_curator import SourceCurator

ResearchEventCallback = Callable[[dict[str, object]], Awaitable[None]]
logger = logging.getLogger(__name__)


class ResearchConductor:
    """Coordinates initial search, sub-query planning, scraping, and context gathering."""

    def __init__(self, researcher) -> None:  # noqa: ANN001
        self.researcher = researcher
        self.query_planner = QueryPlanner(researcher.cost_tracker)
        self.retriever = ResearchRetriever(getattr(researcher, "config", None))
        self.scraper = ResearchScraper()
        self.context_manager = ResearchContextManager(researcher.cost_tracker)
        self.source_curator = SourceCurator()

    async def conduct_research(
        self, on_event: ResearchEventCallback | None = None
    ) -> list[SubQueryContext]:
        await self._emit(
            on_event,
            "planning",
            "正在进行初始搜索并规划子查询...",
            {"query": self.researcher.query},
        )
        initial_results = await self.retriever.search(self.researcher.query)
        await self._emit_search_result(
            on_event,
            step=0,
            query=self.researcher.query,
            sources=initial_results,
            message="已完成初始搜索，正在归纳研究线索...",
        )
        plan_items = await self.query_planner.plan_detailed(
            query=self.researcher.query,
            initial_results=initial_results,
            max_sub_queries=self.researcher.max_sub_queries,
        )
        plan_items = self._ensure_original_query_plan(plan_items)
        sub_queries = [item.title for item in plan_items]
        if self.researcher.query not in sub_queries:
            sub_queries.append(self.researcher.query)
        self.researcher.sub_queries = sub_queries
        self.researcher.plan_items = plan_items
        self._log_plan_created(plan_items)

        await self._emit(
            on_event,
            "plan",
            "子查询规划完成",
            {
                "sub_queries": sub_queries,
                "plan_items": self._serialize_plan_items(plan_items),
                "cost_summary": self.researcher.cost_tracker.summary(),
            },
        )

        semaphore = asyncio.Semaphore(self.researcher.max_concurrency)

        async def run_sub_query(index: int, sub_query: str) -> SubQueryContext:
            async with semaphore:
                await self._emit(
                    on_event,
                    "step_start",
                    f"开始处理子查询 {index}",
                    {
                        "step": index,
                        "query": sub_query,
                        "total": len(sub_queries),
                        "title": sub_query,
                        "description": self._description_for_query(plan_items, sub_query),
                        "queries": self._search_queries_for_query(plan_items, sub_query),
                        "cost_summary": self.researcher.cost_tracker.summary(),
                    },
                )
                await self._emit(
                    on_event,
                    "search_progress",
                    f"正在研究：{sub_query}",
                    {
                        "step": index,
                        "query": sub_query,
                        "total": len(sub_queries),
                        "queries": self._search_queries_for_query(plan_items, sub_query),
                        "cost_summary": self.researcher.cost_tracker.summary(),
                    },
                )
                return await self._process_sub_query(index, sub_query, on_event)

        tasks = [
            asyncio.create_task(run_sub_query(index, sub_query))
            for index, sub_query in enumerate(sub_queries, start=1)
        ]
        contexts: list[SubQueryContext] = []
        for task in asyncio.as_completed(tasks):
            context = await task
            contexts.append(context)
            await self._emit(
                on_event,
                "step_complete",
                f"完成子查询：{context.query}",
                {
                    "step": context.step,
                    "title": context.query,
                    "status": "completed",
                    "analysis": context.context,
                    "cost_summary": self.researcher.cost_tracker.summary(),
                    "citations": [citation.model_dump() for citation in context.citations],
                    "evidence_ids": context.evidence_ids,
                    "compressed_evidence": context.compressed_evidence,
                    "verification": context.verification,
                    "search_sources": [
                        {
                            "title": source.title,
                            "link": source.link,
                            "source": source.source,
                            "query": source.query,
                        }
                        for source in context.sources
                    ],
                },
            )

        contexts = sorted(contexts, key=lambda item: item.step)
        self.researcher.context = contexts
        all_sources = [source for item in contexts for source in item.sources]
        self.researcher.research_sources = self.source_curator.curate(all_sources)
        return contexts

    def _log_plan_created(self, plan_items: list[ResearchPlanItem]) -> None:
        """Log structured plan metadata for LogQL-based runtime verification."""
        logger.info(
            "research_plan_created",
            extra={
                "task_id": getattr(self.researcher, "task_id", None),
                "query": self.researcher.query,
                "plan_items_count": len(plan_items),
                "dimensions": [item.dimension for item in plan_items if item.dimension],
                "search_queries_count": sum(
                    len(item.search_queries) for item in plan_items
                ),
            },
        )

    def _ensure_original_query_plan(
        self,
        plan_items: list[ResearchPlanItem],
    ) -> list[ResearchPlanItem]:
        """Append the original query as a plan item when absent."""
        titles = {item.title for item in plan_items}
        if self.researcher.query in titles:
            return plan_items
        original_item = ResearchPlanItem(
            step=len(plan_items) + 1,
            title=self.researcher.query,
            dimension="核心问题",
            rationale="保留原始问题作为主线，确保最终报告直接回答用户问题。",
            search_queries=[self.researcher.query],
            expected_outcome="形成对原始问题的直接回答和证据汇总。",
            evidence_targets=["综合资料", "权威来源"],
        )
        return [*plan_items, original_item]

    def _serialize_plan_items(
        self,
        plan_items: list[ResearchPlanItem],
    ) -> list[dict[str, object]]:
        """Serialize structured plan items for stream events."""
        return [
            {
                "step": item.step,
                "title": item.title,
                "dimension": item.dimension,
                "rationale": item.rationale,
                "search_queries": item.search_queries,
                "expected_outcome": item.expected_outcome,
                "evidence_targets": item.evidence_targets,
            }
            for item in plan_items
        ]

    def _description_for_query(
        self,
        plan_items: list[ResearchPlanItem],
        query: str,
    ) -> str:
        """Build a concise user-facing plan description for one query."""
        item = self._plan_item_for_query(plan_items, query)
        if item is None:
            return "正在搜索相关信息源并提取可用证据。"
        if item.dimension and item.rationale:
            return f"{item.dimension}：{item.rationale}"
        return item.rationale or item.dimension or "正在搜索相关信息源并提取可用证据。"

    def _search_queries_for_query(
        self,
        plan_items: list[ResearchPlanItem],
        query: str,
    ) -> list[str]:
        """Return planned search queries for one research query."""
        item = self._plan_item_for_query(plan_items, query)
        if item is None or not item.search_queries:
            return [query]
        return item.search_queries

    def _plan_item_for_query(
        self,
        plan_items: list[ResearchPlanItem],
        query: str,
    ) -> ResearchPlanItem | None:
        """Find the structured plan item for one query title."""
        for item in plan_items:
            if item.title == query:
                return item
        return None

    async def _process_sub_query(
        self,
        step: int,
        sub_query: str,
        on_event: ResearchEventCallback | None = None,
    ) -> SubQueryContext:
        planned_queries = self._search_queries_for_query(
            getattr(self.researcher, "plan_items", []),
            sub_query,
        )
        search_results = await self._search_planned_queries(planned_queries)
        plan_item = self._plan_item_for_query(
            getattr(self.researcher, "plan_items", []),
            sub_query,
        )
        search_results = self.source_curator.curate(
            search_results,
            max_sources=8,
            evidence_targets=plan_item.evidence_targets if plan_item else None,
        )
        await self._emit_search_result(
            on_event,
            step=step,
            query=sub_query,
            sources=search_results,
        )
        scraped_sources = await self.scraper.scrape(
            search_results,
            self.researcher.visited_urls,
        )
        await self._emit(
            on_event,
            "analysis_progress",
            f"已阅读相关资料，正在整理：{sub_query}",
            {
                "step": step,
                "query": sub_query,
                "title": sub_query,
                "queries": [sub_query],
                "sources": self._serialize_sources(scraped_sources),
                "read_count": len(scraped_sources),
                "domains": self._extract_domains(scraped_sources),
            },
        )
        evidence_ids = await self._store_evidence(step, sub_query, scraped_sources)
        evidence = self.researcher.evidence_store.get_many(evidence_ids)
        citations = self.researcher.evidence_store.get_citations(evidence_ids)
        compressed_evidence = compression_service.compress_evidence(sub_query, evidence)
        context = await self.context_manager.get_context(sub_query, scraped_sources)
        verification = await verifier_service.verify_section(
            analysis=context,
            citations=citations,
            compressed_evidence=compressed_evidence,
        )
        return SubQueryContext(
            step=step,
            query=sub_query,
            sources=scraped_sources,
            citations=citations,
            evidence_ids=evidence_ids,
            compressed_evidence=compressed_evidence,
            verification=verification,
            context=context,
        )

    async def _search_planned_queries(
        self,
        planned_queries: list[str],
    ) -> list[object]:
        """Search all planned query variants and dedupe results by link."""
        results: list[object] = []
        seen_links: set[str] = set()
        for query in planned_queries:
            for source in await self.retriever.search(query):
                link = str(getattr(source, "link", "")).strip()
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                results.append(source)
        return results

    async def _store_evidence(
        self,
        step: int,
        sub_query: str,
        sources: list,
    ) -> list[str]:
        if not sources:
            return []

        evidence_ids = await self.researcher.evidence_store.add_many(
            section_id=f"subquery-{step}",
            query=sub_query,
            source_type="web",
            task_id=self.researcher.task_id,
            items=[
                {
                    "title": source.title,
                    "link": source.link,
                    "snippet": source.snippet,
                    "source_type": source.source,
                    "extracted_content": source.extracted_content,
                }
                for source in sources
            ],
        )
        if self.researcher.repository is not None and self.researcher.task_id is not None:
            for item in self.researcher.evidence_store.get_many(evidence_ids):
                self.researcher.repository.save_evidence(self.researcher.task_id, item)
        return evidence_ids

    async def _emit(
        self,
        on_event: ResearchEventCallback | None,
        event_type: str,
        message: str,
        data: object,
    ) -> None:
        if on_event is not None:
            await on_event({"type": event_type, "message": message, "data": data})

    async def _emit_search_result(
        self,
        on_event: ResearchEventCallback | None,
        *,
        step: int,
        query: str,
        sources: list[object],
        message: str | None = None,
    ) -> None:
        await self._emit(
            on_event,
            "search_result",
            message or f"搜索完成，已获取候选信息源：{query}",
            {
                "step": step,
                "query": query,
                "queries": [query],
                "sources": self._serialize_sources(sources),
                "domains": self._extract_domains(sources),
            },
        )

    def _serialize_sources(self, sources: list[object]) -> list[dict[str, str]]:
        serialized: list[dict[str, str]] = []
        for source in sources:
            title = str(getattr(source, "title", "")).strip()
            link = str(getattr(source, "link", "")).strip()
            source_type = str(getattr(source, "source", "")).strip()
            query = str(getattr(source, "query", "")).strip()
            if not title and not link:
                continue
            serialized.append(
                {
                    "title": title,
                    "link": link,
                    "source": source_type,
                    "query": query,
                    "domain": self._extract_domain(link),
                }
            )
        return serialized

    def _extract_domains(self, sources: list[object]) -> list[str]:
        domains: list[str] = []
        seen: set[str] = set()
        for source in sources:
            domain = self._extract_domain(str(getattr(source, "link", "")).strip())
            if not domain or domain in seen:
                continue
            seen.add(domain)
            domains.append(domain)
        return domains

    def _extract_domain(self, link: str) -> str:
        if not link:
            return ""
        hostname = urlparse(link).hostname or ""
        return hostname.removeprefix("www.")
