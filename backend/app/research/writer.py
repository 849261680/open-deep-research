from __future__ import annotations

import logging
from datetime import datetime
from datetime import timezone

from ..llms.deepseek_llm import DeepSeekLLM
from ..services.deepseek_service import DeepSeekConfig
from .cost_tracker import CostTracker
from .models import ResearchSource
from .models import SubQueryContext

logger = logging.getLogger(__name__)

# ── Prompt 模板 ──────────────────────────────────────────────────

REPORT_SYSTEM_ROLE = """\
你是一位资深研究分析师，擅长从多源信息中综合证据、对比观点、提炼洞察。你的核心原则：
1. 事实与推断严格区分——凡非来源明确支持的内容，必须标注为"分析"或"推断"
2. 多视角呈现——主动寻找并呈现对立或不同角度的观点
3. 证据链完整——关键论点必须附带来源引用
4. 诚实标注不确定性——信息不足时使用 [信息不足] 标记，绝不编造数据或来源\
"""

REPORT_PROMPT_TEMPLATE = """\
## 原始研究问题
{query}

## 各维度研究上下文
{context_block}

## 参考来源列表
{sources_block}

---

请基于以上研究上下文撰写深度研究报告。严格遵循以下结构和要求：

### 报告结构
1. **执行摘要**（200 字以内）：核心发现和结论概述
2. **背景与现状**：研究主题的背景、当前状态
3. **多维度分析**：按不同角度/维度展开详细分析，每个维度需：
   - 列出关键事实（标注来源编号，如 [来源1]）
   - 如有对立观点，必须同时呈现并标注来源
4. **关键发现与对比**：汇总各维度发现，对比不同来源的信息一致性
5. **争议与不确定性**：明确列出信息不足、存在争议或互相矛盾的领域，用 [信息不足] 标注
6. **趋势与展望**：基于证据的方向性判断（必须标注为"分析/推断"）
7. **结论与建议**：总结核心观点和行动建议
8. **参考来源**：按编号列出所有引用的来源，格式为 `[编号] 标题 - URL`

### 质量要求
- 每个关键论点必须附带至少一个来源引用
- 区分「事实」（来源明确支持）和「分析/推断」（基于证据的推理）
- 数值、日期、名称等必须与来源一致，不确定的加注 [待核实]
- 如某维度信息不足，不要猜测，直接写"当前研究未找到充分证据"并标注 [信息不足]
- 使用 Markdown 格式，善用标题、列表、表格增强可读性
- 总长度控制在 2000-4000 字
"""


class ResearchWriter:
    """Writes the final report from compressed research context."""

    def __init__(self, cost_tracker: CostTracker | None = None) -> None:
        self.llm = DeepSeekLLM()
        self.config = DeepSeekConfig.from_env()
        self.cost_tracker = cost_tracker

    async def write_report(
        self,
        *,
        query: str,
        context: list[SubQueryContext],
        sources: list[ResearchSource],
    ) -> str:
        context_block = self._format_context(context)
        sources_block = self._format_sources(sources)

        prompt = REPORT_PROMPT_TEMPLATE.format(
            query=query,
            context_block=context_block,
            sources_block=sources_block,
        )

        try:
            # 报告生成使用低 temperature 以减少幻觉
            response = await self.llm._acall(prompt, temperature=0.3)
            if self.cost_tracker is not None:
                self.cost_tracker.track_llm_call(
                    step="report_writing",
                    prompt=prompt,
                    response=response,
                )
            return response
        except Exception as exc:  # noqa: BLE001
            logger.warning("research writer failed: %s", exc)
            return self._fallback_report(query, context, sources)

    # ── 上下文格式化（动态 token 分配）──

    def _format_context(self, context: list[SubQueryContext]) -> str:
        """按子查询数量动态分配字符预算，而非硬截断。"""
        total_budget = self.config.max_prompt_chars
        # 预留：prompt 模板 (~2000) + 来源列表 (~2000) + 输出空间 (~4000)
        context_budget = max(total_budget - 8000, 4000)
        per_query_budget = context_budget // max(len(context), 1)

        parts: list[str] = []
        for item in context:
            section = f"### {item.query}\n{item.context}"
            if len(section) > per_query_budget:
                section = section[:per_query_budget] + "\n...[内容已截断]"
            parts.append(section)
        return "\n\n".join(parts)

    def _format_sources(self, sources: list[ResearchSource]) -> str:
        """格式化来源列表，上限提升到 20。"""
        lines: list[str] = []
        for idx, source in enumerate(sources[:20], start=1):
            lines.append(f"[{idx}] {source.title} - {source.link}")
        return "\n".join(lines)

    # ── Fallback：纯文本模板（不依赖 legacy chains）──

    def _fallback_report(
        self,
        query: str,
        context: list[SubQueryContext],
        sources: list[ResearchSource],
    ) -> str:
        """LLM 不可用时的纯文本报告回退。"""
        findings = []
        for item in context:
            findings.append(f"**{item.query}**:\n{item.context}")

        source_lines = []
        for idx, source in enumerate(sources[:10], start=1):
            source_lines.append(f"- [{idx}] {source.title}: {source.link}")

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"""\
# {query} - 研究报告

> ⚠️ 本报告由降级模式生成，可能缺乏深度分析。

## 主要发现

{"".join(findings)}

## 参考来源

{"".join(source_lines)}

## 研究限制

由于 LLM 服务暂时不可用，本报告仅包含压缩后的原始研究上下文，未经过深度分析和综合。

*报告生成时间: {now}*
"""

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
