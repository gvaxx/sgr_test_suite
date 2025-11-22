"""OpenAI-compatible LLM client with retry support."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Iterable, Optional, Protocol, TypeVar

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, OpenAI, RateLimitError

_logger = logging.getLogger(__name__)


@dataclass
class LLMClientConfig:
    """Configuration for the OpenAI-compatible client."""

    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-4o-mini"
    max_retries: int = 3
    backoff_factor: float = 0.5
    timeout: float = 30.0


ChatMessages = Iterable[dict[str, str]]
T = TypeVar("T")


class _Callable(Protocol[T]):
    def __call__(self) -> T: ...


class _AsyncCallable(Protocol[T]):
    def __call__(self) -> Awaitable[T]: ...


class OpenAIClient:
    """Thin wrapper over ``openai`` clients with built-in retries."""

    def __init__(self, config: LLMClientConfig):
        self.config = config
        client_kwargs = {
            "api_key": config.api_key,
            "base_url": config.base_url,
            "timeout": config.timeout,
        }
        self._client = OpenAI(**client_kwargs)
        self._async_client = AsyncOpenAI(**client_kwargs)

    def _should_retry(self, error: Exception) -> bool:
        retryable = (APIConnectionError, APIError, APITimeoutError, RateLimitError)
        return isinstance(error, retryable)

    def _retry_sync(self, func: _Callable[T]) -> T:
        attempt = 0
        while True:
            try:
                return func()
            except Exception as error:  # noqa: BLE001
                attempt += 1
                if not self._should_retry(error) or attempt > self.config.max_retries:
                    raise
                delay = self.config.backoff_factor * (2 ** (attempt - 1))
                _logger.warning(
                    "Retrying OpenAI call after error (attempt %s/%s): %s", attempt, self.config.max_retries, error
                )
                time.sleep(delay)

    async def _retry_async(self, func: _AsyncCallable[T]) -> T:
        attempt = 0
        while True:
            try:
                return await func()
            except Exception as error:  # noqa: BLE001
                attempt += 1
                if not self._should_retry(error) or attempt > self.config.max_retries:
                    raise
                delay = self.config.backoff_factor * (2 ** (attempt - 1))
                _logger.warning(
                    "Retrying async OpenAI call after error (attempt %s/%s): %s",
                    attempt,
                    self.config.max_retries,
                    error,
                )
                await asyncio.sleep(delay)

    def chat(self, messages: ChatMessages, **kwargs: Any) -> Any:
        """Send chat completion request with retries."""

        def _call() -> Any:
            return self._client.chat.completions.create(model=self.config.model, messages=list(messages), **kwargs)

        return self._retry_sync(_call)

    async def achat(self, messages: ChatMessages, **kwargs: Any) -> Any:
        """Async variant of :meth:`chat`."""

        async def _call() -> Any:
            return await self._async_client.chat.completions.create(
                model=self.config.model, messages=list(messages), **kwargs
            )

        return await self._retry_async(_call)


__all__ = ["LLMClientConfig", "OpenAIClient"]
