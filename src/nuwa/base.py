from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import List, TypedDict, Union, Literal, Dict
from openai.types.chat import ChatCompletionMessageParam


class AsyncClosableContext(ABC):
    def __init__(self) -> None:
        self._initialized = False

    async def __aenter__(self):
        await self.initialize()
        self._initialized = True
        return self

    @abstractmethod
    async def initialize(self) -> None:
        raise NotImplementedError

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError


class StreamChunk(BaseModel):
    state: Literal["DOING", "DONE", "END"]
    content: Union[str, Dict]


class ConversationStorage(ABC):
    @abstractmethod
    async def get_messages(
        self, session_id: str, user_input: str = ""
    ) -> List[ChatCompletionMessageParam]:
        raise NotImplementedError

    @abstractmethod
    async def save_messages(
        self, session_id: str, messages: List[ChatCompletionMessageParam]
    ):
        raise NotImplementedError

    @abstractmethod
    async def clear_messages(self, session_id: str):
        raise NotImplementedError
