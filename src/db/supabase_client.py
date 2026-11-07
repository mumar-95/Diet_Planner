"""Supabase client factory."""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from src.config import get_settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY / SUPABASE_SECRET_KEY "
            "(or SUPABASE_ANON_KEY / SUPABASE_PUBLISHABLE_KEY) in .env"
        )
    return create_client(settings.supabase_url, settings.supabase_key)


def ping_supabase() -> bool:
    """Lightweight connectivity check."""
    client = get_supabase()
    client.table("nutrition_documents").select("id").limit(1).execute()
    return True
