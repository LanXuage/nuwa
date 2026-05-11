from fastcrc import crc64
from .base import DataHasher
from typing import ByteString


class CRC64Hasher(DataHasher):
    async def digest(self, data: ByteString) -> int:
        return crc64.ecma_182(data=data)

    async def hexdigest(self, data: ByteString) -> str:
        return hex(crc64.ecma_182(data=data))[2:].zfill(16)
