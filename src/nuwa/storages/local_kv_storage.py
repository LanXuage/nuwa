import os
import asyncio
import msgpack

from .base import KVStorage
from typing import Hashable, Optional, Union


class LocalKVStorage(KVStorage):
    def __init__(self, path: Union[str, os.PathLike[str]]):
        self._path = path
        self._store: dict[Hashable, bytes] = {}
        self._lock = asyncio.Lock()

    async def _set(self, key: Hashable, value: bytes) -> None:
        async with self._lock:
            self._store[key] = value

    async def _get(self, key: Hashable) -> Optional[bytes]:
        async with self._lock:
            return self._store.get(key)

    async def close(self) -> None:
        async with self._lock:
            with open(self._path, "wb") as f:
                msgpack.pack(self._store, f)
            self._store.clear()

    async def initialize(self) -> None:
        if not os.path.exists(self._path):
            return

        loaded = {}

        with open(self._path, "rb") as f:
            loaded = msgpack.unpack(f)

        if not isinstance(loaded, dict):
            raise TypeError(f"Expected dict, got {type(loaded).__name__}")

        for k, v in loaded.items():
            if not isinstance(k, Hashable):
                raise TypeError(f"Key {k!r} is not Hashable")
            if not isinstance(v, bytes):
                raise TypeError(f"Value for key {k!r} is not bytes")

        self._store = loaded
