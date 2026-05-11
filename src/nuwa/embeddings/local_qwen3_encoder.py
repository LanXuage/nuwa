import os
import torch

from torch import Tensor
import torch.nn.functional as F
from ..hashers import DataHasher
from .base import EmbeddedEncoder
from typing import List, Union, Optional
from ..storages import KVStorage, LocalKVStorage
from transformers import AutoTokenizer, AutoModel


class LocalQwen3EmbeddedEncoder(EmbeddedEncoder):
    def __init__(
        self,
        model: Union[str, os.PathLike[str]],
        max_length: int = 8192,
        storage: Union[str, KVStorage] = LocalKVStorage(path=".embedding_cache"),
        key_hasher: Optional[DataHasher] = None,
    ):
        super().__init__(storage=storage, key_hasher=key_hasher)
        self.max_length = max_length
        self.model_name = model
        self.tokenizer = None
        self.model = None

    def load_model(self):
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, padding_side="left"
        )
        self.model = AutoModel.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16,
            device_map="cuda:0",
            attn_implementation="flash_attention_2",
        )

    def last_token_pool(
        self, last_hidden_states: Tensor, attention_mask: Tensor
    ) -> Tensor:
        left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
        if left_padding:
            return last_hidden_states[:, -1]
        else:
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            return last_hidden_states[
                torch.arange(batch_size, device=last_hidden_states.device),
                sequence_lengths,
            ]

    def get_detailed_instruct(self, task_description: str, query: str) -> str:
        return f"Instruct: {task_description}\nQuery: {query}"

    async def _embeddings(
        self,
        texts: List[str],
        dimension: int = 4096,
        task: Optional[str] = None,
    ) -> List[List[float]]:
        if not texts:
            return []
        if self.tokenizer is None:
            self.load_model()
        if task:
            texts = [self.get_detailed_instruct(task, text) for text in texts]
        if self.tokenizer is None or self.model is None:
            raise ValueError
        batch_dict = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        batch_dict.to(self.model.device)
        outputs = self.model(**batch_dict)
        embeddings = self.last_token_pool(
            outputs.last_hidden_state, batch_dict["attention_mask"]
        )
        embeddings = F.normalize(embeddings, p=2, dim=1)
        return embeddings.tolist()
