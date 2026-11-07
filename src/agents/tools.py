"""Tools available to CrewAI nutrition agents."""

from __future__ import annotations

from crewai.tools import tool

from src.rag.retriever import format_context, retrieve_chunks


@tool("Search nutrition knowledge base")
def search_nutrition_kb(query: str) -> str:
    """Search the Supabase nutrition knowledge base for relevant passages.

    Args:
        query: Food name or nutrition question to search for.
    """
    chunks = retrieve_chunks(query, match_count=5)
    return format_context(chunks)
