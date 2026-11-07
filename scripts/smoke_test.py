"""Basic import and parsing smoke checks (no live API/DB required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.chunking import chunk_text
from src.services.orchestrator import parse_crew_output
from src.services.scope_guard import heuristic_is_food_related, out_of_scope_message


def main() -> None:
    assert "food and its nutritions" in out_of_scope_message().lower()
    assert heuristic_is_food_related("protein in chicken") is True
    assert heuristic_is_food_related("stock market today") is False
    chunks = chunk_text("Calories measure energy. " * 40)
    assert len(chunks) >= 1

    parsed = parse_crew_output(
        "===NUTRITIONAL_INFO===\nGood food\n"
        "===MACROS===\nFood: Egg\nServing: 1\nCalories: 70 kcal\n"
        "Protein: 6 g\nCarbohydrates: 0.5 g\nFats: 5 g\n"
        "===ALTERNATIVES===\nEgg whites\n"
        "===MEAL_PLAN===\nOmelette breakfast\n"
        "===NOTES===\nEducational\n"
    )
    assert parsed["food_name"] == "Egg"
    assert parsed["macros"]["protein"] == "6 g"
    print("smoke_test OK")


if __name__ == "__main__":
    main()
