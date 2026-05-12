import openai

from typing import Iterable
from abc import abstractmethod

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)

from ..base import AsyncClosableContext


class LLM(AsyncClosableContext):
    @abstractmethod
    async def chat(
        self, messages: Iterable[ChatCompletionMessageParam], **kwargs
    ) -> ChatCompletion:
        raise NotImplementedError

    @abstractmethod
    async def chat_stream(
        self, messages: Iterable[ChatCompletionMessageParam], **kwargs
    ) -> openai.AsyncStream[ChatCompletionChunk]:
        raise NotImplementedError

    async def initialize(self) -> None:
        pass
