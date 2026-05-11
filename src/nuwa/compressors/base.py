from abc import abstractmethod
from ..base import AsyncClosableContext
from typing import ByteString


class Compressor(AsyncClosableContext):
    @abstractmethod
    async def compress(self, data: ByteString) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def decompress(self, data: ByteString) -> bytes:
        raise NotImplementedError

    async def close(self) -> None:
        pass

    async def initialize(self) -> None:
        pass
