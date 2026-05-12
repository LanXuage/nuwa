from fastcrc import crc64
from .base import DataHasher
from typing import ByteString


class CRC64Hasher(DataHasher):
    async def digest(self, data: ByteString) -> int:
        data_bytes = data if isinstance(data, bytes) else bytes(data)
        return crc64.ecma_182(data=data_bytes)

    async def hexdigest(self, data: ByteString) -> str:
        data_bytes = data if isinstance(data, bytes) else bytes(data)
        return hex(crc64.ecma_182(data=data_bytes))[2:].zfill(16)
