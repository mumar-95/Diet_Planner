"""Decide whether a user query is food/nutrition related."""

from __future__ import annotations

import re

from src.config import OUT_OF_SCOPE_MESSAGE
from src.llm.groq_client import chat_completion

FOOD_KEYWORDS = [
    r"\bfood\b",
    r"\bmeal\b",
    r"\bdiet\b",
    r"\bnutrition\b",
    r"\bcalorie\b",
    r"\bprotein\b",
    r"\bcarb(?:ohydrate)?s?\b",
    r"\bfat\b",
    r"\bvitamin\b",
    r"\bmineral\b",
    r"\bbreakfast\b",
    r"\blunch\b",
    r"\bdinner\b",
    r"\bsnack\b",
    r"\brecipe\b",
    r"\bcook(?:ing|ed)?\b",
    r"\beat(?:ing)?\b",
    r"\bhealthy\b",
    r"\bweight\b",
    r"\bmacro\b",
    r"\bfruit\b",
    r"\bvegetable\b",
    r"\bvegan\b",
    r"\bvegetarian\b",
    r"\bdal\b",
    r"\brice\b",
    r"\bchicken\b",
    r"\begg\b",
    r"\boats?\b",
    r"\byogurt\b",
    r"\bpaneer\b",
    r"\btofu\b",
    r"\bsalad\b",
    r"\bsmoothie\b",
    r"\bsupplement\b",
    r"\bfiber\b",
    r"\bportion\b",
]

OUT_OF_SCOPE_PATTERNS = [
    r"\bweather\b",
    r"\bstock market\b",
    r"\bfootball\b",
    r"\bcricket\b",
    r"\bpolitics\b",
    r"\bjoke\b",
    r"\bmovie\b",
    r"\bcryptocurrency\b",
    r"\bprogramming\b",
    r"\bcoding\b",
]


def heuristic_is_food_related(text: str) -> bool | None:
    """Return True/False when confident, else None for LLM fallback."""
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    if lowered == "no_food_detected" or "no_food_detected" in lowered:
        return False

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, lowered) and not any(
            re.search(k, lowered) for k in FOOD_KEYWORDS
        ):
            return False

    if any(re.search(k, lowered) for k in FOOD_KEYWORDS):
        return True

    # Short noun-like food queries: "apple", "brown rice", "grilled salmon"
    # Treat as food-related so the crew can answer without a classifier round-trip.
    if len(lowered.split()) <= 6 and re.fullmatch(r"[a-z0-9\s\-']+", lowered):
        return True

    return None


def llm_is_food_related(text: str) -> bool:
    answer = chat_completion(
        system=(
            "You are a strict classifier for a food and nutrition assistant. "
            "Reply with ONLY YES or NO. YES if the user message is about food, "
            "ingredients, meals, diet, nutrition, calories, or related health-"
            "through-food topics. NO otherwise."
        ),
        user=text,
        temperature=0,
        max_tokens=5,
    )
    normalized = answer.strip().upper()
    return normalized.startswith("YES")


def is_food_related(text: str) -> bool:
    heuristic = heuristic_is_food_related(text)
    if heuristic is not None:
        return heuristic
    try:
        return llm_is_food_related(text)
    except Exception:
        # Fail closed to food assistant message when classifier unavailable
        # only if clearly non-food; otherwise allow crew for ambiguous short queries.
        return len((text or "").split()) <= 6


def out_of_scope_message() -> str:
    return OUT_OF_SCOPE_MESSAGE
