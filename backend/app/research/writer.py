from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from datetime import timezone

from ..llms.deepseek_llm import DeepSeekLLM
from ..models.research_task import ResearchSection
from ..services.deepseek_service import DeepSeekConfig
from .config import ResearchConfig
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

## 报告配置
报告类型：{report_type}
语气：{tone}

---

请基于以上研究上下文撰写深度研究报告。严格遵循以下结构和要求：

### 报告结构
1. **执行摘要**（200 字以内）：核心发现和结论概述
2. **背景与现状**：研究主题的背景、当前状态
3. **多维度分析**：按不同角度/维度展开详细分析，每个维度需：
   - 列出关键事实（标注来源编号，如 [1]、[2]）
   - 如有对立观点，必须同时呈现并标注来源
4. **关键发现与对比**：汇总各维度发现，对比不同来源的信息一致性
5. **争议与不确定性**：明确列出信息不足、存在争议或互相矛盾的领域，用 [信息不足] 标注
6. **趋势与展望**：基于证据的方向性判断（必须标注为"分析/推断"）
7. **结论与建议**：总结核心观点和行动建议
8. **参考来源**：按编号逐条列出所有引用的来源，格式为 `- [编号] 标题 - URL`

### 质量要求
- 每个关键论点必须附带至少一个来源引用
- 只能使用“参考来源列表”中已经存在的编号，不要编造新的来源编号
- 区分「事实」（来源明确支持）和「分析/推断」（基于证据的推理）
- 数值、日期、名称等必须与来源一致，不确定的加注 [待核实]
- 如某维度信息不足，不要猜测，直接写"当前研究未找到充分证据"并标注 [信息不足]
- 使用 Markdown 格式，善用标题、列表、表格增强可读性
- 总长度控制在 2000-4000 字
"""


class ResearchWriter:
    """Writes the final report from compressed research context."""

    def __init__(
        self,
        cost_tracker: CostTracker | None = None,
        config: ResearchConfig | None = None,
    ) -> None:
        self.llm = DeepSeekLLM()
        self.config = DeepSeekConfig.from_env()
        self.research_config = config or ResearchConfig.from_env()
        self.cost_tracker = cost_tracker

    async def write_report(
        self,
        *,
        query: str,
        sections: list[ResearchSection],
        context: list[SubQueryContext],
        sources: list[ResearchSource],
    ) -> str:
        reference_entries = self._collect_reference_entries(sources, sections, context)
        source_index = self._build_source_index(reference_entries)
        context_block = self._format_context(sections, context, source_index)
        sources_block = self._format_sources(reference_entries)

        prompt = REPORT_PROMPT_TEMPLATE.format(
            query=query,
            context_block=context_block,
            sources_block=sources_block,
            report_type=self.research_config.report_type,
            tone=self.research_config.tone,
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
            return self._replace_reference_section(response, reference_entries)
        except Exception as exc:  # noqa: BLE001
            logger.warning("research writer failed: %s", exc)
            return self._fallback_report(query, sections, context, sources)

    async def evaluate_claim_support(
        self,
        report: str,
        reference_entries: list[dict[str, str]],
    ) -> dict[str, object]:
        """Build claim-level citation support checks for a final report."""
        valid_numbers = {
            index
            for index, entry in enumerate(reference_entries[:20], start=1)
            if entry.get("link")
        }
        claims = [
            self._claim_support_record(claim, valid_numbers, reference_entries)
            for claim in self._extract_report_claims(report)
        ]
        self._apply_semantic_claim_support(
            claims,
            await self._semantic_claim_support(claims),
        )
        supported_count = sum(
            1 for claim in claims if claim["citation_support"] == "supported"
        )
        partial_count = sum(
            1 for claim in claims if claim["citation_support"] == "partially_supported"
        )
        unsupported_count = sum(
            1 for claim in claims if claim["citation_support"] == "unsupported"
        )
        return {
            "claims": claims,
            "summary": {
                "claim_count": len(claims),
                "supported_claim_count": supported_count,
                "partially_supported_claim_count": partial_count,
                "unsupported_claim_count": unsupported_count,
                "citation_support_rate": self._support_rate(
                    supported_count,
                    partial_count,
                    unsupported_count,
                ),
            },
        }

    def _extract_report_claims(self, report: str) -> list[str]:
        """Extract likely factual claims from the report body."""
        body = self._report_without_references(report)
        chunks = re.split(r"(?<=[。！？.!?])\s*|\n+", body)
        claims: list[str] = []
        for chunk in chunks:
            claim = self._clean_claim_text(chunk)
            if not claim or self._should_skip_claim(claim):
                continue
            claims.append(claim)
        return claims[:80]

    def _report_without_references(self, report: str) -> str:
        """Remove the deterministic reference section before checking claims."""
        pattern = re.compile(
            r"(?im)^#{0,6}\s*(?:8[.、]\s*)?\*{0,2}参考来源\*{0,2}\s*$"
        )
        match = pattern.search(report)
        return report[: match.start()] if match else report

    def _clean_claim_text(self, text: str) -> str:
        """Normalize one claim candidate from Markdown text."""
        cleaned = text.strip()
        cleaned = re.sub(r"^#{1,6}\s*", "", cleaned)
        cleaned = re.sub(r"^[-*]\s+", "", cleaned)
        cleaned = re.sub(r"^\d+[.、]\s*", "", cleaned)
        return cleaned.strip()

    def _should_skip_claim(self, claim: str) -> bool:
        """Skip headings and fragments that are too small to audit."""
        if len(claim) < 12:
            return True
        if claim.startswith("|") and claim.endswith("|"):
            return True
        normalized = claim.strip("*：: ")
        return normalized in {
            "执行摘要",
            "背景与现状",
            "多维度分析",
            "关键发现与对比",
            "争议与不确定性",
            "趋势与展望",
            "结论与建议",
        }

    def _claim_support_record(
        self,
        claim: str,
        valid_numbers: set[int],
        reference_entries: list[dict[str, str]],
    ) -> dict[str, object]:
        """Classify one claim by whether its citation numbers are valid."""
        citation_numbers = self._citation_numbers(claim)
        valid_citations = [number for number in citation_numbers if number in valid_numbers]
        invalid_citations = [
            number for number in citation_numbers if number not in valid_numbers
        ]
        if citation_numbers and not invalid_citations:
            status = "supported"
            reason = "引用编号存在于参考来源列表"
        elif valid_citations:
            status = "partially_supported"
            reason = "部分引用编号不存在于参考来源列表"
        else:
            status = "unsupported"
            reason = "缺少有效引用编号" if citation_numbers else "缺少引用编号"
        return {
            "text": claim,
            "citation_numbers": citation_numbers,
            "citation_support": status,
            "reason": reason,
            "citations": [
                reference_entries[number - 1]
                for number in valid_citations
                if 0 < number <= len(reference_entries)
            ],
        }

    async def _semantic_claim_support(
        self,
        claims: list[dict[str, object]],
    ) -> dict[int, dict[str, str]]:
        """Ask the LLM to judge cited claims against available source text."""
        candidates = self._semantic_claim_candidates(claims)
        if not candidates:
            return {}
        prompt = self._semantic_claim_prompt(candidates)
        try:
            response = await self.llm._acall(prompt, temperature=0.0)
            if self.cost_tracker is not None:
                self.cost_tracker.track_llm_call(
                    step="claim_support_validation",
                    prompt=prompt,
                    response=response,
                )
            parsed = self._parse_json(response)
        except Exception as exc:  # noqa: BLE001
            logger.warning("claim support validation failed: %s", exc)
            return {}
        if not isinstance(parsed, dict):
            return {}
        raw_claims = parsed.get("claims", [])
        if not isinstance(raw_claims, list):
            return {}
        results: dict[int, dict[str, str]] = {}
        for item in raw_claims:
            if not isinstance(item, dict):
                continue
            claim_index = item.get("claim_index")
            status = str(item.get("citation_support", "")).strip()
            reason = str(item.get("reason", "")).strip()
            if not isinstance(claim_index, int):
                continue
            if status not in {"supported", "partially_supported", "unsupported"}:
                continue
            results[claim_index] = {
                "citation_support": status,
                "reason": reason or "语义校验未给出原因",
            }
        return results

    def _semantic_claim_candidates(
        self,
        claims: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Build compact semantic validation inputs for claims with source text."""
        candidates: list[dict[str, object]] = []
        for index, claim in enumerate(claims):
            if claim.get("citation_support") == "unsupported":
                continue
            citations = claim.get("citations", [])
            if not isinstance(citations, list):
                continue
            evidence = []
            for citation in citations[:3]:
                if not isinstance(citation, dict):
                    continue
                source_text = self._reference_text(citation)
                if source_text:
                    evidence.append(
                        {
                            "title": str(citation.get("title", "")),
                            "link": str(citation.get("link", "")),
                            "text": source_text,
                        }
                    )
            if evidence:
                candidates.append(
                    {
                        "claim_index": index,
                        "claim": str(claim.get("text", "")),
                        "evidence": evidence,
                    }
                )
        return candidates[:20]

    def _semantic_claim_prompt(self, candidates: list[dict[str, object]]) -> str:
        """Render a compact JSON-only semantic citation validation prompt."""
        payload = json.dumps(candidates, ensure_ascii=False)
        return f"""\
你是引用质量审校员。请逐条判断断言是否被其引用来源文本语义支持。

判定标准：
- supported：来源文本明确支持断言中的核心事实、数值、时间和主体。
- partially_supported：来源文本只支持部分事实，或断言有轻微外推但不完全无关。
- unsupported：来源文本缺少核心事实、与断言矛盾，或无法证明断言。

待校验断言 JSON：
{payload}

只返回 JSON，不要解释：
{{
  "claims": [
    {{
      "claim_index": 0,
      "citation_support": "supported",
      "reason": "一句话说明"
    }}
  ]
}}
"""

    def _apply_semantic_claim_support(
        self,
        claims: list[dict[str, object]],
        semantic_results: dict[int, dict[str, str]],
    ) -> None:
        """Overlay semantic validation results onto citation-number records."""
        for index, result in semantic_results.items():
            if index < 0 or index >= len(claims):
                continue
            claims[index]["citation_support"] = result["citation_support"]
            claims[index]["reason"] = result["reason"]
            claims[index]["support_method"] = "llm_semantic"

    def _reference_text(self, citation: dict[str, object]) -> str:
        """Return compact source text for semantic validation."""
        for key in ("source_text", "extracted_content", "summary", "snippet"):
            value = str(citation.get(key, "")).strip()
            if value:
                return value[:1600]
        return ""

    def _parse_json(self, response: str) -> dict[str, object] | None:
        """Parse a JSON object from plain or fenced LLM output."""
        text = response.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _citation_numbers(self, claim: str) -> list[int]:
        """Return unique bracket citation numbers from one claim."""
        numbers: list[int] = []
        seen: set[int] = set()
        for match in re.finditer(r"\[(\d+)\]", claim):
            number = int(match.group(1))
            if number in seen:
                continue
            seen.add(number)
            numbers.append(number)
        return numbers

    def _support_rate(
        self,
        supported_count: int,
        partial_count: int,
        unsupported_count: int,
    ) -> float:
        """Score full support as 1.0 and partial support as 0.5."""
        total = supported_count + partial_count + unsupported_count
        if total == 0:
            return 0.0
        return round((supported_count + 0.5 * partial_count) / total, 4)

    # ── 上下文格式化（动态 token 分配）──

    def _format_context(
        self,
        sections: list[ResearchSection],
        context: list[SubQueryContext],
        source_index: dict[str, int],
    ) -> str:
        """优先使用已完成 sections，保留证据、校验和引用信息。"""
        section_inputs = self._section_prompt_inputs(sections, context)
        total_budget = self.config.max_prompt_chars
        # 预留：prompt 模板 (~2000) + 来源列表 (~2000) + 输出空间 (~4000)
        context_budget = max(total_budget - 8000, 4000)
        per_query_budget = context_budget // max(len(section_inputs), 1)

        parts: list[str] = []
        for item in section_inputs:
            section = self._render_section_prompt_block(item, source_index)
            if len(section) > per_query_budget:
                section = section[:per_query_budget] + "\n...[内容已截断]"
            parts.append(section)
        return "\n\n".join(parts)

    def _section_prompt_inputs(
        self,
        sections: list[ResearchSection],
        context: list[SubQueryContext],
    ) -> list[dict[str, object]]:
        if sections:
            return [
                {
                    "title": section.title,
                    "analysis": section.analysis,
                    "compressed_evidence": section.compressed_evidence,
                    "verification": section.verification,
                    "deep_research_reason": section.deep_research_reason,
                    "deep_research_stop_condition": section.deep_research_stop_condition,
                    "evidence_gaps": section.evidence_gaps,
                    "follow_up_queries": section.follow_up_queries,
                    "citations": section.citations,
                    "status": section.status,
                }
                for section in sections
            ]

        return [
            {
                "title": item.query,
                "analysis": item.context,
                "compressed_evidence": item.compressed_evidence,
                "verification": item.verification,
                "deep_research_reason": item.deep_research.reason,
                "deep_research_stop_condition": item.deep_research.stop_condition,
                "evidence_gaps": item.deep_research.evidence_gaps,
                "follow_up_queries": item.deep_research.follow_up_queries,
                "citations": item.citations,
                "status": "completed",
            }
            for item in context
        ]

    def _render_section_prompt_block(
        self,
        item: dict[str, object],
        source_index: dict[str, int],
    ) -> str:
        title = str(item.get("title", "未命名章节"))
        status = str(item.get("status", "unknown"))
        analysis = str(item.get("analysis", "")).strip() or "[信息不足]"
        compressed_evidence = str(item.get("compressed_evidence", "")).strip() or "[无证据摘要]"
        verification = item.get("verification", {})
        verification_text = self._format_verification_summary(verification)
        deep_research_text = self._format_deep_research_summary(item)
        citations = item.get("citations", [])
        citation_text = self._format_section_citations(citations, source_index)
        return (
            f"### {title}\n"
            f"- 状态: {status}\n"
            f"- 校验: {verification_text}\n"
            f"- 深挖记录: {deep_research_text}\n"
            f"- 分析摘要:\n{analysis}\n\n"
            f"- 证据压缩:\n{compressed_evidence}\n\n"
            f"- 章节引用编号:\n{citation_text}"
        )

    def _format_deep_research_summary(self, item: dict[str, object]) -> str:
        """Render evidence-gap follow-up decisions for the report writer prompt."""
        reason = str(item.get("deep_research_reason", "")).strip()
        stop_condition = str(item.get("deep_research_stop_condition", "")).strip()
        evidence_gaps = item.get("evidence_gaps", [])
        follow_up_queries = item.get("follow_up_queries", [])
        parts: list[str] = []
        if reason:
            parts.append(f"理由={reason}")
        if isinstance(evidence_gaps, list) and evidence_gaps:
            parts.append("证据缺口=" + "；".join(str(gap) for gap in evidence_gaps))
        if isinstance(follow_up_queries, list) and follow_up_queries:
            parts.append(
                "后续查询=" + "；".join(str(query) for query in follow_up_queries)
            )
        if stop_condition:
            parts.append(f"停止条件={stop_condition}")
        return "；".join(parts) if parts else "无额外深挖"

    def _format_verification_summary(self, verification: object) -> str:
        if not isinstance(verification, dict) or not verification:
            return "未校验"

        status = "通过" if verification.get("passed") else "需复核"
        score = verification.get("score")
        summary = str(verification.get("summary", "")).strip()
        parts = [status]
        if isinstance(score, int | float):
            parts.append(f"score={float(score):.2f}")
        if summary:
            parts.append(summary)
        return " | ".join(parts)

    def _format_section_citations(
        self,
        citations: object,
        source_index: dict[str, int],
    ) -> str:
        if not isinstance(citations, list) or not citations:
            return "[无引用]"

        lines: list[str] = []
        for citation in citations[:5]:
            if hasattr(citation, "title") and hasattr(citation, "link"):
                title = str(citation.title)
                link = str(citation.link)
            elif isinstance(citation, dict):
                title = str(citation.get("title", ""))
                link = str(citation.get("link", ""))
            else:
                continue
            if not link:
                continue
            number = source_index.get(link)
            label = f"[{number}] " if number is not None else ""
            lines.append(f"- {label}{title or link}: {link}")
        return "\n".join(lines) if lines else "[无引用]"

    def _format_sources(self, reference_entries: list[dict[str, str]]) -> str:
        """格式化来源列表，上限提升到 20。"""
        lines: list[str] = []
        for idx, entry in enumerate(reference_entries[:20], start=1):
            lines.append(f"- [{idx}] {entry['title']} - {entry['link']}")
        return "\n".join(lines)

    def _replace_reference_section(
        self,
        report: str,
        reference_entries: list[dict[str, str]],
    ) -> str:
        """Replace model-written references with the deterministic source list."""
        source_lines = self._format_sources(reference_entries)
        if not source_lines:
            source_lines = "无可引用来源。"
        reference_section = f"## 8. 参考来源\n\n{source_lines}"
        pattern = re.compile(
            r"(?im)^#{0,6}\s*(?:8[.、]\s*)?\*{0,2}参考来源\*{0,2}\s*$"
        )
        match = pattern.search(report)
        if match is None:
            return f"{report.rstrip()}\n\n{reference_section}"
        return f"{report[:match.start()].rstrip()}\n\n{reference_section}"

    def _collect_reference_entries(
        self,
        sources: list[ResearchSource],
        sections: list[ResearchSection],
        context: list[SubQueryContext],
    ) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        seen_links: set[str] = set()

        for source in sources:
            self._append_reference_entry(
                entries,
                seen_links,
                title=source.title,
                link=source.link,
                source_text=self._source_text_from_source(source),
            )

        for item in context:
            for source in item.sources:
                self._append_reference_entry(
                    entries,
                    seen_links,
                    title=source.title,
                    link=source.link,
                    source_text=self._source_text_from_source(source),
                )

        for citation in self._iter_all_citations(sections, context):
            self._append_reference_entry(
                entries,
                seen_links,
                title=str(citation.get("title", "")),
                link=str(citation.get("link", "")),
            )

        return entries

    def _iter_all_citations(
        self,
        sections: list[ResearchSection],
        context: list[SubQueryContext],
    ) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        if sections:
            for section in sections:
                for citation in section.citations:
                    items.append(
                        {
                            "title": citation.title,
                            "link": citation.link,
                        }
                    )
            return items

        for item in context:
            for citation in item.citations:
                items.append(
                    {
                        "title": citation.title,
                        "link": citation.link,
                    }
                )
        return items

    def _append_reference_entry(
        self,
        entries: list[dict[str, str]],
        seen_links: set[str],
        *,
        title: str,
        link: str,
        source_text: str = "",
    ) -> None:
        normalized_link = link.strip()
        if not normalized_link:
            return
        if normalized_link in seen_links:
            self._fill_reference_text(entries, normalized_link, source_text)
            return
        seen_links.add(normalized_link)
        entry = {
            "title": title.strip() or normalized_link,
            "link": normalized_link,
        }
        text = source_text.strip()
        if text:
            entry["source_text"] = text
        entries.append(entry)

    def _fill_reference_text(
        self,
        entries: list[dict[str, str]],
        link: str,
        source_text: str,
    ) -> None:
        """Backfill source text when a later duplicate has richer evidence."""
        text = source_text.strip()
        if not text:
            return
        for entry in entries:
            if entry.get("link") == link and not entry.get("source_text"):
                entry["source_text"] = text
                return

    def _source_text_from_source(self, source: ResearchSource) -> str:
        """Build compact validation text from a research source."""
        parts = [
            source.extracted_content.strip(),
            source.summary.strip(),
            source.snippet.strip(),
        ]
        return "\n".join(part for part in parts if part)[:2400]

    def _build_source_index(self, reference_entries: list[dict[str, str]]) -> dict[str, int]:
        return {
            entry["link"]: index
            for index, entry in enumerate(reference_entries[:20], start=1)
            if entry.get("link")
        }

    # ── Fallback：纯文本模板（不依赖 legacy chains）──

    def _fallback_report(
        self,
        query: str,
        sections: list[ResearchSection],
        context: list[SubQueryContext],
        sources: list[ResearchSource],
    ) -> str:
        """LLM 不可用时的纯文本报告回退。"""
        findings = []
        section_inputs = self._section_prompt_inputs(sections, context)
        reference_entries = self._collect_reference_entries(sources, sections, context)
        source_index = self._build_source_index(reference_entries)
        for item in section_inputs:
            findings.append(
                f"## {item['title']}\n\n"
                f"**分析摘要**\n{item['analysis']}\n\n"
                f"**证据压缩**\n{item['compressed_evidence']}\n\n"
                f"**校验结果**\n{self._format_verification_summary(item['verification'])}\n\n"
                f"**引用来源**\n{self._format_section_citations(item['citations'], source_index)}"
            )

        source_lines = []
        for idx, entry in enumerate(reference_entries[:10], start=1):
            source_lines.append(f"- [{idx}] {entry['title']}: {entry['link']}")
        findings_block = "\n\n".join(findings)
        source_lines_block = "\n".join(source_lines)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"""\
# {query} - 研究报告

> ⚠️ 本报告由降级模式生成，可能缺乏深度分析。

## 主要发现

{findings_block}

## 参考来源

{source_lines_block}

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
                "depth": item.depth,
                "parent_query": item.parent_query,
                "analysis": item.context,
                "citations": [citation.model_dump() for citation in item.citations],
                "evidence_ids": item.evidence_ids,
                "compressed_evidence": item.compressed_evidence,
                "verification": item.verification,
                "source_summary": item.source_summary,
                "deep_research": item.deep_research.model_dump(),
                "search_sources": [
                    {
                        "title": source.title,
                        "link": source.link,
                        "source": source.source,
                        "query": source.query,
                        "status": source.status,
                        "failure_reason": source.failure_reason,
                    }
                    for source in item.sources
                ],
            }
            for item in context
        ]
