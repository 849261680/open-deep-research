"""Run the fixed deep-research smoke suite and write a baseline report."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from typing import cast

from backend.app.models.research_task import ResearchTask
from backend.app.models.research_task import utc_now
from backend.app.research.agent import ResearchAgent
from backend.app.research.config import ResearchConfig
from evals.deep_research_smoke.evaluator import EvalTask
from evals.deep_research_smoke.evaluator import evaluate_reports
from evals.deep_research_smoke.evaluator import load_tasks
from evals.deep_research_smoke.evaluator import write_json_report

DEFAULT_REPORTS_PATH = Path("output/deep_research_smoke_reports.json")
DEFAULT_JSON_OUTPUT = Path("output/deep_research_smoke_baseline.json")
DEFAULT_MARKDOWN_OUTPUT = Path("output/eval_baseline.md")


@dataclass
class RunMetrics:
    """Counters collected from the live research event stream."""

    search_count: int = 0
    read_count: int = 0
    elapsed_seconds: float = 0.0


async def run_suite(args: argparse.Namespace) -> int:
    """Run selected tasks, score them, and write output artifacts."""
    tasks = _selected_tasks(load_tasks(args.tasks), args.task_id, args.limit)
    existing_reports = _load_existing_reports(args.reports) if args.resume else []
    reports_by_id = {str(item.get("task_id", "")): item for item in existing_reports}
    reports = [report for report in existing_reports if str(report.get("task_id", ""))]

    for index, task in enumerate(tasks, start=1):
        if task.id in reports_by_id:
            print(f"[{index}/{len(tasks)}] skip existing {task.id}")
            continue
        print(f"[{index}/{len(tasks)}] running {task.id}: {task.query}")
        report = await run_task(task, args)
        reports.append(report)
        reports_by_id[task.id] = report
        _write_reports(reports, args.reports)

    result = evaluate_reports(load_tasks(args.tasks), reports)
    write_json_report(result, args.json_output)
    write_markdown_baseline(result, args.markdown_output, args, reports)
    return 0


async def run_task(task: EvalTask, args: argparse.Namespace) -> dict[str, object]:
    """Run one eval task through the current research agent."""
    config = ResearchConfig(
        max_sub_queries=args.max_sub_queries,
        max_concurrency=args.max_concurrency,
        max_read_pages_per_section=args.max_read_pages_per_section,
        deep_research_breadth=args.deep_research_breadth,
        deep_research_depth=args.deep_research_depth,
        retriever=args.retriever,
    )
    agent = ResearchAgent(query=task.query, config=config)
    research_task = ResearchTask(id=f"eval-{task.id}", query=task.query)
    metrics = RunMetrics()
    started = time.monotonic()
    report_data: dict[str, object] = {}

    async for event in agent.run(research_task):
        _update_metrics(metrics, event)
        if event.get("type") == "report_complete" and isinstance(event.get("data"), dict):
            report_data = cast(dict[str, object], event["data"])

    metrics.elapsed_seconds = round(time.monotonic() - started, 2)
    return _report_payload(task, report_data, metrics)


def _update_metrics(metrics: RunMetrics, event: dict[str, object]) -> None:
    """Update counters from one streamed research event."""
    data = event.get("data", {})
    if event.get("type") == "search_result":
        metrics.search_count += 1
    if event.get("type") == "analysis_progress" and isinstance(data, dict):
        metrics.read_count += int(data.get("read_count", 0) or 0)


def _report_payload(
    task: EvalTask,
    report_data: dict[str, object],
    metrics: RunMetrics,
) -> dict[str, object]:
    """Build the evaluator input payload for one completed task."""
    return {
        "task_id": task.id,
        "query": task.query,
        "generated_at": utc_now(),
        "report": str(report_data.get("report", "")),
        "claims": _claim_checks(report_data),
        "metrics": {
            "elapsed_seconds": metrics.elapsed_seconds,
            "search_count": metrics.search_count,
            "read_count": metrics.read_count,
        },
    }


def _claim_checks(report_data: dict[str, object]) -> list[dict[str, object]]:
    """Extract claim support records from the agent report payload."""
    raw_claims = report_data.get("claim_checks", [])
    if not isinstance(raw_claims, list):
        return []
    return [claim for claim in raw_claims if isinstance(claim, dict)]


def write_markdown_baseline(
    result: dict[str, object],
    path: Path,
    args: argparse.Namespace,
    reports: list[dict[str, object]],
) -> None:
    """Write a README-ready baseline report with aggregate and task metrics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = result.get("metrics", {})
    reports_by_id = {str(item.get("task_id", "")): item for item in reports}
    lines = [
        "# Deep Research Smoke Eval Baseline",
        "",
        "## Run Configuration",
        "",
        f"- Tasks: {result.get('task_count', 0)}",
        f"- Evaluated: {result.get('evaluated_count', 0)}",
        f"- Retriever: `{args.retriever}`",
        f"- Max sub queries: {args.max_sub_queries}",
        f"- Max concurrency: {args.max_concurrency}",
        f"- Max read pages per section: {args.max_read_pages_per_section}",
        f"- Deep research breadth/depth: {args.deep_research_breadth}/{args.deep_research_depth}",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| coverage_score | {_metric(metrics, 'coverage_score')} |",
        f"| citation_support_rate | {_metric(metrics, 'citation_support_rate')} |",
        f"| unsupported_claim_count | {_metric(metrics, 'unsupported_claim_count')} |",
        f"| effective_citations | {_metric(metrics, 'effective_citations')} |",
        f"| elapsed_seconds | {_metric(metrics, 'elapsed_seconds')} |",
        f"| search_count | {_metric(metrics, 'search_count')} |",
        f"| read_count | {_metric(metrics, 'read_count')} |",
        "",
        "## Task Scores",
        "",
        "| Task | Status | Coverage | Citation support | Unsupported claims | Search | Read | Elapsed(s) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for task_score in cast(list[object], result.get("tasks", [])):
        if isinstance(task_score, dict):
            lines.append(_task_score_row(task_score))
    lines.extend(["", "## Task Details", ""])
    for task_score in cast(list[object], result.get("tasks", [])):
        if isinstance(task_score, dict):
            lines.extend(_task_detail(task_score, reports_by_id))
    lines.extend(["", "## Overall Assessment", ""])
    lines.extend(_overall_assessment(result))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _task_score_row(task: dict[str, object]) -> str:
    """Render one compact score table row."""
    return (
        f"| `{task.get('task_id', '')}` | {task.get('status', '')} | "
        f"{task.get('coverage_score', 0)} | {task.get('citation_support_rate', 0)} | "
        f"{task.get('unsupported_claim_count', 0)} | {task.get('search_count', 0)} | "
        f"{task.get('read_count', 0)} | {task.get('elapsed_seconds', 0)} |"
    )


def _task_detail(
    task: dict[str, object],
    reports_by_id: dict[str, dict[str, object]],
) -> list[str]:
    """Render detailed facts, forbidden hits, and runtime budget state."""
    task_id = str(task.get("task_id", ""))
    report = reports_by_id.get(task_id, {})
    return [
        f"### {task_id}",
        "",
        f"- Query: {report.get('query', task.get('query', ''))}",
        f"- Coverage: {task.get('coverage_score', 0)}",
        f"- Citation support rate: {task.get('citation_support_rate', 0)}",
        f"- Unsupported claim count: {task.get('unsupported_claim_count', 0)}",
        f"- Effective citations: {task.get('effective_citations', 0)}",
        f"- Search/read/elapsed: {task.get('search_count', 0)} / {task.get('read_count', 0)} / {task.get('elapsed_seconds', 0)}s",
        f"- Budget: {_budget_text(task.get('budget', {}))}",
        f"- Expected fact hits: {_list_text(task.get('expected_fact_hits', []))}",
        f"- Forbidden claim hits: {_list_text(task.get('forbidden_claim_hits', []))}",
        "",
    ]


def _overall_assessment(result: dict[str, object]) -> list[str]:
    """Summarize the baseline in a short, README-ready paragraph."""
    metrics = result.get("metrics", {})
    coverage = _float_metric(metrics, "coverage_score")
    support = _float_metric(metrics, "citation_support_rate")
    unsupported = _float_metric(metrics, "unsupported_claim_count")
    lines = [
        f"- The current baseline evaluates {result.get('evaluated_count', 0)} of {result.get('task_count', 0)} fixed smoke tasks.",
        f"- Average coverage is {coverage}, average citation support is {support}, and average unsupported claims per task is {unsupported}.",
    ]
    if coverage < 0.6:
        lines.append("- Main improvement area: reports need to cover more of the fixed expected facts explicitly.")
    if support < 0.8:
        lines.append("- Main reliability area: increase valid inline citations on factual claims.")
    if unsupported > 3:
        lines.append("- Main risk area: reduce uncited factual sentences or unsupported claim extraction noise.")
    return lines


def _selected_tasks(
    tasks: list[EvalTask],
    task_ids: list[str],
    limit: int | None,
) -> list[EvalTask]:
    """Filter the fixed task suite by CLI selection flags."""
    selected = [task for task in tasks if not task_ids or task.id in task_ids]
    return selected[:limit] if limit is not None else selected


def _load_existing_reports(path: Path) -> list[dict[str, object]]:
    """Load existing report payloads when resuming a baseline run."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _write_reports(reports: list[dict[str, object]], path: Path) -> None:
    """Persist report payloads after each task."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _metric(metrics: object, key: str) -> object:
    """Read a metric value from the aggregate metrics object."""
    if isinstance(metrics, dict):
        return metrics.get(key, 0)
    return 0


def _float_metric(metrics: object, key: str) -> float:
    """Read a metric as float for assessment thresholds."""
    value = _metric(metrics, key)
    return float(value) if isinstance(value, int | float) else 0.0


def _budget_text(value: object) -> str:
    """Render per-task budget pass states."""
    if not isinstance(value, dict):
        return "n/a"
    parts = [f"{key}={passed}" for key, passed in value.items()]
    return ", ".join(parts) if parts else "n/a"


def _list_text(value: object) -> str:
    """Render scorer hit lists in compact Markdown."""
    if not isinstance(value, list) or not value:
        return "none"
    return ", ".join(str(item) for item in value)


def build_parser() -> argparse.ArgumentParser:
    """Build the baseline runner command parser."""
    parser = argparse.ArgumentParser(description="Run deep research smoke baseline.")
    parser.add_argument("--tasks", type=Path, default=Path("evals/deep_research_smoke/tasks.json"))
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retriever", default="tavily")
    parser.add_argument("--max-sub-queries", type=int, default=5)
    parser.add_argument("--max-concurrency", type=int, default=2)
    parser.add_argument("--max-read-pages-per-section", type=int, default=2)
    parser.add_argument("--deep-research-breadth", type=int, default=0)
    parser.add_argument("--deep-research-depth", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the baseline CLI."""
    args = build_parser().parse_args(argv)
    return asyncio.run(run_suite(args))


if __name__ == "__main__":
    raise SystemExit(main())
