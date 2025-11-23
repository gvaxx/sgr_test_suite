"""Base abstractions for LLM-powered pipelines."""
from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError, loads
from typing import Any, Callable, Iterable, Mapping

from pydantic import BaseModel, ValidationError

from sgr.llm.client import OpenAIClient

ChatMessages = Iterable[dict[str, str]]


@dataclass(slots=True)
class PromptTemplate:
    """Container for prompt strings.

    The ``user`` template is formatted with keyword arguments passed to
    :meth:`ChatPipeline.run`.
    """

    user: str
    system: str | None = None


@dataclass(slots=True)
class ChatPipeline:
    """Simple pipeline that renders prompts and calls the OpenAI client."""

    client: OpenAIClient
    prompt: PromptTemplate
    name: str = "ChatPipeline"
    response_parser: Callable[[Any], Any] | None = None

    def _build_messages(self, params: Mapping[str, Any]) -> list[dict[str, str]]:
        try:
            user_prompt = self.prompt.user.format(**params)
        except KeyError as exc:  # noqa: B904
            missing = exc.args[0]
            msg = f"Missing parameter for prompt placeholder: {missing}"
            raise ValueError(msg) from exc

        messages: list[dict[str, str]] = []
        if self.prompt.system:
            messages.append({"role": "system", "content": self.prompt.system})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    @staticmethod
    def _default_parser(response: Any) -> Any:
        try:
            return response.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            msg = "Unable to extract message content from response"
            raise ValueError(msg) from exc

    def run(self, **params: Any) -> Any:
        messages = self._build_messages(params)
        response = self.client.chat(messages)
        parser = self.response_parser or self._default_parser
        return parser(response)


@dataclass(slots=True)
class StructuredChatPipeline(ChatPipeline):
    """Pipeline that parses model output into a Pydantic schema."""

    response_model: type[BaseModel] | None = None

    def __post_init__(self) -> None:
        if self.response_model is None:  # pragma: no cover - defensive guard
            msg = "StructuredChatPipeline requires a response_model"
            raise ValueError(msg)

    def run(self, **params: Any) -> BaseModel:
        raw = ChatPipeline.run(self, **params)
        try:
            payload = loads(raw)
        except JSONDecodeError as exc:  # noqa: B904
            msg = "Model response is not valid JSON"
            raise ValueError(msg) from exc

        try:
            return self.response_model.model_validate(payload)  # type: ignore[union-attr]
        except ValidationError as exc:  # noqa: B904
            msg = "Model response does not match the expected schema"
            raise ValueError(msg) from exc


__all__ = ["ChatPipeline", "PromptTemplate", "StructuredChatPipeline"]
