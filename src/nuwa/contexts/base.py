from abc import abstractmethod
from typing import Iterable

from ..base import AsyncClosableContext
from openai.types.chat import ChatCompletionMessageParam


class Context(AsyncClosableContext):
    @abstractmethod
    async def get_messages(self) -> Iterable[ChatCompletionMessageParam]:
        raise NotImplementedError

    @abstractmethod
    async def add_messages(self, messages: Iterable[ChatCompletionMessageParam]):
        raise NotImplementedError
