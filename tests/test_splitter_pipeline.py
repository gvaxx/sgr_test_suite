from __future__ import annotations

import json
import unittest
from sgr.pipelines.splitter import (
    ConversationSplit,
    ConversationSplitterPipeline,
    OrderContext,
    SPLITTER_PROMPT,
)
from sgr.testing.models import TestCase
from sgr.testing.runner import TestRunner


class DummyResponse:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": content})()})()]


class DummyClient:
    def __init__(self, content: str):
        self.response = DummyResponse(content=content)

    def chat(self, messages: list[dict[str, str]]):  # noqa: ANN401
        self.last_messages = messages
        return self.response


class ConversationSplitterPipelineTests(unittest.TestCase):
    def test_parses_structured_split(self) -> None:
        response = ConversationSplit(
            thinking="В сообщении один общий вопрос.",
            has_request_several_orders=False,
            orders=[
                OrderContext(
                    context_text="Клиент спрашивает про доставку заказа 1234567.",
                    mentioned_id="1234567",
                )
            ],
        )
        client = DummyClient(content=response.model_dump_json())
        pipeline = ConversationSplitterPipeline(client=client)

        result = pipeline.run(message_text="Где мой заказ 1234567?")

        self.assertIsInstance(result, ConversationSplit)
        self.assertEqual(result.orders[0].mentioned_id, "1234567")
        self.assertEqual(
            client.last_messages,
            [
                {"role": "system", "content": SPLITTER_PROMPT},
                {"role": "user", "content": "Где мой заказ 1234567?"},
            ],
        )

    def test_handles_multiple_orders(self) -> None:
        payload = {
            "thinking": "Два отдельных заказа требуют ответа.",
            "orders": [
                {
                    "context_text": "Уточнить статус заказа 1234567.",
                    "mentioned_id": "1234567",
                },
                {
                    "context_text": "В заказе 7654321 не хватает позиции.",
                    "mentioned_id": "7654321",
                },
            ],
            "has_request_several_orders": True,
        }
        client = DummyClient(content=json.dumps(payload))
        pipeline = ConversationSplitterPipeline(client=client)

        result = pipeline.run(
            message_text="Где мой заказ 1234567? И что с заказом 7654321 — там не хватает ершика",
        )

        self.assertEqual(len(result.orders), 2)
        self.assertEqual({ctx.mentioned_id for ctx in result.orders}, {"1234567", "7654321"})

    def test_default_comparator_checks_count_and_flag(self) -> None:
        payload = {
            "thinking": "Два отдельных заказа требуют ответа.",
            "orders": [
                {
                    "context_text": "Уточнить статус заказа 1234567.",
                    "mentioned_id": "1234567",
                },
                {
                    "context_text": "В заказе 7654321 не хватает позиции.",
                    "mentioned_id": "7654321",
                },
            ],
            "has_request_several_orders": True,
        }
        client = DummyClient(content=json.dumps(payload))
        pipeline = ConversationSplitterPipeline(client=client)

        test_cases = [
            TestCase(
                id="cmp",
                params={
                    "message_text": "Где мой заказ 1234567? И еще вопрос про заказ 7654321 - там не хватает ершика",
                },
                expected_output={"expected_orders_count": 2, "has_request_several_orders": True},
            )
        ]

        run = TestRunner().run(pipeline=pipeline, test_cases=test_cases)

        self.assertTrue(run.results[0].passed)


if __name__ == "__main__":
    unittest.main()
