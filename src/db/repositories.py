"""CRUD helpers for Supabase tables."""

from __future__ import annotations

from typing import Any

from src.db.supabase_client import get_supabase


def create_chat_session() -> str:
    client = get_supabase()
    result = client.table("chat_sessions").insert({}).execute()
    return result.data[0]["id"]


def save_chat_message(
    session_id: str,
    role: str,
    content: str,
    source: str | None = None,
) -> dict[str, Any]:
    client = get_supabase()
    payload = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "source": source,
    }
    result = client.table("chat_messages").insert(payload).execute()
    return result.data[0]


def upsert_nutrition_document(
    *,
    file_name: str,
    file_type: str,
    raw_text: str,
    source: str = "upload",
    content_sha256: str | None = None,
    chunk_count: int = 0,
) -> dict[str, Any]:
    client = get_supabase()
    existing = (
        client.table("nutrition_documents")
        .select("*")
        .eq("file_name", file_name)
        .eq("source", source)
        .limit(1)
        .execute()
    )
    payload = {
        "file_name": file_name,
        "file_type": file_type,
        "raw_text": raw_text,
        "source": source,
        "content_sha256": content_sha256,
        "chunk_count": chunk_count,
    }
    if existing.data:
        doc_id = existing.data[0]["id"]
        result = (
            client.table("nutrition_documents")
            .update(payload)
            .eq("id", doc_id)
            .execute()
        )
        return result.data[0]

    result = client.table("nutrition_documents").insert(payload).execute()
    return result.data[0]


def update_document_chunk_count(document_id: str, chunk_count: int) -> None:
    client = get_supabase()
    (
        client.table("nutrition_documents")
        .update({"chunk_count": chunk_count})
        .eq("id", document_id)
        .execute()
    )


def delete_chunks_for_document(document_id: str) -> None:
    client = get_supabase()
    (
        client.table("nutrition_chunks")
        .delete()
        .eq("document_id", document_id)
        .execute()
    )


def insert_chunks(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    client = get_supabase()
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        client.table("nutrition_chunks").insert(rows[i : i + batch_size]).execute()


def match_chunks(
    query_embedding: list[float],
    *,
    match_count: int = 8,
    document_id: str | None = None,
) -> list[dict[str, Any]]:
    client = get_supabase()
    params: dict[str, Any] = {
        "query_embedding": query_embedding,
        "match_count": match_count,
        "filter_document_id": document_id,
    }
    result = client.rpc("match_nutrition_chunks", params).execute()
    return result.data or []


def list_nutrition_documents(limit: int = 50) -> list[dict[str, Any]]:
    client = get_supabase()
    result = (
        client.table("nutrition_documents")
        .select("id, file_name, file_type, source, chunk_count, created_at, updated_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def create_food_query(
    *,
    query_text: str,
    input_type: str = "text",
    session_id: str | None = None,
    food_name: str | None = None,
    nutritional_info: str | None = None,
    macros: dict[str, Any] | None = None,
    alternatives: str | None = None,
    meal_plan: str | None = None,
    raw_crew_result: str | None = None,
    is_in_scope: bool = True,
) -> dict[str, Any]:
    client = get_supabase()
    payload = {
        "session_id": session_id,
        "query_text": query_text,
        "food_name": food_name,
        "input_type": input_type,
        "nutritional_info": nutritional_info,
        "macros": macros or {},
        "alternatives": alternatives,
        "meal_plan": meal_plan,
        "raw_crew_result": raw_crew_result,
        "is_in_scope": is_in_scope,
    }
    result = client.table("food_queries").insert(payload).execute()
    return result.data[0]
