"""Load environment settings for the AI Food & Nutrition Assistant."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
# Override so edits to .env apply after Streamlit / process restarts.
load_dotenv(ROOT_DIR / ".env", override=True)

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
EMBEDDING_DIMS = 384

OUT_OF_SCOPE_MESSAGE = (
    "Hello boss, I am here to assist you on food and its nutritions"
)

KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base"


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    groq_model: str
    groq_vision_model: str
    embedding_model: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    @property
    def supabase_key(self) -> str:
        """Prefer service role for local single-user demo."""
        return self.supabase_service_role_key or self.supabase_anon_key

    def missing_keys(self) -> list[str]:
        required = {
            "GROQ_API_KEY": self.groq_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_KEY": self.supabase_key,
        }
        return [name for name, value in required.items() if not value]


def _from_streamlit_secrets(name: str) -> str:
    """Read flat secrets from Streamlit Cloud / local secrets.toml."""
    try:
        import streamlit as st

        secrets = st.secrets
    except Exception:
        return ""

    try:
        value = secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        try:
            value = secrets[name]
        except Exception:
            return ""

    if value is None:
        return ""
    return str(value).strip()


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
        secret = _from_streamlit_secrets(name)
        if secret:
            return secret
    return ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Re-read .env on each cache miss so model/key edits are picked up after clear.
    load_dotenv(ROOT_DIR / ".env", override=True)
    return Settings(
        groq_api_key=_first_env("GROQ_API_KEY"),
        groq_model=_first_env("GROQ_MODEL") or DEFAULT_GROQ_MODEL,
        groq_vision_model=_first_env("GROQ_VISION_MODEL") or DEFAULT_VISION_MODEL,
        embedding_model=_first_env("EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL,
        supabase_url=_first_env("SUPABASE_URL"),
        supabase_anon_key=_first_env(
            "SUPABASE_ANON_KEY",
            "SUPABASE_PUBLISHABLE_KEY",
        ),
        supabase_service_role_key=_first_env(
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_SECRET_KEY",
        ),
    )


def refresh_settings() -> Settings:
    """Clear cached settings (call after .env changes or on each LLM build)."""
    get_settings.cache_clear()
    return get_settings()
