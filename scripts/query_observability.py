"""Query the local observability API with PromQL or LogQL from a terminal."""

from __future__ import annotations

import argparse
import json
import os
import sys

import requests


def main() -> int:
    """Parse CLI arguments, call the backend query API, and print JSON."""
    parser = _build_parser()
    args = parser.parse_args()
    response = requests.post(
        f"{args.backend_url.rstrip('/')}/api/observability/{args.language}",
        json={"query": args.query},
        timeout=args.timeout,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for agent-friendly observability queries."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language", choices=["promql", "logql"])
    parser.add_argument("query")
    parser.add_argument(
        "--backend-url",
        default=os.getenv("OPEN_DEEPRESEARCH_BACKEND_URL", "http://localhost:8003"),
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
