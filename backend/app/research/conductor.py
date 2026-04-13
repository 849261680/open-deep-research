from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable

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
                    "search_progress",
                    f"正在研究：{sub_query}",
                    {
                        "step": index,
                        "query": sub_query,
                        "total": len(sub_queries),
                        "cost_summary": self.researcher.cost_tracker.summary(),
                    },
                )
                return await self._process_sub_query(index, sub_query)

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
                    "citations": [
                        {
                            "title": source.title,
                            "link": source.link,
                            "source": source.source,
                            "query": source.query,
                        }
                        for source in context.sources[:5]
                    ],
                },
            )

        contexts = sorted(contexts, key=lambda item: item.step)
        self.researcher.context = contexts
        all_sources = [source for item in contexts for source in item.sources]
        self.researcher.research_sources = self.source_curator.curate(all_sources)
        return contexts

    async def _process_sub_query(
        self, step: int, sub_query: str
    ) -> SubQueryContext:
        search_results = await self.retriever.search(sub_query)
        scraped_sources = await self.scraper.scrape(
            search_results,
            self.researcher.visited_urls,
        )
        context = await self.context_manager.get_context(sub_query, scraped_sources)
        return SubQueryContext(
            step=step,
            query=sub_query,
            sources=scraped_sources,
            context=context,
        )

    async def _emit(
        self,
        on_event: ResearchEventCallback | None,
        event_type: str,
        message: str,
        data: object,
    ) -> None:
        if on_event is not None:
            await on_event({"type": event_type, "message": message, "data": data})
