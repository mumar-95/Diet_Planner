"""Work around CrewAI injecting Anthropic-only cache_breakpoint into Groq calls.

See: https://github.com/crewAIInc/crewAI/issues/5886
"""

from __future__ import annotations

_patched = False


def patch_crewai_cache_breakpoint() -> None:
    """Disable cache_breakpoint injection so Groq / OpenAI-compatible APIs accept messages."""
    global _patched
    if _patched:
        return
    try:
        import crewai.llms.cache as crewai_cache
    except Exception:
        return

    crewai_cache.mark_cache_breakpoint = lambda msg: msg  # type: ignore[assignment]
    _patched = True
