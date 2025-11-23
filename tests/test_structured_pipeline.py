from __future__ import annotations

import json
import unittest
from typing import Any

from pydantic import BaseModel

from models.pipeline import PromptTemplate, StructuredChatPipeline


class DummyResponse:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": content})()})()]


class DummyClient:
    def __init__(self, response: Any):
        self.response = response

    def chat(self, messages: list[dict[str, str]]) -> Any:  # noqa: ANN401
        self.last_messages = messages
        return self.response


class ResultModel(BaseModel):
    name: str


class StructuredChatPipelineTests(unittest.TestCase):
    def test_parses_valid_json_into_model(self) -> None:
        response = DummyResponse(content=json.dumps({"name": "World"}))
        client = DummyClient(response=response)
        pipeline = StructuredChatPipeline(
            client=client,
            prompt=PromptTemplate(user="Hello {name}"),
            response_model=ResultModel,
        )

        result = pipeline.run(name="World")

        self.assertIsInstance(result, ResultModel)
        self.assertEqual(result.name, "World")
        self.assertEqual(
            client.last_messages,
            [{"role": "user", "content": "Hello World"}],
        )

    def test_invalid_json_raises_value_error(self) -> None:
        response = DummyResponse(content="not json")
        client = DummyClient(response=response)
        pipeline = StructuredChatPipeline(
            client=client,
            prompt=PromptTemplate(user="Hello"),
            response_model=ResultModel,
        )

        with self.assertRaises(ValueError):
            pipeline.run()

    def test_schema_validation_error_is_wrapped(self) -> None:
        response = DummyResponse(content=json.dumps({"unexpected": "field"}))
        client = DummyClient(response=response)
        pipeline = StructuredChatPipeline(
            client=client,
            prompt=PromptTemplate(user="Hello"),
            response_model=ResultModel,
        )

        with self.assertRaises(ValueError):
            pipeline.run()


if __name__ == "__main__":
    unittest.main()
