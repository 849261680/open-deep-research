from __future__ import annotations

import json
import logging

from ..llms.deepseek_llm import DeepSeekLLM
from .cost_tracker import CostTracker
from .models import ResearchPlanItem
from .models import ResearchSource

logger = logging.getLogger(__name__)

QUERY_PLANNER_PROMPT = """\
你是一位研究策略专家。请根据用户的研究问题和初始搜索结果，从不同维度拆解出高价值的子查询。

## 用户问题
{query}

## 初始搜索结果
{initial_results_block}

## 要求
- 生成最多 {max_sub_queries} 个研究计划项
- 每个计划项必须覆盖**不同的研究维度**，例如：
  - 时间线（历史演进 / 最新进展）
  - 地域差异（不同国家/地区的情况）
  - 利弊分析（优势、风险、挑战）
  - 案例研究（具体实例、典型场景）
  - 数据趋势（量化指标、市场数据、统计）
  - 对比视角（不同学派/利益方的观点差异）
- title 必须是**可直接用于搜索引擎的具体问题**，不要泛泛的"总结/分析"
- dimension 必须说明研究维度
- rationale 必须说明为什么需要研究这一项
- search_queries 必须给出 1-3 个可执行搜索语句
- expected_outcome 必须说明这一项要产出的结论或证据
- evidence_targets 必须说明需要找的证据类型，例如统计数据、官方文档、案例、论文、新闻报道
- 不要与原始问题完全重复
- 只返回 JSON，不要解释

## 返回格式
{{
  "plan_items": [
    {{
      "title": "具体子查询",
      "dimension": "研究维度",
      "rationale": "拆分理由",
      "search_queries": ["搜索语句1", "搜索语句2"],
      "expected_outcome": "预期产出",
      "evidence_targets": ["证据类型1", "证据类型2"]
    }}
  ]
}}\
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
        plan_items = await self.plan_detailed(
            query=query,
            initial_results=initial_results,
            max_sub_queries=max_sub_queries,
        )
        return [item.title for item in plan_items]

    async def plan_detailed(
        self,
        *,
        query: str,
        initial_results: list[ResearchSource],
        max_sub_queries: int = 5,
    ) -> list[ResearchPlanItem]:
        """Return structured research plan items with strategy metadata."""
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
            plan_items = self._parse_plan_items(response, max_sub_queries)
            if plan_items:
                return plan_items
        except Exception as exc:  # noqa: BLE001
            logger.warning("sub-query planning failed: %s", exc)
        return self._fallback_plan_items(query, max_sub_queries)

    def _format_initial_results(self, results: list[ResearchSource]) -> str:
        if not results:
            return "（无初始搜索结果）"
        return "\n".join(
            f"- {source.title}: {source.snippet} ({source.link})"
            for source in results[:8]
        )

    def _parse_sub_queries(self, response: str, max_sub_queries: int) -> list[str]:
        """Parse legacy sub-query strings from an LLM response."""
        return [
            item.title
            for item in self._parse_plan_items(response, max_sub_queries)
        ]

    def _parse_plan_items(
        self,
        response: str,
        max_sub_queries: int,
    ) -> list[ResearchPlanItem]:
        """Parse structured plan items or legacy sub-query JSON."""
        text = response.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, dict):
            return []
        raw_items = parsed.get("plan_items")
        if isinstance(raw_items, list):
            return self._normalize_plan_items(raw_items, max_sub_queries)
        raw_queries = parsed.get("sub_queries", [])
        if isinstance(raw_queries, list):
            return self._legacy_queries_to_plan_items(raw_queries, max_sub_queries)
        return []

    def _normalize_plan_items(
        self,
        raw_items: list[object],
        max_sub_queries: int,
    ) -> list[ResearchPlanItem]:
        """Normalize detailed plan item dictionaries from the LLM."""
        plan_items: list[ResearchPlanItem] = []
        seen: set[str] = set()
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            title = self._clean_text(raw_item.get("title", ""), 180)
            if not title or title in seen:
                continue
            seen.add(title)
            plan_items.append(
                ResearchPlanItem(
                    step=len(plan_items) + 1,
                    title=title,
                    dimension=self._clean_text(raw_item.get("dimension", ""), 80),
                    rationale=self._clean_text(raw_item.get("rationale", ""), 240),
                    search_queries=self._clean_list(raw_item.get("search_queries", []), 3),
                    expected_outcome=self._clean_text(
                        raw_item.get("expected_outcome", ""),
                        240,
                    ),
                    evidence_targets=self._clean_list(
                        raw_item.get("evidence_targets", []),
                        5,
                    ),
                )
            )
            if len(plan_items) >= max_sub_queries:
                break
        return plan_items

    def _fallback_sub_queries(self, query: str, max_sub_queries: int) -> list[str]:
        """LLM 不可用时，基于原始查询动态生成不同维度的子查询。"""
        return [item.title for item in self._fallback_plan_items(query, max_sub_queries)]

    def _fallback_plan_items(
        self,
        query: str,
        max_sub_queries: int,
    ) -> list[ResearchPlanItem]:
        """Build structured fallback plan items when the LLM planner fails."""
        candidates = [
            (
                query,
                "核心问题",
                "保留原始问题，确保最终报告直接回答用户。",
                [query],
                "形成对原始问题的直接回答。",
                ["综合资料", "权威来源"],
            ),
            (
                f"{query} 历史发展 最新进展",
                "时间线",
                "判断主题的发展阶段和最新变化。",
                [f"{query} 历史发展", f"{query} 最新进展"],
                "获得关键时间节点和近期变化。",
                ["新闻报道", "官方公告", "行业报告"],
            ),
            (
                f"{query} 优势 风险 挑战",
                "利弊分析",
                "识别正反两面的核心论据。",
                [f"{query} 优势", f"{query} 风险 挑战"],
                "形成优势、风险和约束条件清单。",
                ["案例", "专家观点", "风险报告"],
            ),
            (
                f"{query} 典型案例 实际应用",
                "案例研究",
                "用具体实例验证抽象判断。",
                [f"{query} 典型案例", f"{query} 实际应用"],
                "获得可引用的实际案例。",
                ["案例研究", "客户故事", "产品文档"],
            ),
            (
                f"{query} 数据统计 市场趋势",
                "数据趋势",
                "用量化数据支撑趋势判断。",
                [f"{query} 数据统计", f"{query} 市场趋势"],
                "获得统计口径、趋势数据和样本来源。",
                ["统计数据", "行业报告", "市场数据"],
            ),
            (
                f"{query} 不同观点 争议 辩论",
                "对比视角",
                "避免单一观点，呈现争议和不确定性。",
                [f"{query} 不同观点", f"{query} 争议 辩论"],
                "获得支持与反对观点及其证据。",
                ["评论文章", "论文", "专家观点"],
            ),
        ]
        return [
            ResearchPlanItem(
                step=index,
                title=title,
                dimension=dimension,
                rationale=rationale,
                search_queries=search_queries,
                expected_outcome=expected_outcome,
                evidence_targets=evidence_targets,
            )
            for index, (
                title,
                dimension,
                rationale,
                search_queries,
                expected_outcome,
                evidence_targets,
            ) in enumerate(candidates[:max_sub_queries], start=1)
        ]

    def _legacy_queries_to_plan_items(
        self,
        raw_queries: list[object],
        max_sub_queries: int,
    ) -> list[ResearchPlanItem]:
        """Convert old sub-query strings into structured plan items."""
        plan_items: list[ResearchPlanItem] = []
        seen: set[str] = set()
        for raw_query in raw_queries:
            title = self._clean_text(raw_query, 180)
            if not title or title in seen:
                continue
            seen.add(title)
            plan_items.append(
                ResearchPlanItem(
                    step=len(plan_items) + 1,
                    title=title,
                    dimension="未分类维度",
                    rationale="兼容旧格式子查询。",
                    search_queries=[title],
                    expected_outcome="收集并压缩与该子查询相关的上下文。",
                    evidence_targets=["网页资料"],
                )
            )
            if len(plan_items) >= max_sub_queries:
                break
        return plan_items

    def _clean_text(self, value: object, max_length: int) -> str:
        """Normalize one text field from LLM output."""
        return " ".join(str(value).split())[:max_length]

    def _clean_list(self, value: object, max_items: int) -> list[str]:
        """Normalize one string list from LLM output."""
        if not isinstance(value, list):
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = self._clean_text(item, 180)
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(text)
            if len(cleaned) >= max_items:
                break
        return cleaned
