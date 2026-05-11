from __future__ import annotations

from urllib.parse import urlparse

from ..services.search_tools import search_tools
from .config import ResearchConfig
from .models import ResearchSource


class ResearchRetriever:
    """Search retriever layer, equivalent to GPT Researcher's retriever facade."""

    def __init__(self, config: ResearchConfig | None = None) -> None:
        self.config = config or ResearchConfig.from_env()

    async def search(self, query: str, max_results: int = 8) -> list[ResearchSource]:
        sources = self._configured_sources(query)
        remaining = max(max_results - len(sources), 0)
        if remaining == 0:
            return sources[:max_results]

        raw_results = await self._search_raw(query, remaining)
        sources.extend(self._raw_results_to_sources(query, raw_results, remaining))
        return sources[:max_results]

    async def _search_raw(
        self, query: str, max_results: int
    ) -> dict[str, list[dict[str, object]]]:
        """Run the selected retriever backend and return grouped raw results."""
        if self.config.retriever == "duckduckgo":
            return {"web": await search_tools.duckduckgo_search(query, max_results)}
        if self.config.retriever == "serpapi":
            return {"web": await search_tools.google_search(query, max_results)}
        if self.config.retriever == "tavily":
            return {"web": await search_tools.tavily_search(query, max_results)}
        return await search_tools.comprehensive_search(query)

    def _configured_sources(self, query: str) -> list[ResearchSource]:
        """Convert explicit source URLs from config into source records."""
        return [
            ResearchSource(
                title=url,
                link=url,
                source="configured_url",
                query=query,
            )
            for url in self.config.source_urls
            if self._domain_allowed(url)
        ]

    def _raw_results_to_sources(
        self,
        query: str,
        raw_results: dict[str, list[dict[str, object]]],
        max_results: int,
    ) -> list[ResearchSource]:
        """Normalize grouped search results into deduped ResearchSource records."""
        sources: list[ResearchSource] = []
        seen_links: set[str] = set()
        for source_type, items in raw_results.items():
            for item in items:
                link = str(item.get("link", "")).strip()
                if not self._can_use_link(link, seen_links):
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

    def _can_use_link(self, link: str, seen_links: set[str]) -> bool:
        """Check link presence, uniqueness, and configured domain filters."""
        return bool(link and link not in seen_links and self._domain_allowed(link))

    def _domain_allowed(self, link: str) -> bool:
        """Return whether a URL matches the optional query domain filter."""
        if not self.config.query_domains:
            return True
        domain = _link_domain(link)
        return any(_domain_matches(domain, allowed) for allowed in self.config.query_domains)


def _link_domain(link: str) -> str:
    """Extract a normalized hostname from a URL."""
    parsed = urlparse(link)
    return parsed.netloc.lower().removeprefix("www.")


def _domain_matches(domain: str, allowed: str) -> bool:
    """Check exact or subdomain match against a configured domain."""
    normalized = _link_domain(allowed) if "://" in allowed else allowed.lower()
    normalized = normalized.removeprefix("www.")
    return domain == normalized or domain.endswith(f".{normalized}")
