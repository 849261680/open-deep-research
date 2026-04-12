from __future__ import annotations

import json
import logging

from ..llms.deepseek_llm import DeepSeekLLM

logger = logging.getLogger(__name__)
from ..models.research_task import Citation


class VerifierService:
    """Critic pass for section outputs with deterministic fallback."""

    def __init__(self) -> None:
        self.llm = DeepSeekLLM()

    async def verify_section(
        self,
        *,
        analysis: str,
        citations: list[Citation],
        compressed_evidence: str,
    ) -> dict[str, object]:
        llm_result = await self._verify_with_llm(
            analysis=analysis,
            citations=citations,
            compressed_evidence=compressed_evidence,
        )
        if llm_result is not None:
            return llm_result
        return self._deterministic_verify(
            analysis=analysis,
            citations=citations,
            compressed_evidence=compressed_evidence,
        )

    async def _verify_with_llm(
        self,
        *,
        analysis: str,
        citations: list[Citation],
        compressed_evidence: str,
    ) -> dict[str, object] | None:
        if not analysis.strip() or not compressed_evidence.strip():
            return None

        citation_text = "\n".join(
            f"- {citation.title}: {citation.link}" for citation in citations[:5]
        )
        prompt = f"""
你是研究质量审校员。请判断下面的分析是否被证据充分支持。

分析：
{analysis}

证据压缩：
{compressed_evidence}

引用：
{citation_text or "无"}

请只返回 JSON：
{{
  "passed": true,
  "score": 0.0,
  "issues": ["问题1"],
  "summary": "一句话结论"
}}
"""
        try:
            response = await self.llm._acall(prompt)
            parsed = self._parse_json(response)
            if parsed is None:
                return None
            parsed.setdefault("issues", [])
            parsed.setdefault("score", 0.5)
            parsed.setdefault("passed", False)
            parsed.setdefault("summary", "")
            parsed["method"] = "llm_critic"
            return parsed
        except Exception as exc:  # noqa: BLE001
            logger.warning("verifier llm critic failed: %s", exc)
            return None

    def _deterministic_verify(
        self,
        *,
        analysis: str,
        citations: list[Citation],
        compressed_evidence: str,
    ) -> dict[str, object]:
        issues: list[str] = []

        if not analysis.strip():
            issues.append("分析结果为空")
        if len(citations) < 2:
            issues.append("可引用来源不足，结论支撑偏弱")
        if len(compressed_evidence.strip()) < 80:
            issues.append("证据上下文过短，可能缺少有效检索内容")

        return {
            "passed": not issues,
            "issues": issues,
            "score": max(0.0, 1.0 - 0.25 * len(issues)),
            "summary": "规则校验通过" if not issues else "规则校验发现证据不足",
            "method": "deterministic_fallback",
        }

    def _parse_json(self, response: str) -> dict[str, object] | None:
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


verifier_service = VerifierService()
