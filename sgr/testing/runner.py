"""Test runner that executes pipelines against test cases."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Protocol

from .models import TestCase, TestResult, TestRun


class Pipeline(Protocol):
    """Minimal protocol a pipeline must follow for testing."""

    name: str | None

    def run(self, **params: Any) -> Any: ...


Comparator = Callable[[Any, Any], bool]


def default_comparator(actual: Any, expected: Any) -> bool:
    """Basic comparator used when no custom comparator is provided."""

    return actual == expected


class TestRunner:
    """Execute pipelines against a suite of test cases."""

    def __init__(self, comparator: Comparator | None = None):
        self._comparator = comparator or default_comparator

    def run(self, pipeline: Pipeline, test_cases: Iterable[TestCase]) -> TestRun:
        """Execute a pipeline against provided test cases."""

        started_at = datetime.utcnow()
        results: list[TestResult] = []

        for test_case in test_cases:
            case_started_at = datetime.utcnow()
            try:
                output = pipeline.run(**test_case.params)
                passed = self._comparator(output, test_case.expected_output)
                error: str | None = None
            except Exception as exc:  # noqa: BLE001
                output = None
                passed = False
                error = str(exc)
            case_ended_at = datetime.utcnow()

            results.append(
                TestResult(
                    id=test_case.id,
                    passed=passed,
                    output=output,
                    expected_output=test_case.expected_output,
                    started_at=case_started_at,
                    ended_at=case_ended_at,
                    error=error,
                )
            )

        ended_at = datetime.utcnow()
        pipeline_name = getattr(pipeline, "name", pipeline.__class__.__name__)
        return TestRun(pipeline_name=pipeline_name, started_at=started_at, ended_at=ended_at, results=results)


__all__ = ["Pipeline", "TestRunner", "default_comparator"]
