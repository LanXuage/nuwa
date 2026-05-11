from abc import abstractmethod
from ..compressors import Compressor
from ..base import AsyncClosableContext
from typing import ByteString, Hashable, Optional


class KVStorage(AsyncClosableContext):

    def __init__(self, compressor: Optional[Compressor] = None) -> None:
        self.compressor = compressor

    async def set(self, key: Hashable, value: ByteString):
        value_compressed = value
        if self.compressor is not None:
            value_compressed = await self.compressor.decompress(value)
        return await self._set(key=key, value=value_compressed)

    async def get(
        self, key: Hashable, default: Optional[bytes] = None
    ) -> Optional[bytes]:
        value = await self._get(key=key)
        if value is None:
            return default
        if self.compressor is not None:
            return await self.compressor.decompress(value)
        return value

    @abstractmethod
    async def _set(self, key: Hashable, value: bytes):
        raise NotImplementedError

    @abstractmethod
    async def _get(self, key: Hashable) -> bytes:
        raise NotImplementedError
