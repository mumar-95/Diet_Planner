"""Fetch/cache appetizing images that match a food or recipe name."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = ROOT_DIR / "assets" / "food_cache"
FALLBACK_DIR = ROOT_DIR / "assets"


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return cleaned[:80] or "food"


def _cache_path(label: str) -> Path:
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10]
    return CACHE_DIR / f"{_slug(label)}-{digest}.jpg"


def _request_json(url: str, timeout: int = 15) -> dict | list | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NourishAI-DietPlanner/1.0 (local nutrition assistant)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as exc:  # noqa: BLE001
        logger.info("JSON fetch failed for %s: %s", url, exc)
        return None


def _download(url: str, timeout: int = 30) -> bytes | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NourishAI-DietPlanner/1.0 (local nutrition assistant)",
            "Accept": "image/*,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if data and (
                "image" in ctype
                or data[:3] == b"\xff\xd8\xff"
                or data[:8] == b"\x89PNG\r\n\x1a\n"
            ):
                return data
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("Food image download failed: %s", exc)
    return None


def _search_terms(food_label: str) -> list[str]:
    label = re.sub(r"\s+", " ", (food_label or "").strip())
    terms = [label] if label else []
    # Also try shorter phrases for better API hits.
    words = [w for w in re.split(r"[^a-zA-Z0-9]+", label.lower()) if len(w) > 2]
    stop = {
        "with",
        "and",
        "the",
        "for",
        "from",
        "recipe",
        "macros",
        "calories",
        "healthy",
        "food",
        "meal",
    }
    words = [w for w in words if w not in stop]
    if len(words) >= 2:
        terms.append(" ".join(words[:3]))
    if words:
        terms.append(words[0])
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        key = t.lower()
        if key and key not in seen:
            seen.add(key)
            out.append(t)
    return out or ["healthy meal"]


def _themealdb_candidates(term: str) -> list[str]:
    url = (
        "https://www.themealdb.com/api/json/v1/1/search.php?s="
        + urllib.parse.quote(term)
    )
    payload = _request_json(url, timeout=12)
    if not isinstance(payload, dict):
        return []
    meals = payload.get("meals") or []
    urls: list[str] = []
    for meal in meals[:5]:
        thumb = meal.get("strMealThumb")
        if isinstance(thumb, str) and thumb.startswith("http"):
            urls.append(thumb)
    return urls


def _openverse_candidates(term: str) -> list[str]:
    url = (
        "https://api.openverse.org/v1/images/"
        f"?q={urllib.parse.quote(term + ' food')}"
        "&page_size=8&format=json"
    )
    payload = _request_json(url, timeout=15)
    if not isinstance(payload, dict):
        return []
    urls: list[str] = []
    for item in payload.get("results") or []:
        for key in ("url", "thumbnail"):
            value = item.get(key)
            if isinstance(value, str) and value.startswith("http"):
                urls.append(value)
                break
    return urls


def _wikimedia_candidates(term: str) -> list[str]:
    url = (
        "https://en.wikipedia.org/w/api.php?action=query&generator=search"
        f"&gsrsearch={urllib.parse.quote(term + ' food')}"
        "&gsrlimit=8&prop=pageimages&piprop=thumbnail&pithumbsize=800&format=json"
    )
    payload = _request_json(url, timeout=15)
    if not isinstance(payload, dict):
        return []
    pages = (payload.get("query") or {}).get("pages") or {}
    urls: list[str] = []
    for page in pages.values():
        thumb = (page.get("thumbnail") or {}).get("source")
        if isinstance(thumb, str) and thumb.startswith("http"):
            urls.append(thumb)
    return urls


def _pollinations_url(food_label: str) -> str:
    prompt = urllib.parse.quote(
        "appetizing professional food photography of "
        f"{food_label}, plated meal, natural lighting, realistic, no text, no watermark"
    )
    seed = int(hashlib.sha1(food_label.encode("utf-8")).hexdigest()[:8], 16) % 10_000_000
    return (
        f"https://image.pollinations.ai/prompt/{prompt}"
        f"?width=768&height=768&nologo=true&seed={seed}"
    )


def save_uploaded_image(filename: str, data: bytes) -> str | None:
    """Persist an uploaded food photo and return its local path."""
    if not data:
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename or "upload.jpg").suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    path = CACHE_DIR / f"upload-{hashlib.sha1(data).hexdigest()[:12]}{suffix}"
    path.write_bytes(data)
    return str(path)


def get_food_image_path(food_name: str, query: str = "") -> str | None:
    """Return a local image path that matches the requested food/recipe."""
    label = (food_name or query or "").strip() or "healthy plated meal"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = _cache_path(label.lower())
    if cached.exists() and cached.stat().st_size > 1000:
        return str(cached)

    candidate_urls: list[str] = []
    for term in _search_terms(label):
        for collector in (_themealdb_candidates, _openverse_candidates, _wikimedia_candidates):
            try:
                candidate_urls.extend(collector(term))
            except Exception as exc:  # noqa: BLE001
                logger.info("Image source %s failed: %s", collector.__name__, exc)
        if candidate_urls:
            break

    # Keep order but unique
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in candidate_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    for url in unique_urls[:8]:
        data = _download(url)
        if data and len(data) > 2000:
            cached.write_bytes(data)
            return str(cached)

    # Last-resort generative endpoint (may be rate-limited).
    data = _download(_pollinations_url(label), timeout=45)
    if data and len(data) > 2000:
        cached.write_bytes(data)
        return str(cached)

    for name in ("card-meals.jpg", "card-macros.jpg", "hero-nutrition.jpg", "card-alternatives.jpg"):
        path = FALLBACK_DIR / name
        if path.exists():
            return str(path)
    return None
