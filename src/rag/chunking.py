"""LangChain-based text chunking for the nutrition knowledge base."""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> list[str]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [c.strip() for c in splitter.split_text(cleaned) if c.strip()]
