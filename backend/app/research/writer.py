from __future__ import annotations

import logging

from ..agents.report_generator import ReportGenerator
from ..llms.deepseek_llm import DeepSeekLLM
from .cost_tracker import CostTracker
from .models import ResearchSource
from .models import SubQueryContext

logger = logging.getLogger(__name__)


class ResearchWriter:
    """Writes the final report from compressed research context."""

    def __init__(self, cost_tracker: CostTracker | None = None) -> None:
        self.llm = DeepSeekLLM()
        self.fallback_reporter = ReportGenerator()
        self.cost_tracker = cost_tracker

    async def write_report(
        self,
        *,
        query: str,
        context: list[SubQueryContext],
        sources: list[ResearchSource],
    ) -> str:
        prompt = f"""
你是 GPT Researcher 风格的 writer。请基于研究上下文写最终报告。

原始问题：
{query}

研究上下文：
{self._format_context(context)}

来源：
{self._format_sources(sources)}

请输出中文 Markdown 报告：
# {query} - 深度研究报告

## 执行摘要
## 关键发现
## 详细分析
## 来源与证据
## 研究限制
## 结论

要求：
- 客观，不能编造来源没有的信息
- 关键结论要带来源链接
- 信息不足时明确说明
"""
        try:
            response = await self.llm._acall(prompt)
            if self.cost_tracker is not None:
                self.cost_tracker.track_llm_call(
                    step="report_writing",
                    prompt=prompt,
                    response=response,
                )
            return response
        except Exception as exc:  # noqa: BLE001
            logger.warning("research writer failed: %s", exc)
            return await self.fallback_reporter.generate_final_report(
                self.to_legacy_results(context),
                query,
            )

    def _format_context(self, context: list[SubQueryContext]) -> str:
        return "\n\n".join(
            f"### {item.query}\n{item.context}" for item in context
        )[:12000]

    def _format_sources(self, sources: list[ResearchSource]) -> str:
        return "\n".join(
            f"- {source.title}: {source.link}" for source in sources[:12]
        )

    def to_legacy_results(
        self, context: list[SubQueryContext]
    ) -> list[dict[str, object]]:
        return [
            {
                "step": item.step,
                "title": item.query,
                "status": "completed",
                "analysis": item.context,
                "citations": [
                    {
                        "title": source.title,
                        "link": source.link,
                        "source": source.source,
                        "query": source.query,
                    }
                    for source in item.sources[:5]
                ],
                "search_sources": [
                    {
                        "title": source.title,
                        "link": source.link,
                        "source": source.source,
                        "query": source.query,
                    }
                    for source in item.sources
                ],
            }
            for item in context
        ]
