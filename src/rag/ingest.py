"""Parse and index nutrition documents into Supabase pgvector."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import BinaryIO

from docx import Document as DocxDocument
from pypdf import PdfReader

from src.config import KNOWLEDGE_BASE_DIR
from src.db import repositories as repo
from src.rag.chunking import chunk_text
from src.rag.embeddings import embed_texts


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def extract_text_from_docx(data: bytes) -> str:
    document = DocxDocument(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs if p.text).strip()


def extract_text_from_plain(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore").strip()


def extract_text(filename: str, data: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(data)
    if lower.endswith(".docx"):
        return extract_text_from_docx(data)
    if lower.endswith((".txt", ".md")):
        return extract_text_from_plain(data)
    raise ValueError(f"Unsupported file type for: {filename}")


def file_type_for(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".docx"):
        return "docx"
    if lower.endswith(".md"):
        return "md"
    return "txt"


def index_text(
    *,
    file_name: str,
    raw_text: str,
    source: str = "upload",
    file_type: str | None = None,
) -> dict:
    """Chunk, embed, and store a nutrition document. Returns document metadata."""
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Document has no extractable text")

    digest = _sha256_text(text)
    doc = repo.upsert_nutrition_document(
        file_name=file_name,
        file_type=file_type or file_type_for(file_name),
        raw_text=text,
        source=source,
        content_sha256=digest,
        chunk_count=0,
    )
    document_id = doc["id"]

    chunks = chunk_text(text)
    embeddings = embed_texts(chunks)
    repo.delete_chunks_for_document(document_id)
    rows = [
        {
            "document_id": document_id,
            "chunk_index": idx,
            "content": chunk,
            "embedding": embedding,
        }
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    repo.insert_chunks(rows)
    repo.update_document_chunk_count(document_id, len(rows))
    return {
        "document_id": document_id,
        "file_name": file_name,
        "chunk_count": len(rows),
        "source": source,
    }


def index_uploaded_file(filename: str, data: bytes, source: str = "upload") -> dict:
    text = extract_text(filename, data)
    return index_text(
        file_name=filename,
        raw_text=text,
        source=source,
        file_type=file_type_for(filename),
    )


def index_uploaded_fileobj(
    filename: str,
    fileobj: BinaryIO,
    source: str = "upload",
) -> dict:
    data = fileobj.read()
    return index_uploaded_file(filename, data, source=source)


def index_seed_knowledge_base(directory: Path | None = None) -> list[dict]:
    """Index all seed .txt/.md files under knowledge_base/."""
    root = directory or KNOWLEDGE_BASE_DIR
    if not root.exists():
        return []

    results: list[dict] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        results.append(
            index_text(
                file_name=path.name,
                raw_text=text,
                source="seed",
                file_type=file_type_for(path.name),
            )
        )
    return results
