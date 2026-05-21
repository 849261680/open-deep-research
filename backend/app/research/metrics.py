"""Collect process-level metrics for one research task."""

from __future__ import annotations

from time import monotonic


class ResearchMetrics:
    """Track search, source, citation, elapsed, and cost metrics."""

    def __init__(self) -> None:
        self._started_at = monotonic()
        self.search_count = 0
        self.selected_source_count = 0
        self.read_count = 0
        self.cited_source_count = 0
        self._cited_links: set[str] = set()

    def record_searches(self, count: int = 1) -> None:
        """Add completed search calls to the running total."""
        self.search_count += max(count, 0)

    def record_selected_sources(self, count: int) -> None:
        """Add curated candidate sources selected for possible reading."""
        self.selected_source_count += max(count, 0)

    def record_read_sources(self, count: int) -> None:
        """Add successfully read source pages to the running total."""
        self.read_count += max(count, 0)

    def record_citations(self, links: list[str]) -> None:
        """Record unique citation links used by the research output."""
        for link in links:
            if link:
                self._cited_links.add(link)
        self.cited_source_count = len(self._cited_links)

    def snapshot(self, cost_summary: dict[str, object] | None = None) -> dict[str, object]:
        """Return a stable JSON-safe metrics payload."""
        cost = cost_summary or {}
        return {
            "search_count": self.search_count,
            "selected_source_count": self.selected_source_count,
            "read_count": self.read_count,
            "cited_source_count": self.cited_source_count,
            "elapsed_seconds": round(monotonic() - self._started_at, 3),
            "total_tokens": _number(cost.get("total_tokens"), default=0),
            "estimated_cost_usd": _number(cost.get("estimated_cost_usd"), default=0.0),
        }


def _number(value: object, *, default: int | float) -> int | float:
    """Coerce numeric cost fields without trusting arbitrary payload types."""
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return default
    return default
