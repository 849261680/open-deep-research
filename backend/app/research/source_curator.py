from __future__ import annotations

from .models import ResearchSource


class SourceCurator:
    """Curates sources by deduping and keeping sources with usable content."""

    def curate(
        self, sources: list[ResearchSource], max_sources: int = 12
    ) -> list[ResearchSource]:
        curated: list[ResearchSource] = []
        seen_links: set[str] = set()
        for source in sources:
            if not source.link or source.link in seen_links:
                continue
            seen_links.add(source.link)
            if not (source.extracted_content or source.snippet):
                continue
            curated.append(source)
            if len(curated) >= max_sources:
                break
        return curated
