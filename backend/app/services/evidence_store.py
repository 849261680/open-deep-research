from __future__ import annotations
from uuid import uuid4

from .content_extraction_service import content_extraction_service
from ..models.research_task import Citation
from ..models.research_task import EvidenceItem


class EvidenceStore:
    """In-memory evidence store.

    This gives the orchestrator a stable evidence layer now and can be swapped
    for a database later without changing the higher-level flow.
    """

    def __init__(self) -> None:
        self._evidence: dict[str, EvidenceItem] = {}

    async def add_many(
        self,
        *,
        section_id: str,
        query: str,
        source_type: str,
        task_id: str | None = None,
        items: list[dict[str, object]],
    ) -> list[str]:
        evidence_ids: list[str] = []
        extraction_targets = [
            str(item.get("link", ""))
            for item in items[:2]
            if isinstance(item, dict) and item.get("link")
        ]
        extracted_map: dict[str, str] = {}
        if extraction_targets:
            extracted_map = await self._extract_many(extraction_targets)

        for item in items:
            evidence_id = str(uuid4())
            evidence = EvidenceItem(
                id=evidence_id,
                section_id=section_id,
                query=query,
                source_type=str(item.get("source_type", source_type)),
                title=str(item.get("title", "")),
                link=str(item.get("link", "")),
                snippet=str(item.get("snippet", "")),
                extracted_content=extracted_map.get(str(item.get("link", "")), ""),
            )
            self._evidence[evidence_id] = evidence
            evidence_ids.append(evidence_id)
        return evidence_ids

    def get_many(self, evidence_ids: list[str]) -> list[EvidenceItem]:
        return [
            self._evidence[evidence_id]
            for evidence_id in evidence_ids
            if evidence_id in self._evidence
        ]

    def get_citations(self, evidence_ids: list[str], limit: int = 5) -> list[Citation]:
        citations: list[Citation] = []
        seen_links: set[str] = set()
        for evidence in self.get_many(evidence_ids):
            if not evidence.link or evidence.link in seen_links:
                continue
            seen_links.add(evidence.link)
            citations.append(
                Citation(
                    title=evidence.title,
                    link=evidence.link,
                    source=evidence.source_type,
                    query=evidence.query,
                )
            )
            if len(citations) >= limit:
                break
        return citations

    def clear(self) -> None:
        self._evidence = {}

    async def _extract_many(self, links: list[str]) -> dict[str, str]:
        import asyncio

        tasks = [content_extraction_service.extract_content(link) for link in links]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        extracted: dict[str, str] = {}
        for link, result in zip(links, results):
            if isinstance(result, Exception):
                extracted[link] = ""
            else:
                extracted[link] = result
        return extracted
