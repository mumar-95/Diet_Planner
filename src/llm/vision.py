"""Groq vision helpers for food image identification."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from src.config import refresh_settings
from src.llm.groq_client import get_groq_client

VISION_SYSTEM = (
    "You identify foods in images for a nutrition assistant. "
    "Describe the visible food items clearly and concisely. "
    "If no food is visible, say exactly: NO_FOOD_DETECTED."
)


def _guess_mime(filename: str, fallback: str = "image/jpeg") -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or fallback


def identify_food_from_image_bytes(
    data: bytes,
    *,
    filename: str = "food.jpg",
    mime_type: str | None = None,
) -> str:
    """Return a short food description from an image using Groq vision."""
    settings = refresh_settings()
    client = get_groq_client()
    mime = mime_type or _guess_mime(filename)
    b64 = base64.b64encode(data).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    response = client.chat.completions.create(
        model=settings.groq_vision_model,
        temperature=0.1,
        max_tokens=400,
        messages=[
            {"role": "system", "content": VISION_SYSTEM},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Identify the food in this image. "
                            "List main items and typical preparation if obvious."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    )
    return (response.choices[0].message.content or "").strip()


def identify_food_from_path(path: str | Path) -> str:
    p = Path(path)
    return identify_food_from_image_bytes(
        p.read_bytes(),
        filename=p.name,
    )
