"""Local embedding helpers (no OpenAI) for pgvector search."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable

from fastembed import TextEmbedding

from src.config import get_settings

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    settings = get_settings()
    return TextEmbedding(model_name=settings.embedding_model or DEFAULT_MODEL)


def _to_list(vectors: Iterable) -> list[list[float]]:
    return [list(map(float, vec)) for vec in vectors]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    return _to_list(model.embed(texts))


def embed_query(text: str) -> list[float]:
    model = get_embedding_model()
    vectors = _to_list(model.query_embed(text))
    return vectors[0]
