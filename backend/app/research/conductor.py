from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from typing import TypedDict
from typing import cast
from urllib.parse import urlparse

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langsmith import traceable

from ..services.compression_service import compression_service
from ..services.verifier_service import verifier_service
from .context_manager import ResearchContextManager
from .models import DeepResearchDecision
from .models import ResearchPlanItem
from .models import ResearchSource
from .models import SubQueryContext
from .query_planner import QueryPlanner
from .retriever import ResearchRetriever
from .scraper import ResearchScraper
from .source_curator import SourceCurator

ResearchEventCallback = Callable[[dict[str, object]], Awaitable[None]]
logger = logging.getLogger(__name__)
LOGGED_RESEARCH_EVENTS = {
    "step_start",
    "step_complete",
    "deep_research_decision",
}


class ResearchGraphState(TypedDict, total=False):
    """Mutable LangGraph state for the top-level research workflow."""

    plan_items: list[ResearchPlanItem]
    runnable_plan_items: list[ResearchPlanItem]
    completed_queries: list[str]
    sub_queries: list[str]
    contexts: list[SubQueryContext]


class QueryBranchItem(TypedDict):
    """One queued query branch item inside the deep-research subgraph."""

    step: int
    query: str
    depth: int
    parent_query: str
    plan_item: ResearchPlanItem | None


class QueryBranchGraphState(TypedDict, total=False):
    """Mutable LangGraph state for one root query and its follow-ups."""

    pending: list[QueryBranchItem]
    current: QueryBranchItem
    current_context: SubQueryContext
    contexts: list[SubQueryContext]


def _trace_research_inputs(inputs: dict[str, object]) -> dict[str, object]:
    """Keep LangSmith workflow inputs compact and JSON-safe."""
    conductor = inputs.get("self")
    researcher = getattr(conductor, "researcher", None)
    return {
        "query": getattr(researcher, "query", ""),
        "task_id": getattr(researcher, "task_id", None),
        "max_sub_queries": getattr(researcher, "max_sub_queries", None),
        "max_concurrency": getattr(researcher, "max_concurrency", None),
    }


def _trace_state_inputs(inputs: dict[str, object]) -> dict[str, object]:
    """Summarize LangGraph state without logging callbacks or full contexts."""
    state = inputs.get("state")
    if not isinstance(state, dict):
        return _trace_research_inputs(inputs)
    sub_queries = state.get("sub_queries", [])
    return {
        **_trace_research_inputs(inputs),
        "sub_query_count": len(sub_queries) if isinstance(sub_queries, list) else 0,
        "completed_query_count": len(state.get("completed_queries", [])),
    }


def _trace_query_inputs(inputs: dict[str, object]) -> dict[str, object]:
    """Summarize one query branch for LangSmith."""
    return {
        **_trace_research_inputs(inputs),
        "step": inputs.get("step"),
        "query": inputs.get("query") or inputs.get("sub_query"),
        "depth": inputs.get("depth"),
        "parent_query": inputs.get("parent_query", ""),
    }


def _trace_context_outputs(output: object) -> dict[str, object]:
    """Summarize context list outputs for LangSmith."""
    if isinstance(output, list):
        return {
            "context_count": len(output),
            "queries": [
                getattr(context, "query", "")
                for context in output[:10]
            ],
        }
    return {"output_type": type(output).__name__}


def _trace_state_outputs(output: object) -> dict[str, object]:
    """Summarize state outputs for LangSmith."""
    if isinstance(output, dict):
        return {
            "plan_item_count": len(output.get("plan_items", [])),
            "sub_query_count": len(output.get("sub_queries", [])),
            "context_count": len(output.get("contexts", [])),
        }
    return {"output_type": type(output).__name__}


