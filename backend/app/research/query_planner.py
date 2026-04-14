from __future__ import annotations

import json
import logging

from ..llms.deepseek_llm import DeepSeekLLM
from .cost_tracker import CostTracker
from .models import ResearchSource

logger = logging.getLogger(__name__)

QUERY_PLANNER_PROMPT = """\
你是一位研究策略专家。请根据用户的研究问题和初始搜索结果，从不同维度拆解出高价值的子查询。

## 用户问题
{query}

## 初始搜索结果
{initial_results_block}

## 要求
- 生成最多 {max_sub_queries} 个子查询
- 每个子查询必须覆盖**不同的研究维度**，例如：
  - 时间线（历史演进 / 最新进展）
  - 地域差异（不同国家/地区的情况）
  - 利弊分析（优势、风险、挑战）
  - 案例研究（具体实例、典型场景）
  - 数据趋势（量化指标、市场数据、统计）
  - 对比视角（不同学派/利益方的观点差异）
- 子查询必须是**可直接用于搜索引擎的具体问题**，不要泛泛的"总结/分析"
- 不要与原始问题完全重复
- 只返回 JSON，不要解释

## 返回格式
{{"sub_queries": ["具体子查询1", "具体子查询2", ...]}}\
"""


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
        max_sub_queries: int = 5,
    ) -> list[str]:
        prompt = QUERY_PLANNER_PROMPT.format(
            query=query,
            initial_results_block=self._format_initial_results(initial_results),
            max_sub_queries=max_sub_queries,
        )
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
        if not results:
            return "（无初始搜索结果）"
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
        """LLM 不可用时，基于原始查询动态生成不同维度的子查询。"""
        candidates = [
            query,
            f"{query} 历史发展 最新进展",
            f"{query} 优势 风险 挑战",
            f"{query} 典型案例 实际应用",
            f"{query} 数据统计 市场趋势",
            f"{query} 不同观点 争议 辩论",
        ]
        return candidates[:max_sub_queries]
