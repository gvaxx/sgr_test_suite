from __future__ import annotations

import unittest
from typing import Any

from models.pipeline import ChatPipeline, PromptTemplate


class DummyResponse:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": content})()})()]


class DummyClient:
    def __init__(self, response: Any):
        self.response = response
        self.recorded_messages: list[list[dict[str, str]]] = []

    def chat(self, messages: list[dict[str, str]]) -> Any:  # noqa: ANN401
        self.recorded_messages.append(messages)
        return self.response


class ChatPipelineTests(unittest.TestCase):
    def test_builds_messages_with_system_prompt(self) -> None:
        client = DummyClient(DummyResponse("ok"))
        pipeline = ChatPipeline(client=client, prompt=PromptTemplate(user="Hello {name}", system="System message"))

        result = pipeline.run(name="World")

        self.assertEqual(result, "ok")
        self.assertEqual(
            client.recorded_messages[0],
            [
                {"role": "system", "content": "System message"},
                {"role": "user", "content": "Hello World"},
            ],
        )

    def test_missing_placeholder_raises_value_error(self) -> None:
        client = DummyClient(DummyResponse("ok"))
        pipeline = ChatPipeline(client=client, prompt=PromptTemplate(user="Hello {name}"))

        with self.assertRaises(ValueError):
            pipeline.run()

    def test_custom_response_parser_is_used(self) -> None:
        response = {"message": "parsed"}
        client = DummyClient(response)
        parser = lambda payload: payload["message"]  # noqa: E731
        pipeline = ChatPipeline(client=client, prompt=PromptTemplate(user="Hello"), response_parser=parser)

        result = pipeline.run()

        self.assertEqual(result, "parsed")


if __name__ == "__main__":
    unittest.main()
