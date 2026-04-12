from __future__ import annotations

from ..models.research_task import EvidenceItem


class CompressionService:
    """Condense raw evidence into a compact context for analysis and reporting."""

    def compress_evidence(
        self, section_title: str, evidence: list[EvidenceItem], limit: int = 8
    ) -> str:
        lines: list[str] = [f"研究主题: {section_title}"]
        for item in evidence[:limit]:
            snippet = item.snippet.strip()
            if len(snippet) > 280:
                snippet = snippet[:280] + "..."
            extracted = item.extracted_content.strip()
            if len(extracted) > 400:
                extracted = extracted[:400] + "..."
            lines.append(
                f"- [{item.source_type}] {item.title}\n  链接: {item.link}\n  摘要: {snippet}\n  正文摘录: {extracted}"
            )
        return "\n".join(lines)


compression_service = CompressionService()
