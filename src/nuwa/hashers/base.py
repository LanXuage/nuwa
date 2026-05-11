from typing import ByteString
from abc import abstractmethod
from ..base import AsyncClosableContext


class DataHasher(AsyncClosableContext):
    @abstractmethod
    async def digest(self, data: ByteString) -> int:
        raise NotImplementedError

    @abstractmethod
    async def hexdigest(self, data: ByteString) -> str:
        raise NotImplementedError

    async def close(self) -> None:
        pass

    async def initialize(self) -> None:
        pass
