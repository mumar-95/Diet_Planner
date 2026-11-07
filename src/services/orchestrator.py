"""End-to-end orchestration for food/nutrition queries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.agents.crew import run_nutrition_crew
from src.config import OUT_OF_SCOPE_MESSAGE
from src.db import repositories as repo
from src.llm.vision import identify_food_from_image_bytes
from src.rag.retriever import format_context, retrieve_chunks
from src.services.scope_guard import is_food_related


SECTION_KEYS = (
    "NUTRITIONAL_INFO",
    "MACROS",
    "ALTERNATIVES",
    "MEAL_PLAN",
    "NOTES",
)


@dataclass
class AssistantResult:
    in_scope: bool
    query_text: str
    input_type: str
    message: str = ""
    nutritional_info: str = ""
    macros: dict[str, Any] = field(default_factory=dict)
    alternatives: str = ""
    meal_plan: str = ""
    notes: str = ""
    food_name: str = ""
    raw_crew_result: str = ""
    rag_context: str = ""
    food_query_id: str | None = None


def _extract_section(text: str, key: str) -> str:
    pattern = rf"==={key}===\s*(.*?)(?====(?:NUTRITIONAL_INFO|MACROS|ALTERNATIVES|MEAL_PLAN|NOTES)===|\Z)"
    match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _parse_macros(macros_text: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "food": "",
        "serving": "",
        "calories": "",
        "protein": "",
        "carbohydrates": "",
        "fats": "",
        "raw": macros_text,
    }
    if not macros_text:
        return result

    patterns = {
        "food": r"(?i)Food:\s*(.+)",
        "serving": r"(?i)Serving:\s*(.+)",
        "calories": r"(?i)Calories:\s*(.+)",
        "protein": r"(?i)Protein:\s*(.+)",
        "carbohydrates": r"(?i)Carbohydrates:\s*(.+)",
        "fats": r"(?i)Fats:\s*(.+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, macros_text)
        if match:
            result[key] = match.group(1).strip()
    return result


def parse_crew_output(raw: str) -> dict[str, Any]:
    sections = {key.lower(): _extract_section(raw, key) for key in SECTION_KEYS}
    macros = _parse_macros(sections.get("macros", ""))
    return {
        "nutritional_info": sections.get("nutritional_info", ""),
        "macros": macros,
        "alternatives": sections.get("alternatives", ""),
        "meal_plan": sections.get("meal_plan", ""),
        "notes": sections.get("notes", ""),
        "food_name": macros.get("food") or "",
    }


def _persist(
    result: AssistantResult,
    session_id: str | None,
) -> AssistantResult:
    if not session_id:
        return result
    try:
        repo.save_chat_message(session_id, "user", result.query_text, source=result.input_type)
        assistant_text = result.message if not result.in_scope else _format_assistant_message(result)
        repo.save_chat_message(
            session_id,
            "assistant",
            assistant_text,
            source="crew" if result.in_scope else "out_of_scope",
        )
        row = repo.create_food_query(
            query_text=result.query_text,
            input_type=result.input_type,
            session_id=session_id,
            food_name=result.food_name or None,
            nutritional_info=result.nutritional_info or None,
            macros=result.macros,
            alternatives=result.alternatives or None,
            meal_plan=result.meal_plan or None,
            raw_crew_result=result.raw_crew_result or result.message or None,
            is_in_scope=result.in_scope,
        )
        result.food_query_id = row.get("id")
    except Exception:
        # Persistence should not break the user-facing answer.
        pass
    return result


def _format_assistant_message(result: AssistantResult) -> str:
    parts = [
        "## Nutritional Information",
        result.nutritional_info or "—",
        "",
        "## Macros",
        f"- Food: {result.macros.get('food') or '—'}",
        f"- Serving: {result.macros.get('serving') or '—'}",
        f"- Calories: {result.macros.get('calories') or '—'}",
        f"- Protein: {result.macros.get('protein') or '—'}",
        f"- Carbohydrates: {result.macros.get('carbohydrates') or '—'}",
        f"- Fats: {result.macros.get('fats') or '—'}",
        "",
        "## Healthy Alternatives",
        result.alternatives or "—",
        "",
        "## Daily Meal Recommendations",
        result.meal_plan or "—",
        "",
        "## Notes",
        result.notes or "—",
    ]
    return "\n".join(parts)


def process_text_query(
    query: str,
    *,
    session_id: str | None = None,
    input_type: str = "text",
    document_id: str | None = None,
) -> AssistantResult:
    text = (query or "").strip()
    result = AssistantResult(
        in_scope=True,
        query_text=text,
        input_type=input_type,
    )

    if not text:
        result.in_scope = False
        result.message = OUT_OF_SCOPE_MESSAGE
        return _persist(result, session_id)

    if not is_food_related(text):
        result.in_scope = False
        result.message = OUT_OF_SCOPE_MESSAGE
        return _persist(result, session_id)

    chunks = retrieve_chunks(text, match_count=8, document_id=document_id)
    rag_context = format_context(chunks)
    result.rag_context = rag_context

    raw = run_nutrition_crew(text, rag_context)
    parsed = parse_crew_output(raw)

    # Fallback if the model ignored section markers
    if not any(
        [
            parsed["nutritional_info"],
            parsed["alternatives"],
            parsed["meal_plan"],
            parsed["notes"],
        ]
    ):
        parsed["nutritional_info"] = raw
        parsed["notes"] = (
            "Educational nutrition information only; not personalized medical advice."
        )

    result.raw_crew_result = raw
    result.nutritional_info = parsed["nutritional_info"]
    result.macros = parsed["macros"]
    result.alternatives = parsed["alternatives"]
    result.meal_plan = parsed["meal_plan"]
    result.notes = parsed["notes"]
    result.food_name = parsed["food_name"]
    result.message = _format_assistant_message(result)
    return _persist(result, session_id)


def process_image_query(
    image_bytes: bytes,
    *,
    filename: str = "food.jpg",
    mime_type: str | None = None,
    session_id: str | None = None,
    user_note: str = "",
) -> AssistantResult:
    description = identify_food_from_image_bytes(
        image_bytes,
        filename=filename,
        mime_type=mime_type,
    )
    if "NO_FOOD_DETECTED" in description.upper():
        result = AssistantResult(
            in_scope=False,
            query_text=user_note or f"[image:{filename}]",
            input_type="image",
            message=OUT_OF_SCOPE_MESSAGE,
        )
        return _persist(result, session_id)

    query = description
    if user_note.strip():
        query = f"{user_note.strip()}\n\nIdentified from image: {description}"
    else:
        query = f"Provide nutrition analysis for: {description}"

    return process_text_query(query, session_id=session_id, input_type="image")
