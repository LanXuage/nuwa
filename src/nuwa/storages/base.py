from abc import abstractmethod
from ..compressors import Compressor
from ..base import AsyncClosableContext
from typing import ByteString, Hashable, Optional, List
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam


class KVStorage(AsyncClosableContext):
    def __init__(self, compressor: Optional[Compressor] = None) -> None:
        self.compressor = compressor

    async def set(self, key: Hashable, value: ByteString):
        value_compressed = value
        if self.compressor is not None:
            value_compressed = await self.compressor.decompress(value)
        return await self._set(key=key, value=value_compressed)

    async def get(
        self, key: Hashable, default: Optional[ByteString] = None
    ) -> Optional[ByteString]:
        value = await self._get(key=key)
        if value is None:
            return default
        if self.compressor is not None:
            return await self.compressor.decompress(value)
        return value

    @abstractmethod
    async def _set(self, key: Hashable, value: ByteString):
        raise NotImplementedError

    @abstractmethod
    async def _get(self, key: Hashable) -> Optional[ByteString]:
        raise NotImplementedError


class Session(BaseModel):
    session_id: str
    title: str
    description: str = ""


class ConversationStorage(AsyncClosableContext):
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def get_messages(
        self, session: Session, user_input: str = ""
    ) -> List[ChatCompletionMessageParam]:
        raise NotImplementedError

    @abstractmethod
    async def save_messages(
        self, session: Session, messages: List[ChatCompletionMessageParam]
    ):
        raise NotImplementedError

    @abstractmethod
    async def clear_messages(self, session_id: str):
        raise NotImplementedError
