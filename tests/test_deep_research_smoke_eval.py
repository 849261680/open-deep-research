"""Regression tests for the deep research smoke evaluator."""

from __future__ import annotations

import json
from typing import cast

from evals.deep_research_smoke.evaluator import evaluate_reports
from evals.deep_research_smoke.evaluator import load_tasks
from evals.deep_research_smoke.evaluator import main
from evals.deep_research_smoke.evaluator import score_report
from evals.deep_research_smoke.evaluator import write_markdown_report


def test_loads_fixed_smoke_task_set() -> None:
    """Verify the fixed smoke suite has enough task coverage."""
    tasks = load_tasks()

    assert len(tasks) == 10
    assert tasks[0].id == "quantum-computing-applications-2026"
    assert tasks[0].expected_facts
    assert tasks[0].preferred_sources
    assert tasks[0].forbidden_claims
    min_read_count = cast(int, tasks[0].budget["min_read_count"])
    assert min_read_count >= 8


def test_scores_report_quality_metrics() -> None:
    """Verify one report produces the expected quality metrics."""
    task = load_tasks()[0]
    report = {
        "task_id": task.id,
        "report": "容错量子计算依赖量子纠错。NISQ 系统仍适合探索药物发现和优化问题。",
        "claims": [
            {
                "text": "量子纠错是容错量子计算的关键。",
                "citation_support": "supported",
                "citations": [{"link": "https://ibm.com/quantum"}],
            },
            {
                "text": "量子计算已经全面取代经典计算。",
                "citation_support": "unsupported",
                "citations": [{"link": "https://example.com/bad"}],
            },
        ],
        "metrics": {
            "elapsed_seconds": 100,
            "search_count": 6,
            "read_count": 9,
        },
    }

    score = score_report(task, report)

    assert score["coverage_score"] == 1.0
    assert score["citation_support_rate"] == 0.5
    assert score["unsupported_claim_count"] == 2
    assert score["effective_citations"] == 1
    assert score["budget"] == {
        "elapsed_seconds": True,
        "search_count": True,
        "read_count": True,
    }


def test_evaluates_reports_and_writes_outputs(tmp_path) -> None:
    """Verify aggregate scoring handles missing reports and Markdown output."""
    tasks = load_tasks()[:2]
    reports = [
        {
            "task_id": tasks[0].id,
            "report": "容错量子计算、量子纠错、NISQ、药物发现和优化问题。",
            "claims": [
                {
                    "text": "NISQ 仍有限制。",
                    "citation_support": True,
                    "citations": ["https://nature.com/example"],
                }
            ],
            "elapsed_seconds": 80,
            "search_count": 5,
            "read_count": 8,
        }
    ]

    result = evaluate_reports(tasks, reports)
    markdown_path = tmp_path / "baseline.md"
    write_markdown_report(result, markdown_path)

    assert result["task_count"] == 2
    assert result["evaluated_count"] == 1
    task_scores = cast(list[dict[str, object]], result["tasks"])
    assert task_scores[1]["status"] == "missing_report"
    assert "Deep Research Smoke Baseline" in markdown_path.read_text(encoding="utf-8")


def test_cli_writes_json_and_markdown_reports(tmp_path) -> None:
    """Verify the command entry point writes both report formats."""
    reports_path = tmp_path / "reports.json"
    json_output = tmp_path / "baseline.json"
    markdown_output = tmp_path / "baseline.md"
    reports_path.write_text(
        json.dumps(
            [
                {
                    "task_id": "quantum-computing-applications-2026",
                    "report": "容错量子计算 量子纠错 NISQ 药物发现 优化问题",
                    "claims": [
                        {
                            "text": "量子纠错很重要",
                            "citation_support": "supported",
                            "citations": [{"url": "https://googleblog.com/quantum"}],
                        }
                    ],
                    "metrics": {
                        "elapsed_seconds": 90,
                        "search_count": 5,
                        "read_count": 8,
                    },
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--reports",
            str(reports_path),
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
        ]
    )

    payload = json.loads(json_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert json_output.exists()
    assert markdown_output.exists()
    assert payload["task_count"] == 10
    assert payload["evaluated_count"] == 1
