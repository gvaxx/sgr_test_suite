from __future__ import annotations

from dataclasses import dataclass

import pytest

from sgr.testing.models import TestCase
from sgr.testing.runner import TestRunner


@dataclass
class EchoPipeline:
    name: str = "Echo"
    default_comparator = staticmethod(lambda actual, expected: str(actual).lower() == str(expected).lower())

    def run(self, text: str) -> str:
        return text


@dataclass
class RegistryPipeline:
    name: str = "Registry"
    comparators = {
        "length": staticmethod(lambda actual, expected: len(str(actual)) == expected),
    }

    def run(self, text: str) -> str:
        return text


@dataclass
class SimplePipeline:
    name: str = "Simple"

    def run(self, text: str) -> str:
        return text


def test_uses_pipeline_default_comparator_when_available() -> None:
    pipeline = EchoPipeline()
    runner = TestRunner()
    test_case = TestCase(id="1", params={"text": "PING"}, expected_output="ping")

    result = runner.run(pipeline=pipeline, test_cases=[test_case])

    assert result.results[0].passed is True


def test_runner_comparator_overrides_pipeline_default() -> None:
    pipeline = EchoPipeline()
    runner = TestRunner(comparator=lambda actual, expected: actual == expected)
    test_case = TestCase(id="1", params={"text": "PING"}, expected_output="ping")

    result = runner.run(pipeline=pipeline, test_cases=[test_case])

    assert result.results[0].passed is False


def test_named_comparator_resolved_from_runner_registry() -> None:
    pipeline = SimplePipeline()
    runner = TestRunner(comparators={"length": lambda actual, expected: len(actual) == expected})
    test_case = TestCase(id="1", params={"text": "data"}, expected_output=4, comparator="length")

    result = runner.run(pipeline=pipeline, test_cases=[test_case])

    assert result.results[0].passed is True


def test_named_comparator_resolved_from_pipeline_registry() -> None:
    pipeline = RegistryPipeline()
    runner = TestRunner()
    test_case = TestCase(id="1", params={"text": "ping"}, expected_output=4, comparator="length")

    result = runner.run(pipeline=pipeline, test_cases=[test_case])

    assert result.results[0].passed is True


def test_unknown_comparator_name_raises_error() -> None:
    pipeline = SimplePipeline()
    runner = TestRunner()
    test_case = TestCase(id="1", params={"text": "ping"}, expected_output="ping", comparator="missing")

    with pytest.raises(ValueError):
        runner.run(pipeline=pipeline, test_cases=[test_case])
