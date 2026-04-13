from __future__ import annotations

import logging

from ..llms.deepseek_llm import DeepSeekLLM
from .cost_tracker import CostTracker
from .models import ResearchSource

logger = logging.getLogger(__name__)


class ResearchContextManager:
    """Compresses scraped source content into query-relevant context."""

    def __init__(self, cost_tracker: CostTracker | None = None) -> None:
        self.llm = DeepSeekLLM()
        self.cost_tracker = cost_tracker

    async def get_context(self, query: str, sources: list[ResearchSource]) -> str:
        if not sources:
            return ""

        source_text = "\n\n".join(
            f"Title: {source.title}\n"
            f"URL: {source.link}\n"
            f"Snippet: {source.snippet}\n"
            f"Content: {(source.extracted_content or source.snippet)[:1800]}"
            for source in sources
        )
        prompt = f"""
请从下面网页内容中提取与研究查询最相关的上下文。

研究查询：
{query}

网页内容：
{source_text[:9000]}

要求：
- 只保留能支持研究报告的事实、数据、观点和限制
- 每条重要信息尽量保留来源 URL
- 删除重复和无关内容
- 中文输出，结构化列点
"""
        try:
            response = await self.llm._acall(prompt)
            if self.cost_tracker is not None:
                self.cost_tracker.track_llm_call(
                    step="context_compression",
                    prompt=prompt,
                    response=response,
                )
            return response
        except Exception as exc:  # noqa: BLE001
            logger.warning("context compression failed: %s", exc)
            return "\n\n".join(
                f"{source.title}: {source.snippet} ({source.link})"
                for source in sources
            )
