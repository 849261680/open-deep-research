from __future__ import annotations

import asyncio

from ..services.content_extraction_service import content_extraction_service
from .models import ResearchSource


class ResearchScraper:
    """Scrapes search result URLs and tracks visited URLs."""

    async def scrape(
        self,
        sources: list[ResearchSource],
        visited_urls: set[str],
        max_sources: int = 8,
    ) -> list[ResearchSource]:
        new_sources: list[ResearchSource] = []
        for source in sources:
            if source.link in visited_urls:
                source.status = "discarded"
                source.failure_reason = "duplicate_visited_url"
                continue
            visited_urls.add(source.link)
            new_sources.append(source)
            if len(new_sources) >= max_sources:
                break

        extraction_sources = [
            source for source in new_sources if not source.extracted_content.strip()
        ]
        extracted = await asyncio.gather(
            *[
                content_extraction_service.extract_content(source.link)
                for source in extraction_sources
            ],
            return_exceptions=True,
        )
        for source in new_sources:
            if source.extracted_content.strip():
                source.status = "read"
                source.failure_reason = ""
        for source, content in zip(extraction_sources, extracted):
            if isinstance(content, BaseException):
                source.status = "failed"
                source.failure_reason = str(content) or content.__class__.__name__
                source.extracted_content = ""
            elif content.strip():
                source.status = "read"
                source.failure_reason = ""
                source.extracted_content = content
            else:
                source.status = "failed"
                source.failure_reason = "empty_content"
                source.extracted_content = ""
        return new_sources
