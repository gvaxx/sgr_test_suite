"""Conversation splitter pipeline for disentangling orders in user messages."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from models.pipeline import PromptTemplate, StructuredChatPipeline
from sgr.llm import OpenAIClient


class OrderContext(BaseModel):
    context_text: str = Field(
        description="Переформулированная суть проблемы по одному конкретному заказу в одно предложение.",
    )
    mentioned_id: Optional[str] = Field(
        default=None,
        description="Номер заказа, упомянутый в этом контексте (если есть), для справки.",
    )


class ConversationSplit(BaseModel):
    thinking: str = Field(
        description="Рассуждение: сколько разных заказов/ситуаций упомянуто и почему их нужно разделить.",
    )
    has_request_several_orders: bool = Field(
        description="True, если в сообщении явно упомянуто больше одного заказа/ситуации.",
    )
    orders: List[OrderContext] = Field(description="Список выделенных контекстов (минимум 1).")


SPLITTER_PROMPT = """
Ты — ассистент первичной обработки сообщений техподдержки.
Твоя задача — прочитать сообщение пользователя и определить, о скольких РАЗНЫХ заказах или ситуациях идет речь.

## Твои действия
1. Если пользователь пишет про ОДИН заказ или одну общую проблему — верни этот текст, слегка очистив его от "воды", или оставь как есть.
2. Если пользователь пишет про НЕСКОЛЬКО заказов (например, "Где заказ 123? А в заказе 456 разбили чашку") — раздели это на отдельные записи.
3. Для каждой записи создай `context_text`: это должно быть ОДНО емкое предложение, описывающее суть проблемы именно для этого заказа.
4. В поле `has_request_several_orders` поставь true, если упомянуто больше одного заказа/контекста, иначе false.

## Примеры
Вход: "Где мой заказ 1234567? И еще, в прошлом заказе 7654321 не доложили мыло."
Выход:
- context_text: "Клиент спрашивает статус доставки заказа 1234567."
- context_text: "В заказе 7654321 не доложили мыло."

Вход: "Привезите мне еду!"
Выход:
- context_text: "Привезите мне еду!" (один контекст)

Вход: "Заказ 111 готов? И когда вернут деньги за 222?"
Выход:
- context_text: "Вопрос о готовности заказа 111."
- context_text: "Вопрос о сроках возврата денег за заказ 222."

Верни результат строго в формате JSON по схеме ConversationSplit.
"""


def compare_orders_and_flag(actual: ConversationSplit | dict, expected: dict) -> bool:
    """Compare only по количеству заказов и флагу множественных запросов."""

    expected_count = expected.get("expected_orders_count")
    expected_flag = expected.get("has_request_several_orders")

    if isinstance(actual, ConversationSplit):
        actual_orders = actual.orders
        actual_flag = actual.has_request_several_orders
    elif isinstance(actual, dict):
        actual_orders = actual.get("orders", [])
        actual_flag = actual.get("has_request_several_orders")
    else:
        return False

    if expected_count is not None and len(actual_orders) != expected_count:
        return False

    if expected_flag is not None and bool(actual_flag) != expected_flag:
        return False

    return True


class ConversationSplitterPipeline(StructuredChatPipeline):
    """Пайплайн, выделяющий отдельные контексты заказов из текста."""

    default_comparator = staticmethod(compare_orders_and_flag)
    comparators = {"orders_and_flag": staticmethod(compare_orders_and_flag)}

    def __init__(self, client: OpenAIClient) -> None:
        prompt = PromptTemplate(user="{message_text}", system=SPLITTER_PROMPT)
        super().__init__(
            client=client,
            prompt=prompt,
            name="ConversationSplitterPipeline",
            response_model=ConversationSplit,
        )

    def run(self, message_text: str) -> ConversationSplit:
        return super().run(message_text=message_text)


__all__ = [
    "ConversationSplit",
    "ConversationSplitterPipeline",
    "OrderContext",
    "SPLITTER_PROMPT",
    "compare_orders_and_flag",
]
