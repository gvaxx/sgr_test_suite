"""Data structures for test execution results."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class TestCase:
    """Single test case definition."""

    id: str
    params: dict[str, Any]
    expected_output: Any


@dataclass
class TestResult:
    """Result of a single test case execution."""

    id: str
    passed: bool
    output: Any
    expected_output: Any
    started_at: datetime
    ended_at: datetime
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Compute duration in seconds."""

        return (self.ended_at - self.started_at).total_seconds()


@dataclass
class RunSummary:
    """Aggregate statistics for a test run."""

    total: int
    passed: int
    failed: int

    @property
    def accuracy(self) -> float:
        """Return accuracy percentage."""

        if self.total == 0:
            return 0.0
        return self.passed / self.total


@dataclass
class TestRun:
    """Complete test run report."""

    pipeline_name: str
    started_at: datetime
    ended_at: datetime
    results: List[TestResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert run details to a JSON-serializable structure."""

        return {
            "pipeline_name": self.pipeline_name,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "summary": {
                "total": self.summary.total,
                "passed": self.summary.passed,
                "failed": self.summary.failed,
                "accuracy": self.summary.accuracy,
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
                for result in self.results
            ],
        }

    @property
    def summary(self) -> RunSummary:
        """Summarize run outcome."""

        total = len(self.results)
        passed = sum(1 for result in self.results if result.passed)
        failed = total - passed
        return RunSummary(total=total, passed=passed, failed=failed)

    @property
    def duration_seconds(self) -> float:
        """Compute duration in seconds."""

        return (self.ended_at - self.started_at).total_seconds()
