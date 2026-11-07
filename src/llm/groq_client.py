"""Groq text client helpers."""

from __future__ import annotations

from functools import lru_cache

from groq import Groq

from src.config import refresh_settings


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    settings = refresh_settings()
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY was not found in the .env file")
    return Groq(api_key=settings.groq_api_key)


def chat_completion(
    *,
    system: str,
    user: str,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    settings = refresh_settings()
    get_groq_client.cache_clear()
    client = get_groq_client()
    response = client.chat.completions.create(
        model=settings.groq_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()
