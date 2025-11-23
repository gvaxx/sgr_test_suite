"""Command-line interface for running pipelines against test cases."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from .models import TestCase, TestRun
from .runner import Pipeline, TestRunner


def _load_pipeline(target: str) -> Pipeline:
    """Load a pipeline object from ``module:attribute`` reference."""

    if ":" not in target:
        msg = "Pipeline should be provided as 'module:attribute'"
        raise ValueError(msg)

    module_name, attr = target.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
    try:
        pipeline_or_factory: Pipeline | Callable[[], Pipeline] = getattr(module, attr)
    except AttributeError as exc:  # noqa: B904
        msg = f"Attribute '{attr}' not found in module '{module_name}'"
        raise ValueError(msg) from exc

    pipeline: Pipeline = pipeline_or_factory() if callable(pipeline_or_factory) else pipeline_or_factory

    if not hasattr(pipeline, "run"):
        msg = "Pipeline object must define a 'run' method"
        raise ValueError(msg)

    return pipeline


def _load_test_cases(path: Path) -> list[TestCase]:
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        msg = "Test cases JSON should be a list of objects"
        raise ValueError(msg)

    cases: list[TestCase] = []
    for item in raw:
        if not isinstance(item, dict):
            msg = "Each test case should be an object"
            raise ValueError(msg)
        try:
            case_id = item["id"]
            params = item.get("params", {})
            expected = item["expected_output"]
        except KeyError as exc:  # noqa: B904
            msg = "Each test case must contain 'id' and 'expected_output' keys"
            raise ValueError(msg) from exc

        if not isinstance(params, dict):
            msg = "Test case 'params' must be a mapping"
            raise ValueError(msg)

        cases.append(TestCase(id=case_id, params=params, expected_output=expected))

    return cases


def _test_run_to_dict(test_run: TestRun) -> dict[str, Any]:
    return {
        "pipeline_name": test_run.pipeline_name,
        "started_at": test_run.started_at.isoformat(),
        "ended_at": test_run.ended_at.isoformat(),
        "duration_seconds": test_run.duration_seconds,
        "summary": {
            "total": test_run.summary.total,
            "passed": test_run.summary.passed,
            "failed": test_run.summary.failed,
            "accuracy": test_run.summary.accuracy,
        },
        "results": [
            {
                "id": result.id,
                "passed": result.passed,
                "output": result.output,
                "expected_output": result.expected_output,
                "started_at": result.started_at.isoformat(),
                "ended_at": result.ended_at.isoformat(),
                "duration_seconds": result.duration_seconds,
                "error": result.error,
            }
            for result in test_run.results
        ],
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pipeline test cases from CLI")
    parser.add_argument(
        "--pipeline",
        required=True,
        help="Python reference to pipeline instance or factory in format module:attribute",
    )
    parser.add_argument("--tests", type=Path, required=True, help="Path to JSON file with test cases")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to save JSON report with run results",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    pipeline = _load_pipeline(args.pipeline)
    test_cases = _load_test_cases(args.tests)

    runner = TestRunner()
    test_run = runner.run(pipeline=pipeline, test_cases=test_cases)

    summary = test_run.summary
    print(f"Pipeline: {test_run.pipeline_name}")
    print(f"Total: {summary.total} | Passed: {summary.passed} | Failed: {summary.failed}")
    print(f"Accuracy: {summary.accuracy:.0%} | Duration: {test_run.duration_seconds:.2f}s")

    if args.output:
        args.output.write_text(json.dumps(_test_run_to_dict(test_run), ensure_ascii=False, indent=2))
        print(f"Report saved to {args.output}")

    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
