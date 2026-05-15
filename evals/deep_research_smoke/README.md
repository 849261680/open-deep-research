# Deep Research Smoke Eval

This directory defines the first fixed quality baseline for deep research outputs.
It is intentionally offline: it scores saved report payloads instead of calling the
LLM or search providers.

## Task Format

`tasks.json` contains 10 real research tasks. Each task defines:

- `expected_facts`: facts or concepts the report should cover.
- `preferred_sources`: domains or organizations that should be preferred by the runner.
- `forbidden_claims`: claims that should not appear in a grounded report.
- `budget`: runtime and retrieval expectations.

## Report Input

The evaluator expects a JSON list of report payloads:

```json
[
  {
    "task_id": "quantum-computing-applications-2026",
    "report": "final report markdown",
    "claims": [
      {
        "text": "Quantum error correction is a key bottleneck.",
        "citation_support": "supported",
        "citations": [{"link": "https://example.com/source"}]
      }
    ],
    "metrics": {
      "elapsed_seconds": 120,
      "search_count": 8,
      "read_count": 12
    }
  }
]
```

## Run

```bash
uv run python -m evals.deep_research_smoke.evaluator \
  --reports output/deep_research_smoke_reports.json \
  --json-output output/deep_research_smoke_baseline.json \
  --markdown-output output/deep_research_smoke_baseline.md
```

The output includes `citation_support_rate`, `coverage_score`,
`unsupported_claim_count`, `elapsed_seconds`, `search_count`, and `read_count`.
