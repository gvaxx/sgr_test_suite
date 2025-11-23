"""JSON-схема для описания тест-кейсов и функции загрузки."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import RootModel, ValidationError, BaseModel, Field

from .models import TestCase


class TestCasePayload(BaseModel):
    """Структура одного тест-кейса в JSON-файле."""

    id: str = Field(description="Уникальный идентификатор теста")
    params: dict[str, Any] = Field(default_factory=dict, description="Аргументы, передаваемые в pipeline.run")
    expected_output: Any = Field(description="Ожидаемый вывод пайплайна")
    comparator: str | None = Field(
        default=None,
        description=(
            "Необязательное имя компаратора из реестра раннера/пайплайна. "
            "Если не задано — используется значение по умолчанию."
        ),
    )
    description: str | None = Field(default=None, description="Краткое описание назначения теста")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Произвольные метаданные (например, тема, язык, заметки)",
    )


class TestCasesFile(RootModel[list[TestCasePayload]]):
    """Корневой объект JSON-файла с тестами."""

    root: list[TestCasePayload]

    def to_test_cases(self) -> list[TestCase]:
        return [
            TestCase(
                id=item.id,
                params=item.params,
                expected_output=item.expected_output,
                comparator=item.comparator,
                description=item.description,
                metadata=item.metadata,
            )
            for item in self.root
        ]


TEST_CASES_JSON_SCHEMA = TestCasesFile.model_json_schema()


def load_test_cases(path: Path) -> list[TestCase]:
    """Загрузить и провалидировать тест-кейсы из JSON-файла."""

    try:
        payload = TestCasesFile.model_validate_json(path.read_text())
    except ValidationError as exc:  # noqa: B904
        msg = f"Invalid test cases JSON at {path}: {exc}"
        raise ValueError(msg) from exc

    return payload.to_test_cases()


__all__ = ["TEST_CASES_JSON_SCHEMA", "load_test_cases", "TestCasePayload", "TestCasesFile"]
