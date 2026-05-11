import msgpack

from abc import abstractmethod
from typing import Union, List, Optional
from ..storages import LocalKVStorage, KVStorage
from ..base import AsyncClosableContext
from ..hashers import DataHasher, CRC64Hasher


class EmbeddedEncoder(AsyncClosableContext):
    def __init__(
        self,
        storage: Union[str, KVStorage] = LocalKVStorage(path=".embedding_cache"),
        key_hasher: Optional[DataHasher] = None,
    ):
        if isinstance(storage, str):
            storage = LocalKVStorage(path=storage)
        self.storage: KVStorage = storage
        if key_hasher is None:
            key_hasher = CRC64Hasher()
        self.key_hasher: DataHasher = key_hasher

    async def embeddings(
        self,
        texts: List[str],
        dimension: int = 4096,
        task: Optional[str] = None,
    ) -> List[List[float]]:
        results: List[List[float]] = []
        texts_need_embeddings: List[str] = []
        for text in texts:
            _key = self.key_hasher.digest(
                f"{text}::{dimension}::{task if task else ''}".encode(encoding="utf-8")
            )
            _value = await self.storage.get(_key)
            if _value is None:
                texts_need_embeddings.append(text)
            results.append(msgpack.unpackb(_value))
        _results = []
        if texts_need_embeddings:
            _results = await self._embeddings(
                texts=texts_need_embeddings, dimension=dimension, task=task
            )
        i = j = 0
        while i < len(_results) and j < len(results):
            if not results[j]:
                results[j] = _results[i]
                i += 1
            j += 1
        for i, text in enumerate(texts_need_embeddings):
            await self.storage.set(
                self.key_hasher.digest(
                    f"{text}::{dimension}::{task if task else ''}".encode(
                        encoding="utf-8"
                    )
                ),
                msgpack.packb(results[i]),  # type: ignore
            )
        return results

    @abstractmethod
    async def _embeddings(
        self,
        texts: List[str],
        dimension: int = 4096,
        task: Optional[str] = None,
    ) -> List[List[float]]:
        raise NotImplementedError

    async def close(self) -> None:
        pass

    async def initialize(self) -> None:
        pass
