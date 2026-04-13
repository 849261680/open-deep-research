from __future__ import annotations

from ..services.search_tools import search_tools
from .models import ResearchSource


class ResearchRetriever:
    """Search retriever layer, equivalent to GPT Researcher's retriever facade."""

    async def search(self, query: str, max_results: int = 8) -> list[ResearchSource]:
        raw_results = await search_tools.comprehensive_search(query)
        sources: list[ResearchSource] = []
        seen_links: set[str] = set()
        for source_type, items in raw_results.items():
            for item in items:
                link = str(item.get("link", "")).strip()
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                sources.append(
                    ResearchSource(
                        title=str(item.get("title", "")),
                        link=link,
                        source=str(item.get("source", source_type)),
                        query=query,
                        snippet=str(item.get("snippet", "")),
                    )
                )
                if len(sources) >= max_results:
                    return sources
        return sources
