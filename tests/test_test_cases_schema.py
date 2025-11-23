from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sgr.testing.schema import load_test_cases


class TestCaseSchemaTests(unittest.TestCase):
    def _write_payload(self, payload: object) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "cases.json"
        path.write_text(json.dumps(payload, ensure_ascii=False))
        return path

    def test_loads_valid_cases_with_metadata(self) -> None:
        path = self._write_payload(
            [
                {
                    "id": "case-1",
                    "params": {"text": "ping"},
                    "expected_output": "PING",
                    "description": "Uppercases input",
                    "metadata": {"topic": "demo"},
                    "comparator": "strict",
                }
            ]
        )

        cases = load_test_cases(path)

        self.assertEqual(1, len(cases))
        case = cases[0]
        self.assertEqual("case-1", case.id)
        self.assertEqual({"text": "ping"}, case.params)
        self.assertEqual("PING", case.expected_output)
        self.assertEqual("strict", case.comparator)
        self.assertEqual("Uppercases input", case.description)
        self.assertEqual({"topic": "demo"}, case.metadata)

    def test_invalid_root_structure_raises(self) -> None:
        path = self._write_payload({"id": "case"})

        with self.assertRaises(ValueError):
            load_test_cases(path)

    def test_invalid_comparator_type_raises(self) -> None:
        path = self._write_payload(
            [
                {
                    "id": "case-1",
                    "params": {},
                    "expected_output": {},
                    "comparator": 123,
                }
            ]
        )

        with self.assertRaises(ValueError):
            load_test_cases(path)


if __name__ == "__main__":
    unittest.main()