def _trace_branch_inputs(inputs: dict[str, object]) -> dict[str, object]:
    """Summarize deep-research subgraph state for LangSmith."""
    state = inputs.get("state")
    if not isinstance(state, dict):
        return _trace_research_inputs(inputs)
    current = state.get("current", {})
    if not isinstance(current, dict):
        current = {}
    pending = state.get("pending", [])
    return {
        **_trace_research_inputs(inputs),
        "step": current.get("step"),
        "query": current.get("query"),
        "depth": current.get("depth"),
        "pending_count": len(pending) if isinstance(pending, list) else 0,
    }


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
        return await self._run_langgraph_workflow(on_event)

    @traceable(
        name="Deep Research LangGraph workflow",
        run_type="chain",
        tags=["langgraph", "research-agent"],
        process_inputs=_trace_research_inputs,
        process_outputs=_trace_context_outputs,
    )
    async def _run_langgraph_workflow(
        self,
        on_event: ResearchEventCallback | None = None,
    ) -> list[SubQueryContext]:
        """Run the LangGraph workflow with a top-level LangSmith trace span."""
        graph = self._build_research_graph(on_event)
        state = await graph.ainvoke({})
        return state.get("contexts", [])

    def _build_research_graph(self, on_event: ResearchEventCallback | None):
        """Build the LangGraph workflow that orchestrates one research run."""
        graph = StateGraph(ResearchGraphState)
        graph.add_node("plan_queries", self._graph_plan_queries(on_event))
        graph.add_node("research_queries", self._graph_research_queries(on_event))
        graph.add_node("curate_sources", self._graph_curate_sources())
        graph.add_edge(START, "plan_queries")
        graph.add_edge("plan_queries", "research_queries")
        graph.add_edge("research_queries", "curate_sources")
        graph.add_edge("curate_sources", END)
        return graph.compile()

    def _graph_plan_queries(self, on_event: ResearchEventCallback | None):
        """Return a LangGraph node that plans root research queries."""
        async def node(state: ResearchGraphState) -> ResearchGraphState:  # noqa: ARG001
            await self._emit(
                on_event,
                "workflow_start",
                "LangGraph 研究工作流已启动",
                {
                    "workflow_engine": "langgraph",
                    "nodes": ["plan_queries", "research_queries", "curate_sources"],
                },
            )
            return await self._plan_query_state(on_event)

        return node

    def _graph_research_queries(self, on_event: ResearchEventCallback | None):
        """Return a LangGraph node that runs planned queries."""
        async def node(state: ResearchGraphState) -> ResearchGraphState:
            return {"contexts": await self._run_query_state(state, on_event)}

        return node

    def _graph_curate_sources(self):
        """Return a LangGraph node that stores final contexts and curated sources."""
        async def node(state: ResearchGraphState) -> ResearchGraphState:
            contexts = sorted(state.get("contexts", []), key=lambda item: item.step)
            self.researcher.context = contexts
            all_sources = [source for item in contexts for source in item.sources]
            self.researcher.research_sources = self.source_curator.curate(all_sources)
            return {"contexts": contexts}

        return node

    async def _plan_query_state(
        self,
        on_event: ResearchEventCallback | None,
    ) -> ResearchGraphState:
        """Plan the runnable root queries for the LangGraph state."""
        return await self._traced_plan_query_state(on_event)

    @traceable(
        name="plan_queries",
        run_type="chain",
        tags=["langgraph-node", "planning"],
        process_inputs=_trace_research_inputs,
        process_outputs=_trace_state_outputs,
    )
    async def _traced_plan_query_state(
        self,
        on_event: ResearchEventCallback | None,
    ) -> ResearchGraphState:
        """Traceable implementation of the LangGraph planning node."""
        await self._emit(
            on_event,
            "planning",
            "正在进行初始搜索并规划子查询...",
            {"query": self.researcher.query},
        )
        plan_items = await self._plan_items(on_event)
        plan_items = self._ensure_original_query_plan(plan_items)
        completed_queries = self._completed_checkpoint_queries()
        runnable_plan_items = [
            item for item in plan_items if item.title not in completed_queries
        ]
        sub_queries = [item.title for item in runnable_plan_items]
        if (
            self.researcher.query not in sub_queries
            and self.researcher.query not in completed_queries
        ):
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
                "completed_checkpoint_queries": sorted(completed_queries),
                "cost_summary": self.researcher.cost_tracker.summary(),
            },
        )
        return {
            "plan_items": plan_items,
            "runnable_plan_items": runnable_plan_items,
            "completed_queries": sorted(completed_queries),
            "sub_queries": sub_queries,
        }

    async def _run_query_state(
        self,
        state: ResearchGraphState,
        on_event: ResearchEventCallback | None,
    ) -> list[SubQueryContext]:
        """Run planned query branches from the LangGraph state."""
        return await self._traced_run_query_state(state, on_event)

    @traceable(
        name="research_queries",
        run_type="chain",
        tags=["langgraph-node", "research"],
        process_inputs=_trace_state_inputs,
        process_outputs=_trace_context_outputs,
    )
    async def _traced_run_query_state(
        self,
        state: ResearchGraphState,
        on_event: ResearchEventCallback | None,
    ) -> list[SubQueryContext]:
        """Traceable implementation of the LangGraph research node."""
        sub_queries = state.get("sub_queries", [])
        if not sub_queries:
            self.researcher.context = list(
                getattr(self.researcher, "checkpoint_contexts", [])
            )
            return []

        plan_items = state.get("plan_items", [])
        runnable_plan_items = state.get("runnable_plan_items", [])
        semaphore = asyncio.Semaphore(self.researcher.max_concurrency)

        async def run_sub_query(index: int, sub_query: str) -> list[SubQueryContext]:
            async with semaphore:
                return await self._process_query_tree(
                    step=index,
                    query=sub_query,
                    plan_items=plan_items,
                    total=len(sub_queries),
                    on_event=on_event,
                )

        runnable_steps = [(item.step, item.title) for item in runnable_plan_items]
        tasks = [
            asyncio.create_task(run_sub_query(index, sub_query))
            for index, sub_query in runnable_steps
        ]
        contexts: list[SubQueryContext] = []
        for task in asyncio.as_completed(tasks):
            branch_contexts = await task
            contexts.extend(branch_contexts)
            for context in branch_contexts:
                await self._emit_step_complete(on_event, context)

        return contexts

    def _completed_checkpoint_queries(self) -> set[str]:
        """Return queries already completed in the persisted checkpoint."""
        return {
            context.query
            for context in getattr(self.researcher, "checkpoint_contexts", [])
            if context.context
        }

    async def _plan_items(
        self,
        on_event: ResearchEventCallback | None,
    ) -> list[ResearchPlanItem]:
        """Use confirmed plan items or generate a fresh plan from initial search."""
        confirmed = getattr(self.researcher, "confirmed_plan_items", [])
        if confirmed:
            return self._normalize_confirmed_plan_items(confirmed)
        initial_results = await self.retriever.search(self.researcher.query)
        await self._emit_search_result(
            on_event,
            step=0,
            query=self.researcher.query,
            sources=initial_results,
            message="已完成初始搜索，正在归纳研究线索...",
        )
        return await self.query_planner.plan_detailed(
            query=self.researcher.query,
            initial_results=initial_results,
            max_sub_queries=self.researcher.max_sub_queries,
        )

    async def _process_query_tree(
        self,
        *,
        step: int,
        query: str,
        plan_items: list[ResearchPlanItem],
        total: int,
        on_event: ResearchEventCallback | None,
        depth: int = 1,
        parent_query: str = "",
        inherited_plan_item: ResearchPlanItem | None = None,
    ) -> list[SubQueryContext]:
        """Run one query and recursively follow evidence gaps within depth limits."""
        return await self._traced_process_query_tree(
            step=step,
            query=query,
            plan_items=plan_items,
            total=total,
            on_event=on_event,
            depth=depth,
            parent_query=parent_query,
            inherited_plan_item=inherited_plan_item,
        )

    @traceable(
        name="process_query_tree",
        run_type="chain",
        tags=["deep-research", "recursive"],
        process_inputs=_trace_query_inputs,
        process_outputs=_trace_context_outputs,
    )
    async def _traced_process_query_tree(
        self,
        *,
        step: int,
        query: str,
        plan_items: list[ResearchPlanItem],
        total: int,
        on_event: ResearchEventCallback | None,
        depth: int = 1,
        parent_query: str = "",
        inherited_plan_item: ResearchPlanItem | None = None,
    ) -> list[SubQueryContext]:
        """Traceable query branch runner, including follow-up loops."""
        graph = self._build_query_branch_graph(
            plan_items=plan_items,
            total=total,
            on_event=on_event,
        )
        initial_plan_item = inherited_plan_item or self._plan_item_for_query(
            plan_items,
            query,
        )
        state = await graph.ainvoke(
            {
                "pending": [
                    {
                        "step": step,
                        "query": query,
                        "depth": depth,
                        "parent_query": parent_query,
                        "plan_item": initial_plan_item,
                    }
                ],
                "contexts": [],
            }
        )
        return state.get("contexts", [])

    def _build_query_branch_graph(
        self,
        *,
        plan_items: list[ResearchPlanItem],
        total: int,
        on_event: ResearchEventCallback | None,
    ):
        """Build a LangGraph subgraph for one query branch and its follow-ups."""
        graph = StateGraph(QueryBranchGraphState)
        graph.add_node("load_next_query", self._branch_load_next_query())
        graph.add_node(
            "process_current_query",
            self._branch_process_current_query(plan_items, total, on_event),
        )
        graph.add_node(
            "decide_next_queries",
            self._branch_decide_next_queries(plan_items, total, on_event),
        )
        graph.add_edge(START, "load_next_query")
        graph.add_edge("load_next_query", "process_current_query")
        graph.add_edge("process_current_query", "decide_next_queries")
        graph.add_conditional_edges(
            "decide_next_queries",
            self._branch_route_after_decision,
            {
                "continue": "load_next_query",
                "done": END,
            },
        )
        return graph.compile()

    def _branch_load_next_query(self):
        """Return a node that loads the next queued query branch item."""
        async def node(state: QueryBranchGraphState) -> QueryBranchGraphState:
            pending = state.get("pending", [])
            if not pending:
                return state
            return {
                "current": pending[0],
                "pending": pending[1:],
            }

        return node

    def _branch_process_current_query(
        self,
        plan_items: list[ResearchPlanItem],
        total: int,
        on_event: ResearchEventCallback | None,
    ):
        """Return a node that researches the currently loaded query."""
        async def node(state: QueryBranchGraphState) -> QueryBranchGraphState:
            return await self._traced_branch_process_current_query(
                state=state,
                plan_items=plan_items,
                total=total,
                on_event=on_event,
            )

        return node

    @traceable(
        name="branch_process_current_query",
        run_type="chain",
        tags=["langgraph-subgraph", "deep-research"],
        process_inputs=_trace_branch_inputs,
        process_outputs=_trace_state_outputs,
    )
    async def _traced_branch_process_current_query(
        self,
        *,
        state: QueryBranchGraphState,
        plan_items: list[ResearchPlanItem],
        total: int,
        on_event: ResearchEventCallback | None,
    ) -> QueryBranchGraphState:
        """Process one query item in the deep-research subgraph."""
        current = state.get("current")
        if current is None:
            return {"contexts": state.get("contexts", [])}
        plan_item = current["plan_item"] or self._plan_item_for_query(
            plan_items,
            current["query"],
        )
        await self._emit_step_start(
            on_event,
            current["step"],
            current["query"],
            plan_items,
            total,
            current["depth"],
            current["parent_query"],
        )
        context = await self._process_sub_query(
            current["step"],
            current["query"],
            on_event,
            depth=current["depth"],
            parent_query=current["parent_query"],
            plan_item=plan_item,
        )
        return {"current_context": context}

    def _branch_decide_next_queries(
        self,
        plan_items: list[ResearchPlanItem],
        total: int,  # noqa: ARG002
        on_event: ResearchEventCallback | None,
    ):
        """Return a node that decides and queues follow-up queries."""
        async def node(state: QueryBranchGraphState) -> QueryBranchGraphState:
            return await self._traced_branch_decide_next_queries(
                state=state,
                plan_items=plan_items,
                on_event=on_event,
            )

        return node

    @traceable(
        name="branch_decide_next_queries",
        run_type="chain",
        tags=["langgraph-subgraph", "deep-research-decision"],
        process_inputs=_trace_branch_inputs,
        process_outputs=_trace_state_outputs,
    )
    async def _traced_branch_decide_next_queries(
        self,
        *,
        state: QueryBranchGraphState,
        plan_items: list[ResearchPlanItem],
        on_event: ResearchEventCallback | None,
    ) -> QueryBranchGraphState:
        """Decide whether the current query needs follow-up branches."""
        current = state.get("current")
        context = state.get("current_context")
        if current is None or context is None:
            return {"contexts": state.get("contexts", [])}
        plan_item = current["plan_item"] or self._plan_item_for_query(
            plan_items,
            current["query"],
        )
        decision = await self._decide_deeper_research(
            context,
            plan_item,
            current["depth"],
        )
        context.deep_research = decision
        await self._emit_deep_research_decision(on_event, context, decision)
        contexts = [*state.get("contexts", []), context]
        pending = state.get("pending", [])
        if not decision.should_continue:
            return {"contexts": contexts, "pending": pending}

        follow_up_items: list[QueryBranchItem] = [
            {
                "step": self._child_step(current["step"], child_index),
                "query": follow_up_query,
                "depth": current["depth"] + 1,
                "parent_query": current["query"],
                "plan_item": cast(ResearchPlanItem | None, plan_item),
            }
            for child_index, follow_up_query in enumerate(
                decision.follow_up_queries,
                start=1,
            )
        ]
        return {"contexts": contexts, "pending": [*follow_up_items, *pending]}

    def _branch_route_after_decision(self, state: QueryBranchGraphState) -> str:
        """Route the branch subgraph while queued follow-up queries remain."""
        return "continue" if state.get("pending") else "done"

    def _log_plan_created(self, plan_items: list[ResearchPlanItem]) -> None:
        """Log structured plan metadata for LogQL-based runtime verification."""
        logger.info(
            "research_plan_created",
            extra={
                "task_id": getattr(self.researcher, "task_id", None),
                "request_id": getattr(self.researcher, "request_id", None),
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

    def _normalize_confirmed_plan_items(
        self,
        plan_items: list[ResearchPlanItem],
    ) -> list[ResearchPlanItem]:
        """Renumber confirmed plan items after user edits or deletions."""
        normalized: list[ResearchPlanItem] = []
        for item in plan_items:
            normalized.append(item.model_copy(update={"step": len(normalized) + 1}))
            if len(normalized) >= self.researcher.max_sub_queries:
                break
        return normalized

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
        *,
        depth: int = 1,
        parent_query: str = "",
        plan_item: ResearchPlanItem | None = None,
    ) -> SubQueryContext:
        return await self._traced_process_sub_query(
            step,
            sub_query,
            on_event,
            depth=depth,
            parent_query=parent_query,
            plan_item=plan_item,
        )

    @traceable(
        name="process_sub_query",
        run_type="chain",
        tags=["research", "evidence"],
        process_inputs=_trace_query_inputs,
        process_outputs=lambda output: {
            "query": getattr(output, "query", ""),
            "step": getattr(output, "step", None),
            "depth": getattr(output, "depth", None),
            "source_count": len(getattr(output, "sources", [])),
            "citation_count": len(getattr(output, "citations", [])),
            "evidence_count": len(getattr(output, "evidence_ids", [])),
        },
    )
    async def _traced_process_sub_query(
        self,
        step: int,
        sub_query: str,
        on_event: ResearchEventCallback | None = None,
        *,
        depth: int = 1,
        parent_query: str = "",
        plan_item: ResearchPlanItem | None = None,
    ) -> SubQueryContext:
        """Traceable sub-query pipeline from search through verification."""
        planned_queries = self._search_queries_for_query(
            getattr(self.researcher, "plan_items", []),
            sub_query,
        )
        search_results = await self._search_planned_queries(planned_queries)
        plan_item = plan_item or self._plan_item_for_query(
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
        read_budget = self._read_budget()
        scraped_sources = await self.scraper.scrape(
            search_results,
            self.researcher.visited_urls,
            max_sources=read_budget,
        )
        source_summary = self._source_summary(scraped_sources)
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
                "source_summary": source_summary,
                "domains": self._extract_domains(scraped_sources),
            },
        )
        evidence_ids = await self._store_evidence(
            step,
            sub_query,
            scraped_sources,
            extraction_limit=read_budget,
        )
        evidence = self.researcher.evidence_store.get_many(evidence_ids)
        citations = self.researcher.evidence_store.get_citations(evidence_ids)
        self._mark_cited_sources(scraped_sources, citations)
        source_summary = self._source_summary(scraped_sources)
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
            depth=depth,
            parent_query=parent_query,
            sources=scraped_sources,
            citations=citations,
            evidence_ids=evidence_ids,
            compressed_evidence=compressed_evidence,
            verification=verification,
            context=context,
            source_summary=source_summary,
        )

    async def _decide_deeper_research(
        self,
        context: SubQueryContext,
        plan_item: ResearchPlanItem | None,
        depth: int,
    ) -> DeepResearchDecision:
        """Decide and record whether to continue one branch of research."""
        config = getattr(self.researcher, "config", None)
        max_depth = getattr(config, "deep_research_depth", 1)
        breadth = getattr(config, "deep_research_breadth", 0)
        if depth >= max_depth:
            return DeepResearchDecision(
                should_continue=False,
                reason=f"已达到配置的最大深度 {max_depth}。",
                stop_condition="达到 deep_research_depth",
            )
        return await self.query_planner.plan_deeper_research(
            query=context.query,
            plan_item=plan_item,
            compressed_evidence=context.compressed_evidence,
            verification=context.verification,
            max_follow_up_queries=breadth,
        )

    async def _emit_step_start(
        self,
        on_event: ResearchEventCallback | None,
        step: int,
        query: str,
        plan_items: list[ResearchPlanItem],
        total: int,
        depth: int,
        parent_query: str,
    ) -> None:
        """Emit start and search progress for one root or deeper query."""
        await self._emit(
            on_event,
            "step_start",
            f"开始处理子查询 {step}",
            {
                "step": step,
                "query": query,
                "total": total,
                "depth": depth,
                "parent_query": parent_query,
                "title": query,
                "description": self._description_for_query(plan_items, query),
                "queries": self._search_queries_for_query(plan_items, query),
                "cost_summary": self.researcher.cost_tracker.summary(),
            },
        )
        await self._emit(
            on_event,
            "search_progress",
            f"正在研究：{query}",
            {
                "step": step,
                "query": query,
                "total": total,
                "depth": depth,
                "parent_query": parent_query,
                "queries": self._search_queries_for_query(plan_items, query),
                "cost_summary": self.researcher.cost_tracker.summary(),
            },
        )

    async def _emit_deep_research_decision(
        self,
        on_event: ResearchEventCallback | None,
        context: SubQueryContext,
        decision: DeepResearchDecision,
    ) -> None:
        """Emit the evidence-gap decision made after reading one query."""
        await self._emit(
            on_event,
            "deep_research_decision",
            f"深挖判断：{context.query}",
            {
                "step": context.step,
                "query": context.query,
                "depth": context.depth,
                "parent_query": context.parent_query,
                "should_continue": decision.should_continue,
                "reason": decision.reason,
                "evidence_gaps": decision.evidence_gaps,
                "follow_up_queries": decision.follow_up_queries,
                "stop_condition": decision.stop_condition,
            },
        )

    async def _emit_step_complete(
        self,
        on_event: ResearchEventCallback | None,
        context: SubQueryContext,
    ) -> None:
        """Emit completed context with source and deep-research metadata."""
        await self._emit(
            on_event,
            "step_complete",
            f"完成子查询：{context.query}",
            {
                "step": context.step,
                "title": context.query,
                "status": "completed",
                "depth": context.depth,
                "parent_query": context.parent_query,
                "analysis": context.context,
                "cost_summary": self.researcher.cost_tracker.summary(),
                "citations": [citation.model_dump() for citation in context.citations],
                "evidence_ids": context.evidence_ids,
                "compressed_evidence": context.compressed_evidence,
                "verification": context.verification,
                "deep_research": context.deep_research.model_dump(),
                "source_summary": context.source_summary,
                "search_sources": [
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
            },
        )

    def _child_step(self, parent_step: int, child_index: int) -> int:
        """Build a stable numeric step for one deeper follow-up query."""
        return parent_step * 100 + child_index

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
        extraction_limit: int,
    ) -> list[str]:
        """Store source evidence while honoring the configured read budget."""
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
                    "status": source.status,
                    "failure_reason": source.failure_reason,
                }
                for source in sources
            ],
            extraction_limit=extraction_limit,
        )
        if self.researcher.repository is not None and self.researcher.task_id is not None:
            for item in self.researcher.evidence_store.get_many(evidence_ids):
                self.researcher.repository.save_evidence(self.researcher.task_id, item)
        return evidence_ids

    def _read_budget(self) -> int:
        """Return the configured source-read budget for one section."""
        config = getattr(self.researcher, "config", None)
        return int(getattr(config, "max_read_pages_per_section", 8))

    def _mark_cited_sources(self, sources: list[ResearchSource], citations: list) -> None:
        """Mark sources that made it into the citation list."""
        cited_links = {str(citation.link) for citation in citations if getattr(citation, "link", "")}
        for source in sources:
            if source.link in cited_links:
                source.status = "cited"
                source.failure_reason = ""

    def _source_summary(self, sources: list[ResearchSource]) -> dict[str, int]:
        """Count source lifecycle states for stream and report metadata."""
        return {
            "searched_count": len(sources),
            "selected_count": sum(1 for source in sources if source.status in {"selected", "read", "cited", "failed"}),
            "read_count": sum(1 for source in sources if source.status in {"read", "cited"}),
            "failed_count": sum(1 for source in sources if source.status == "failed"),
            "cited_count": sum(1 for source in sources if source.status == "cited"),
            "discarded_count": sum(1 for source in sources if source.status == "discarded"),
        }

    async def _emit(
        self,
        on_event: ResearchEventCallback | None,
        event_type: str,
        message: str,
        data: object,
    ) -> None:
        self._log_research_event(event_type, data)
        if on_event is not None:
            await on_event({"type": event_type, "message": message, "data": data})

    def _log_research_event(self, event_type: str, data: object) -> None:
        """Write selected research stream events as compact structured logs."""
        if event_type not in LOGGED_RESEARCH_EVENTS or not isinstance(data, dict):
            return
        logger.info(
            event_type,
            extra={
                "task_id": getattr(self.researcher, "task_id", None),
                "request_id": getattr(self.researcher, "request_id", None),
                "research_event_type": event_type,
                **self._log_fields_for_event(event_type, data),
            },
        )

    def _log_fields_for_event(
        self,
        event_type: str,
        data: dict[str, object],
    ) -> dict[str, object]:
        """Extract low-volume fields that make LogQL verification practical."""
        if event_type == "step_start":
            return self._step_start_log_fields(data)
        if event_type == "deep_research_decision":
            return self._deep_decision_log_fields(data)
        if event_type == "step_complete":
            return self._step_complete_log_fields(data)
        return {}

    def _step_start_log_fields(self, data: dict[str, object]) -> dict[str, object]:
        """Summarize a started root or follow-up query for runtime logs."""
        queries = data.get("queries", [])
        return {
            "step": data.get("step"),
            "query": data.get("query"),
            "depth": data.get("depth"),
            "parent_query": data.get("parent_query", ""),
            "total": data.get("total"),
            "planned_query_count": len(queries) if isinstance(queries, list) else 0,
        }

    def _deep_decision_log_fields(self, data: dict[str, object]) -> dict[str, object]:
        """Summarize the evidence-gap decision for one query branch."""
        evidence_gaps = data.get("evidence_gaps", [])
        follow_up_queries = data.get("follow_up_queries", [])
        return {
            "step": data.get("step"),
            "query": data.get("query"),
            "depth": data.get("depth"),
            "parent_query": data.get("parent_query", ""),
            "should_continue": data.get("should_continue"),
            "reason": data.get("reason"),
            "evidence_gaps": evidence_gaps if isinstance(evidence_gaps, list) else [],
            "evidence_gap_count": (
                len(evidence_gaps) if isinstance(evidence_gaps, list) else 0
            ),
            "follow_up_queries": (
                follow_up_queries if isinstance(follow_up_queries, list) else []
            ),
            "follow_up_query_count": (
                len(follow_up_queries)
                if isinstance(follow_up_queries, list)
                else 0
            ),
            "stop_condition": data.get("stop_condition"),
        }

    def _step_complete_log_fields(self, data: dict[str, object]) -> dict[str, object]:
        """Summarize a completed query without logging large analysis text."""
        citations = data.get("citations", [])
        evidence_ids = data.get("evidence_ids", [])
        search_sources = data.get("search_sources", [])
        verification = data.get("verification", {})
        deep_research = data.get("deep_research", {})
        if not isinstance(verification, dict):
            verification = {}
        if not isinstance(deep_research, dict):
            deep_research = {}
        evidence_gaps = deep_research.get("evidence_gaps", [])
        follow_up_queries = deep_research.get("follow_up_queries", [])
        return {
            "step": data.get("step"),
            "query": data.get("title"),
            "depth": data.get("depth"),
            "parent_query": data.get("parent_query", ""),
            "status": data.get("status"),
            "citation_count": len(citations) if isinstance(citations, list) else 0,
            "evidence_count": len(evidence_ids) if isinstance(evidence_ids, list) else 0,
            "source_count": (
                len(search_sources) if isinstance(search_sources, list) else 0
            ),
            "verification_passed": verification.get("passed"),
            "verification_score": verification.get("score"),
            "should_continue": deep_research.get("should_continue"),
            "evidence_gap_count": (
                len(evidence_gaps) if isinstance(evidence_gaps, list) else 0
            ),
            "follow_up_query_count": (
                len(follow_up_queries)
                if isinstance(follow_up_queries, list)
                else 0
            ),
            "stop_condition": deep_research.get("stop_condition"),
        }

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
                    "status": str(getattr(source, "status", "")).strip(),
                    "failure_reason": str(getattr(source, "failure_reason", "")).strip(),
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
