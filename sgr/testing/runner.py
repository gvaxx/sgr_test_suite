"""Test runner that executes pipelines against test cases."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Mapping, Protocol

from .models import Comparator, TestCase, TestResult, TestRun


class Pipeline(Protocol):
    """Minimal protocol a pipeline must follow for testing."""

    name: str | None

    def run(self, **params: Any) -> Any: ...


def default_comparator(actual: Any, expected: Any) -> bool:
    """Basic comparator used when no custom comparator is provided."""

    return actual == expected


class TestRunner:
    """Execute pipelines against a suite of test cases."""

    def __init__(
        self,
        *,
        comparator: Comparator | None = None,
        comparators: Mapping[str, Comparator] | None = None,
    ) -> None:
        self._runner_comparator = comparator
        self._comparators = dict(comparators or {})

    def run(self, pipeline: Pipeline, test_cases: Iterable[TestCase]) -> TestRun:
        """Execute a pipeline against provided test cases."""

        started_at = datetime.utcnow()
        results: list[TestResult] = []

        for test_case in test_cases:
            case_started_at = datetime.utcnow()
            comparator = self._select_comparator(test_case=test_case, pipeline=pipeline)
            try:
                output = pipeline.run(**test_case.params)
                passed = comparator(output, test_case.expected_output)
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

    def _select_comparator(self, *, test_case: TestCase, pipeline: Pipeline) -> Comparator:
        if callable(test_case.comparator):
            return test_case.comparator

        if isinstance(test_case.comparator, str):
            if test_case.comparator in self._comparators:
                return self._comparators[test_case.comparator]

            pipeline_comparators = getattr(pipeline, "comparators", None)
            if isinstance(pipeline_comparators, Mapping) and test_case.comparator in pipeline_comparators:
                return pipeline_comparators[test_case.comparator]

            msg = f"Unknown comparator '{test_case.comparator}' for test case {test_case.id}"
            raise ValueError(msg)

        if self._runner_comparator is not None:
            return self._runner_comparator

        pipeline_default = getattr(pipeline, "default_comparator", None)
        if pipeline_default is not None:
            return pipeline_default

        return default_comparator


__all__ = ["Pipeline", "TestRunner", "default_comparator"]
