import logging

import httpx

from typing import Iterable, Callable, Awaitable, Optional

from openai import AsyncOpenAI, NotGiven, not_given
from openai._client import AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)
from .base import LLM

logger = logging.getLogger(__name__)


class OpenAICompatible(LLM):
    def __init__(
        self,
        model: str,
        api_key: str | Callable[[], Awaitable[str]] | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
        **kwargs,
    ) -> None:
        self._client: Optional[AsyncOpenAI] = AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, **kwargs
        )
        self._model = model

    async def chat(
        self, messages: Iterable[ChatCompletionMessageParam], **kwargs
    ) -> ChatCompletion:
        if self._client is None:
            raise RuntimeError("Client not initialized.")
        if kwargs.get("stream", False):
            logger.warning("Please create new LLM object to enable other model! ")
        kwargs["stream"] = False
        model = kwargs.get("model")
        if model is not None and model != self._model:
            logger.warning(
                "Model mismatch: instance is '%s', but got '%s'. Create a new LLM instance.",
                self._model,
                model,
            )
        kwargs["model"] = self._model
        return await self._client.chat.completions.create(messages=messages, **kwargs)

    async def chat_stream(
        self, messages: Iterable[ChatCompletionMessageParam], **kwargs
    ) -> AsyncStream[ChatCompletionChunk]:
        if self._client is None:
            raise RuntimeError("Client not initialized.")
        if kwargs.get("stream", False):
            logger.warning("Please create new LLM object to enable other model! ")
        kwargs["stream"] = False
        model = kwargs.get("model")
        if model is not None and model != self._model:
            logger.warning(
                "Model mismatch: instance is '%s', but got '%s'. Create a new LLM instance.",
                self._model,
                model,
            )
        kwargs["model"] = self._model
        return await self._client.chat.completions.create(messages=messages, **kwargs)

    async def close(self) -> None:
        client = self._client
        self._client = None
        if client is not None:
            try:
                await client.close()
            finally:
                pass
