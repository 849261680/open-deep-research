"""Score deep research smoke reports against fixed quality tasks."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

DEFAULT_TASKS_PATH = Path(__file__).with_name("tasks.json")
JsonMap = dict[str, object]


@dataclass(frozen=True)
class EvalTask:
    """One fixed deep research task and its quality expectations."""

    id: str
    query: str
    expected_facts: list[str]
    preferred_sources: list[str]
    forbidden_claims: list[str]
    budget: JsonMap


def load_tasks(path: Path = DEFAULT_TASKS_PATH) -> list[EvalTask]:
    """Load smoke evaluation tasks from JSON."""
    raw_tasks = _read_json_list(path)
    return [_task_from_json(item) for item in raw_tasks]


def load_reports(path: Path) -> list[JsonMap]:
    """Load previously generated research outputs from JSON."""
    return _read_json_list(path)


def evaluate_reports(tasks: list[EvalTask], reports: list[JsonMap]) -> JsonMap:
    """Score all task reports and return aggregate metrics."""
    reports_by_task = {
        str(report.get("task_id", "")): report
        for report in reports
        if isinstance(report.get("task_id"), str)
    }
    task_scores = [score_report(task, reports_by_task.get(task.id, {})) for task in tasks]
    return {
        "task_count": len(tasks),
        "evaluated_count": sum(1 for score in task_scores if score["status"] == "evaluated"),
        "metrics": _aggregate_metrics(task_scores),
        "tasks": task_scores,
    }


def score_report(task: EvalTask, report: JsonMap) -> JsonMap:
    """Score one report against one smoke evaluation task."""
    if not report:
        return _missing_score(task)

    text = _report_text(report)
    claims = _claims(report)
    expected_hits = _matching_phrases(text, task.expected_facts)
    forbidden_hits = _matching_phrases(text, task.forbidden_claims)
    support_counts = _support_counts(claims)
    metrics = _metrics(report)
    return {
        "task_id": task.id,
        "query": task.query,
        "status": "evaluated",
        "coverage_score": _ratio(len(expected_hits), len(task.expected_facts)),
        "expected_fact_hits": expected_hits,
        "forbidden_claim_hits": forbidden_hits,
        "citation_support_rate": _ratio(
            support_counts["supported"],
            support_counts["supported"] + support_counts["partial"] + support_counts["unsupported"],
        ),
        "unsupported_claim_count": support_counts["unsupported"] + len(forbidden_hits),
        "effective_citations": _effective_citations(claims),
        "elapsed_seconds": metrics["elapsed_seconds"],
        "search_count": metrics["search_count"],
        "read_count": metrics["read_count"],
        "budget": _budget_status(task, metrics),
    }


def write_json_report(result: JsonMap, path: Path) -> None:
    """Write a machine-readable evaluation report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown_report(result: JsonMap, path: Path) -> None:
    """Write a human-readable evaluation report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = result.get("metrics", {})
    lines = [
        "# Deep Research Smoke Baseline",
        "",
        f"- Tasks: {result.get('task_count', 0)}",
        f"- Evaluated: {result.get('evaluated_count', 0)}",
        f"- Coverage score: {_metric_text(metrics, 'coverage_score')}",
        f"- Citation support rate: {_metric_text(metrics, 'citation_support_rate')}",
        f"- Unsupported claims: {_metric_text(metrics, 'unsupported_claim_count')}",
        f"- Elapsed seconds: {_metric_text(metrics, 'elapsed_seconds')}",
        f"- Search count: {_metric_text(metrics, 'search_count')}",
        f"- Read count: {_metric_text(metrics, 'read_count')}",
        "",
        "## Tasks",
        "",
    ]
    for task in result.get("tasks", []):
        if isinstance(task, dict):
            lines.extend(_task_markdown(task))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the smoke evaluator from the command line."""
    parser = argparse.ArgumentParser(description="Score deep research smoke reports.")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS_PATH)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    result = evaluate_reports(load_tasks(args.tasks), load_reports(args.reports))
    write_json_report(result, args.json_output)
    if args.markdown_output is not None:
        write_markdown_report(result, args.markdown_output)
    return 0


