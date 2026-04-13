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
                continue
            visited_urls.add(source.link)
            new_sources.append(source)
            if len(new_sources) >= max_sources:
                break

        extracted = await asyncio.gather(
            *[
                content_extraction_service.extract_content(source.link)
                for source in new_sources
            ],
            return_exceptions=True,
        )
        for source, content in zip(new_sources, extracted):
            if isinstance(content, Exception):
                source.extracted_content = ""
            else:
                source.extracted_content = content
        return new_sources
