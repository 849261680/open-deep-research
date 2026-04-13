from __future__ import annotations

import json
import logging

from ..llms.deepseek_llm import DeepSeekLLM
from .cost_tracker import CostTracker
from .models import ResearchSource

logger = logging.getLogger(__name__)


class QueryPlanner:
    """Plans sub-queries after an initial search, matching GPT Researcher flow."""

    def __init__(self, cost_tracker: CostTracker | None = None) -> None:
        self.llm = DeepSeekLLM()
        self.cost_tracker = cost_tracker

    async def plan(
        self,
        *,
        query: str,
        initial_results: list[ResearchSource],
        max_sub_queries: int = 3,
    ) -> list[str]:
        prompt = f"""
你是 GPT Researcher 风格的 query planner。请基于用户问题和初始搜索结果生成子查询。

用户问题：
{query}

初始搜索结果：
{self._format_initial_results(initial_results)}

要求：
- 生成 {max_sub_queries} 个以内的 sub_queries
- 每个 sub_query 应覆盖不同研究角度
- 不要返回泛泛的“总结/分析”，要能直接搜索
- 只返回 JSON，不要解释

返回格式：
{{"sub_queries": ["query 1", "query 2"]}}
"""
        try:
            response = await self.llm._acall(prompt)
            if self.cost_tracker is not None:
                self.cost_tracker.track_llm_call(
                    step="query_planning",
                    prompt=prompt,
                    response=response,
                )
            sub_queries = self._parse_sub_queries(response, max_sub_queries)
            if sub_queries:
                return sub_queries
        except Exception as exc:  # noqa: BLE001
            logger.warning("sub-query planning failed: %s", exc)
        return self._fallback_sub_queries(query, max_sub_queries)

    def _format_initial_results(self, results: list[ResearchSource]) -> str:
        return "\n".join(
            f"- {source.title}: {source.snippet} ({source.link})"
            for source in results[:8]
        )

    def _parse_sub_queries(self, response: str, max_sub_queries: int) -> list[str]:
        text = response.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        raw_queries = parsed.get("sub_queries", []) if isinstance(parsed, dict) else []
        sub_queries: list[str] = []
        seen: set[str] = set()
        for raw_query in raw_queries:
            if not isinstance(raw_query, str):
                continue
            cleaned = " ".join(raw_query.split())[:180]
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            sub_queries.append(cleaned)
            if len(sub_queries) >= max_sub_queries:
                break
        return sub_queries

    def _fallback_sub_queries(self, query: str, max_sub_queries: int) -> list[str]:
        candidates = [
            query,
            f"{query} 背景 现状",
            f"{query} 风险 挑战",
            f"{query} 对比 案例",
        ]
        return candidates[:max_sub_queries]
