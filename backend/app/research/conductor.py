from __future__ import annotations

import asyncio
from urllib.parse import urlparse
from collections.abc import Awaitable
from collections.abc import Callable

from ..services.compression_service import compression_service
from ..services.verifier_service import verifier_service
from .context_manager import ResearchContextManager
from .models import SubQueryContext
from .query_planner import QueryPlanner
from .retriever import ResearchRetriever
from .scraper import ResearchScraper
from .source_curator import SourceCurator

ResearchEventCallback = Callable[[dict[str, object]], Awaitable[None]]


class ResearchConductor:
    """Coordinates initial search, sub-query planning, scraping, and context gathering."""

    def __init__(self, researcher) -> None:  # noqa: ANN001
        self.researcher = researcher
        self.query_planner = QueryPlanner(researcher.cost_tracker)
        self.retriever = ResearchRetriever()
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
        sub_queries = await self.query_planner.plan(
            query=self.researcher.query,
            initial_results=initial_results,
            max_sub_queries=self.researcher.max_sub_queries,
        )
        if self.researcher.query not in sub_queries:
            sub_queries.append(self.researcher.query)
        self.researcher.sub_queries = sub_queries

        await self._emit(
            on_event,
            "plan",
            "子查询规划完成",
            {
                "sub_queries": sub_queries,
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
                        "description": "正在搜索相关信息源并提取可用证据。",
                        "queries": [sub_query],
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
                        "queries": [sub_query],
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

    async def _process_sub_query(
        self,
        step: int,
        sub_query: str,
        on_event: ResearchEventCallback | None = None,
    ) -> SubQueryContext:
        search_results = await self.retriever.search(sub_query)
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
