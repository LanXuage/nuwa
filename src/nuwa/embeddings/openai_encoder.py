from ..hashers import DataHasher
from .base import EmbeddedEncoder
from openai import AsyncOpenAI, omit
from typing import List, Union, Optional
from ..storages import KVStorage, LocalKVStorage


class OpenAIEmbeddedEncoder(EmbeddedEncoder):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        use_dimesion: bool = True,
        storage: Union[str, KVStorage] = LocalKVStorage(path=".embedding_cache"),
        key_hasher: Optional[DataHasher] = None,
    ):
        super().__init__(storage=storage, key_hasher=key_hasher)
        self._use_dimesion = use_dimesion
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client: Optional[AsyncOpenAI] = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)

    async def _embeddings(self, texts, dimension=4096, task=None) -> List[List[float]]:
        if self._client is None:
            raise RuntimeError("Client not initialized.")
        embedding = await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=dimension if self._use_dimesion else omit,
        )
        return [item.embedding for item in embedding.data]

    async def close(self) -> None:
        client = self._client
        self._client = None
        if client is not None:
            try:
                await client.close()
            finally:
                pass