def _read_json_list(path: Path) -> list[JsonMap]:
    """Read a JSON file that must contain a list of objects."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path} must contain a JSON list")
    items: list[JsonMap] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"{path} contains a non-object item")
        items.append(item)
    return items


def _task_from_json(item: JsonMap) -> EvalTask:
    """Normalize one task JSON object."""
    return EvalTask(
        id=str(item["id"]),
        query=str(item["query"]),
        expected_facts=_text_list(item.get("expected_facts", [])),
        preferred_sources=_text_list(item.get("preferred_sources", [])),
        forbidden_claims=_text_list(item.get("forbidden_claims", [])),
        budget=item.get("budget", {}) if isinstance(item.get("budget"), dict) else {},
    )


def _missing_score(task: EvalTask) -> JsonMap:
    """Return a stable score for tasks without a report yet."""
    return {
        "task_id": task.id,
        "query": task.query,
        "status": "missing_report",
        "coverage_score": 0.0,
        "expected_fact_hits": [],
        "forbidden_claim_hits": [],
        "citation_support_rate": 0.0,
        "unsupported_claim_count": 0,
        "effective_citations": 0,
        "elapsed_seconds": 0.0,
        "search_count": 0,
        "read_count": 0,
        "budget": {
            "elapsed_seconds": False,
            "search_count": False,
            "read_count": False,
        },
    }


def _report_text(report: JsonMap) -> str:
    """Collect searchable report text from supported fields."""
    parts = [
        str(report.get("report", "")),
        str(report.get("summary", "")),
    ]
    for claim in _claims(report):
        parts.append(str(claim.get("text", "")))
    return "\n".join(parts)


def _claims(report: JsonMap) -> list[JsonMap]:
    """Return normalized claim objects from a report."""
    raw_claims = report.get("claims", [])
    if not isinstance(raw_claims, list):
        return []
    return [claim for claim in raw_claims if isinstance(claim, dict)]


def _matching_phrases(text: str, phrases: list[str]) -> list[str]:
    """Find expected or forbidden phrases in report text."""
    normalized_text = _normalize_text(text)
    return [phrase for phrase in phrases if _normalize_text(phrase) in normalized_text]


def _support_counts(claims: list[JsonMap]) -> dict[str, int]:
    """Count supported, partial, and unsupported claim states."""
    counts = {"supported": 0, "partial": 0, "unsupported": 0}
    for claim in claims:
        state = _claim_support_state(claim)
        counts[state] += 1
    return counts


def _claim_support_state(claim: JsonMap) -> str:
    """Normalize one claim support state."""
    value = claim.get("citation_support", claim.get("support"))
    if value is True:
        return "supported"
    if value is False:
        return "unsupported"
    normalized = str(value).strip().lower()
    if normalized in {"supported", "support", "true", "yes"}:
        return "supported"
    if normalized in {"partial", "partially_supported", "partially supported"}:
        return "partial"
    return "unsupported"


def _effective_citations(claims: list[JsonMap]) -> int:
    """Count unique citation links attached to supported claims."""
    links: set[str] = set()
    for claim in claims:
        if _claim_support_state(claim) != "supported":
            continue
        links.update(_citation_links(claim))
    return len(links)


def _citation_links(claim: JsonMap) -> list[str]:
    """Extract citation links from one claim."""
    raw_citations = claim.get("citations", [])
    if not isinstance(raw_citations, list):
        return []
    links: list[str] = []
    for citation in raw_citations:
        link = _citation_link(citation)
        if link:
            links.append(link)
    return links


def _citation_link(citation: object) -> str:
    """Extract a link from one citation record."""
    if isinstance(citation, str):
        return citation.strip()
    if isinstance(citation, dict):
        return str(citation.get("link", citation.get("url", ""))).strip()
    return ""


def _metrics(report: JsonMap) -> JsonMap:
    """Read runtime metrics from a report payload."""
    raw_metrics = report.get("metrics", {})
    metrics = raw_metrics if isinstance(raw_metrics, dict) else {}
    return {
        "elapsed_seconds": _number(metrics.get("elapsed_seconds", report.get("elapsed_seconds", 0))),
        "search_count": int(_number(metrics.get("search_count", report.get("search_count", 0)))),
        "read_count": int(_number(metrics.get("read_count", report.get("read_count", 0)))),
    }


def _budget_status(task: EvalTask, metrics: JsonMap) -> dict[str, bool]:
    """Check whether a report satisfies task runtime budgets."""
    max_elapsed = _number(task.budget.get("max_elapsed_seconds", 0))
    min_search = int(_number(task.budget.get("min_search_count", 0)))
    min_read = int(_number(task.budget.get("min_read_count", 0)))
    return {
        "elapsed_seconds": max_elapsed <= 0 or _number(metrics["elapsed_seconds"]) <= max_elapsed,
        "search_count": int(metrics["search_count"]) >= min_search,
        "read_count": int(metrics["read_count"]) >= min_read,
    }


def _aggregate_metrics(task_scores: list[JsonMap]) -> JsonMap:
    """Average numeric task metrics across evaluated reports."""
    evaluated = [score for score in task_scores if score["status"] == "evaluated"]
    if not evaluated:
        return {
            "coverage_score": 0.0,
            "citation_support_rate": 0.0,
            "unsupported_claim_count": 0.0,
            "effective_citations": 0.0,
            "elapsed_seconds": 0.0,
            "search_count": 0.0,
            "read_count": 0.0,
        }
    return {
        key: _mean(evaluated, key)
        for key in [
            "coverage_score",
            "citation_support_rate",
            "unsupported_claim_count",
            "effective_citations",
            "elapsed_seconds",
            "search_count",
            "read_count",
        ]
    }


def _task_markdown(task: JsonMap) -> list[str]:
    """Render one task score as Markdown."""
    return [
        f"### {task.get('task_id', '')}",
        "",
        f"- Status: {task.get('status', '')}",
        f"- Coverage: {task.get('coverage_score', 0)}",
        f"- Citation support: {task.get('citation_support_rate', 0)}",
        f"- Unsupported claims: {task.get('unsupported_claim_count', 0)}",
        f"- Expected fact hits: {', '.join(_text_list(task.get('expected_fact_hits', []))) or 'none'}",
        f"- Forbidden claim hits: {', '.join(_text_list(task.get('forbidden_claim_hits', []))) or 'none'}",
        "",
    ]


def _metric_text(metrics: object, key: str) -> object:
    """Read a metric from the aggregate metrics object."""
    if isinstance(metrics, dict):
        return metrics.get(key, 0)
    return 0


def _text_list(value: object) -> list[str]:
    """Normalize a JSON value into a list of non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_text(value: str) -> str:
    """Normalize text for coarse phrase matching."""
    return "".join(value.lower().split())


def _number(value: object) -> float:
    """Convert numeric JSON values into floats."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return 0.0


def _ratio(numerator: int, denominator: int) -> float:
    """Return a rounded ratio with zero-denominator safety."""
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _mean(items: list[JsonMap], key: str) -> float:
    """Average one numeric key across score objects."""
    values = [_number(item.get(key, 0)) for item in items]
    return round(sum(values) / max(len(values), 1), 4)


if __name__ == "__main__":
    raise SystemExit(main())
