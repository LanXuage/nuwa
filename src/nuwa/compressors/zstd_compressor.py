import zstandard as zstd

from .base import Compressor
from typing import ByteString


class ZSTDCompressor(Compressor):
    def __init__(
        self,
        level: int = 3,
        dict_data: zstd.ZstdCompressionDict | None = None,
        compression_params: zstd.ZstdCompressionParameters | None = None,
        write_checksum: bool | None = None,
        write_content_size: bool | None = None,
        write_dict_id: bool | None = None,
        threads: int = 0,
        max_window_size: int = 0,
        format: int = zstd.FORMAT_ZSTD1,
    ) -> None:
        self.compressor = zstd.ZstdCompressor(
            level=level,
            dict_data=dict_data,
            compression_params=compression_params,
            write_checksum=write_checksum,
            write_content_size=write_content_size,
            write_dict_id=write_dict_id,
            threads=threads,
        )
        self.decompressor = zstd.ZstdDecompressor(
            dict_data=dict_data, max_window_size=max_window_size, format=format
        )

    async def compress(self, data: ByteString) -> bytes:
        return self.compressor.compress(data)

    async def decompress(self, data: ByteString) -> bytes:
        return self.decompressor.decompress(data)
