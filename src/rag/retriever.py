"""Retrieve similar nutrition chunks from Supabase pgvector."""

from __future__ import annotations

from typing import Any

from src.db.repositories import match_chunks
from src.rag.embeddings import embed_query


def retrieve_chunks(
    query: str,
    *,
    match_count: int = 8,
    document_id: str | None = None,
) -> list[dict[str, Any]]:
    embedding = embed_query(query)
    return match_chunks(
        embedding,
        match_count=match_count,
        document_id=document_id,
    )


def format_context(chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return "No relevant knowledge-base passages were retrieved."
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        similarity = chunk.get("similarity")
        sim_txt = f" (similarity={similarity:.3f})" if isinstance(similarity, (int, float)) else ""
        parts.append(f"[{i}]{sim_txt}\n{chunk.get('content', '').strip()}")
    return "\n\n".join(parts)
