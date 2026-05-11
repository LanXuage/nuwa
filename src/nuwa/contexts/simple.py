from typing import Iterable

from .base import Context
from openai.types.chat import ChatCompletionMessageParam


class SimpleContext(Context):
    async def add_messages(self, messages: Iterable[ChatCompletionMessageParam]):
        pass

    async def get_messages(self) -> Iterable[ChatCompletionMessageParam]:
        return []

    async def close(self) -> None:
        pass

    async def initialize(self) -> None:
        pass
