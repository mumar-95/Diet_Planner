"""Streamlit UI for the AI Food & Nutrition Assistant."""

from __future__ import annotations

import logging
import math
import os
import re
import socket
import subprocess
import sys
import time
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
VENV_STREAMLIT = ROOT / ".venv" / "Scripts" / "streamlit.exe"
PREFERRED_PORT = 8502

HERO_IMAGE = ASSETS / "hero-nutrition.jpg"
CARD_MACROS = ASSETS / "card-macros.jpg"
CARD_MEALS = ASSETS / "card-meals.jpg"
CARD_ALTS = ASSETS / "card-alternatives.jpg"
EX_RUN = ASSETS / "exercise-run.jpg"
EX_CYCLE = ASSETS / "exercise-cycle.jpg"
EX_STRENGTH = ASSETS / "exercise-strength.jpg"
EX_YOGA = ASSETS / "exercise-yoga.jpg"

TARGET_PROTEIN_G = 50.0
TARGET_CARBS_G = 250.0
TARGET_FAT_G = 70.0

MEAL_OPTIONS = ("Breakfast", "Lunch", "Dinner")

EXERCISES = (
    {"name": "Brisk walk", "kcal_per_min": 4.5, "image": EX_RUN, "blurb": "Easy outdoor pace"},
    {"name": "Jogging", "kcal_per_min": 10.0, "image": EX_RUN, "blurb": "Steady cardio burn"},
    {"name": "Cycling", "kcal_per_min": 8.0, "image": EX_CYCLE, "blurb": "Road or stationary bike"},
    {"name": "Strength", "kcal_per_min": 6.5, "image": EX_STRENGTH, "blurb": "Weights / bodyweight"},
    {"name": "Yoga flow", "kcal_per_min": 3.5, "image": EX_YOGA, "blurb": "Mobility + light burn"},
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="NourishAI · Daily Nutritions",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _using_project_venv() -> bool:
    try:
        prefix = Path(sys.prefix).resolve()
        venv = (ROOT / ".venv").resolve()
        exe = Path(sys.executable).resolve()
        return prefix == venv or venv in exe.parents
    except Exception:
        return False


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _launch_venv_streamlit(port: int) -> None:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [
            str(VENV_STREAMLIT),
            "run",
            str(ROOT / "app.py"),
            "--server.port",
            str(port),
            "--server.headless",
            "false",
        ],
        cwd=str(ROOT),
        env=os.environ.copy(),
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def _is_streamlit_cloud() -> bool:
    """Detect Streamlit Community Cloud / remote hosting."""
    markers = (
        "STREAMLIT_SHARING_MODE",
        "STREAMLIT_CLOUD",
        "STREAMLIT_RUNTIME_EXISTING_SECRETS_PATH",
        "STREAMLIT_APP_IDENTITY",
    )
    if any(os.getenv(key) for key in markers):
        return True
    # Cloud mounts the repo under /mount/src
    return Path("/mount/src").exists()


def _handoff_to_project_venv() -> None:
    # Never attempt local Windows .venv relaunch on Streamlit Cloud / Linux.
    if _is_streamlit_cloud() or sys.platform != "win32":
        return
    if _using_project_venv():
        return
    if not VENV_STREAMLIT.exists():
        return
    if not _port_open(PREFERRED_PORT):
        _launch_venv_streamlit(PREFERRED_PORT)
        for _ in range(80):
            if _port_open(PREFERRED_PORT):
                break
            time.sleep(0.25)
    target = f"http://localhost:{PREFERRED_PORT}"
    st.title("NourishAI")
    if _port_open(PREFERRED_PORT):
        st.success("Open the working app on the project Python environment.")
        st.link_button("Open working app", target, type="primary")
    else:
        st.error("Run `.\\run.bat` to start the app.")
    st.stop()


def _env_error_page(exc: BaseException | None = None) -> None:
    st.title("NourishAI")
    st.error("Use the project `.venv` (Python 3.12) via `run.bat`.")
    if exc is not None:
        st.code(f"{type(exc).__name__}: {exc}")
    st.stop()


_handoff_to_project_venv()


@st.cache_resource(show_spinner="Loading nutrition engine…")
def _load_runtime() -> dict[str, Any]:
    from src.config import OUT_OF_SCOPE_MESSAGE, get_settings
    from src.db.repositories import create_chat_session
    from src.db.supabase_client import ping_supabase
    from src.rag.ingest import index_seed_knowledge_base, index_uploaded_file
    from src.services.orchestrator import process_image_query, process_text_query

    return {
        "OUT_OF_SCOPE_MESSAGE": OUT_OF_SCOPE_MESSAGE,
        "get_settings": get_settings,
        "create_chat_session": create_chat_session,
        "ping_supabase": ping_supabase,
        "index_seed_knowledge_base": index_seed_knowledge_base,
        "index_uploaded_file": index_uploaded_file,
        "process_image_query": process_image_query,
        "process_text_query": process_text_query,
    }


def init_session_state() -> None:
    defaults: dict[str, Any] = {
        "messages": [],
        "chat_session_id": None,
        "last_result": None,
        "food_log": [],
        "selected_date": date.today(),
        "selected_meal": "Breakfast",
        "ask_prompt": "",
        "pending_ask": None,
        "detail_food_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_app_styles() -> None:
    st.html(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');

html, body, [class*="stApp"], .stMarkdown, button {
  font-family: "Outfit", "Segoe UI", sans-serif !important;
}
.stApp {
  background:
    radial-gradient(900px 500px at 8% -5%, rgba(61,220,151,.22), transparent 55%),
    radial-gradient(800px 420px at 95% 5%, rgba(255,145,0,.16), transparent 50%),
    radial-gradient(700px 400px at 50% 100%, rgba(0,188,212,.10), transparent 45%),
    linear-gradient(165deg, #070B0A 0%, #0D1412 40%, #0A100E 100%);
}
[data-testid="stHeader"] { background: transparent; }
.block-container {
  padding-top: 1.1rem !important;
  padding-bottom: 2.5rem !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
  max-width: min(1600px, 100%) !important;
}
section.main .block-container { width: 100% !important; }
.hero-banner {
  position: relative; overflow: hidden; border-radius: 28px;
  border: 1px solid rgba(61,220,151,.25);
  background: linear-gradient(120deg, rgba(15,28,24,.95), rgba(18,24,22,.88));
  box-shadow: 0 20px 50px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.06);
  padding: 1.4rem 1.6rem; margin-bottom: 1.1rem;
}
.hero-banner h1 {
  margin: 0; font-size: 2.35rem; font-weight: 800; letter-spacing: -0.03em;
  background: linear-gradient(90deg, #FFFFFF 10%, #3DDC97 55%, #FFB74D 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-banner p { margin: .45rem 0 0; color: #B7C9C0; font-size: 1.02rem; max-width: 52rem; }
.hero-badges { display:flex; flex-wrap:wrap; gap:.45rem; margin-top:.85rem; }
.hero-badges span {
  background: rgba(61,220,151,.12); color:#CFF5E4; border:1px solid rgba(61,220,151,.28);
  border-radius:999px; padding:.28rem .7rem; font-size:.78rem; font-weight:600;
}
.date-rail {
  display:flex; gap:.65rem; overflow-x:auto; padding:.25rem 0 .4rem; margin-bottom:.35rem;
}
.date-chip {
  min-width: 84px; text-align:center; border-radius:18px; padding:.75rem .6rem;
  background: #18231F; border: 1px solid #2A3A34; color:#EAF3EE !important;
  box-shadow: 0 8px 18px rgba(0,0,0,.25);
}
.date-chip .dow {
  font-size:.78rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:#A7C0B4;
}
.date-chip .dom {
  font-size:1.55rem; font-weight:800; line-height:1.15; color:#FFFFFF; margin-top:.15rem;
}
.date-chip .mon {
  font-size:.8rem; font-weight:600; color:#D7E7DE; margin-top:.1rem;
}
.date-chip.active {
  background: linear-gradient(160deg, #1B5E20, #2E7D32);
  border-color: #69F0AE;
  box-shadow: 0 0 0 2px rgba(105,240,174,.35), 0 12px 28px rgba(46,125,50,.35);
}
.date-chip.active .dow, .date-chip.active .mon { color:#E8FFEF; }
.date-chip.active .dom { color:#FFFFFF; }
.food-title {
  margin: 0 0 .35rem 0 !important;
  font-size: 1.25rem !important;
  font-weight: 760 !important;
  color: #F3FBF7 !important;
  line-height: 1.35 !important;
  white-space: normal !important;
  overflow-wrap: anywhere;
  word-break: normal !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(180deg, rgba(24,35,31,.96), rgba(16,24,21,.94)) !important;
  border: 1px solid rgba(61,220,151,.16) !important;
  border-radius: 22px !important;
  box-shadow: 0 14px 34px rgba(0,0,0,.38);
  width: 100% !important;
}
div[data-testid="stButton"] button {
  border-radius: 14px; font-weight: 700; letter-spacing: .01em;
}
.hbar-wrap { margin: .7rem 0; }
.hbar-label {
  display:flex; justify-content:space-between; color:#D5E4DC; font-size:.92rem; font-weight:600; margin-bottom:.28rem;
}
.hbar { height: 11px; border-radius: 999px; background:#24322C; overflow:hidden; }
.hbar > span { display:block; height:100%; border-radius:999px; }
img { border-radius: 18px; }
@keyframes floatIn { from { opacity:0; transform: translateY(8px);} to { opacity:1; transform:none;} }
.hero-banner, div[data-testid="stVerticalBlockBorderWrapper"] { animation: floatIn .45s ease both; }
</style>
"""
    )


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _pct(value: float | None, target: float) -> float:
    if value is None or target <= 0:
        return 0.0
    return max(0.0, min(value / target, 1.0))


def close_detail() -> None:
    st.session_state.detail_food_id = None


def open_detail(food_id: str) -> None:
    st.session_state.detail_food_id = food_id


def set_meal(meal: str) -> None:
    st.session_state.selected_meal = meal


def set_day(day_iso: str) -> None:
    st.session_state.selected_date = date.fromisoformat(day_iso)


def queue_ask() -> None:
    text = (st.session_state.get("ask_prompt") or "").strip()
    if text:
        st.session_state.pending_ask = text
        st.session_state.ask_prompt = ""


def ensure_chat_session(runtime: dict[str, Any]) -> str | None:
    if st.session_state.chat_session_id:
        return st.session_state.chat_session_id
    try:
        session_id = runtime["create_chat_session"]()
        st.session_state.chat_session_id = session_id
        return session_id
    except Exception as exc:  # noqa: BLE001
        logger.exception("Could not create chat session")
        st.sidebar.warning(f"Chat persistence unavailable: {exc}")
        return None


def _entry_from_result(
    result: Any,
    meal: str,
    query: str,
    *,
    thumb_path: str | None = None,
) -> dict[str, Any]:
    from src.services.food_images import get_food_image_path

    macros = result.macros or {}
    name = macros.get("food") or query.strip() or "Food item"
    # Prefer an uploaded photo; otherwise fetch/generate an image for THIS dish.
    thumb = thumb_path or get_food_image_path(str(name), query)
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "serving": macros.get("serving") or "100g",
        "calories": _parse_number(macros.get("calories")),
        "protein": _parse_number(macros.get("protein")),
        "carbs": _parse_number(macros.get("carbohydrates")),
        "fats": _parse_number(macros.get("fats")),
        "meal": meal,
        "day": st.session_state.selected_date.isoformat(),
        "query": query,
        "result": result,
        "thumb": thumb,
    }


def exercise_plan(kcal: float | None) -> list[dict[str, Any]]:
    burn = float(kcal) if kcal and kcal > 0 else 250.0
    rows = []
    for ex in EXERCISES:
        minutes = max(1, int(math.ceil(burn / ex["kcal_per_min"])))
        rows.append({**ex, "minutes": minutes, "burn_target": int(round(burn))})
    return rows


def render_macro_bar(label: str, value: float | None, target: float, color: str) -> None:
    pct = int(_pct(value, target) * 100)
    shown = f"{value:g}g" if value is not None else "—"
    st.html(
        f"""
<div class="hbar-wrap">
  <div class="hbar-label"><span>{label}</span><span>{shown} · {pct}%</span></div>
  <div class="hbar"><span style="width:{pct}%; background:{color};"></span></div>
</div>
"""
    )


def render_hero() -> None:
    st.html(
        """
<div class="hero-banner">
  <h1>Daily Nutritions</h1>
  <p>Ask any food, unlock macros, healthier swaps, meal ideas, and workouts to burn it off — powered by CrewAI + Groq.</p>
  <div class="hero-badges">
    <span>🥗 Smart food log</span>
    <span>🔥 Macro clarity</span>
    <span>🏃 Burn-off plans</span>
    <span>✨ Dark studio UI</span>
  </div>
</div>
"""
    )


def render_date_strip() -> None:
    today = date.today()
    days = [today + timedelta(days=i) for i in range(-2, 3)]
    selected = st.session_state.selected_date

    chips = []
    for day in days:
        active = "active" if day == selected else ""
        chips.append(
            f'<div class="date-chip {active}">'
            f'<div class="dow">{day.strftime("%a")}</div>'
            f'<div class="dom">{day.day:02d}</div>'
            f'<div class="mon">{day.strftime("%b")}</div>'
            f"</div>"
        )
    st.html(f'<div class="date-rail">{"".join(chips)}</div>')

    # High-contrast selectable labels (readable on dark theme)
    labels = [f"{d.strftime('%a')} {d.day:02d} {d.strftime('%b')}" for d in days]
    default_label = f"{selected.strftime('%a')} {selected.day:02d} {selected.strftime('%b')}"
    if default_label not in labels:
        default_label = labels[2]

    choice = st.pills(
        "Calendar day",
        labels,
        selection_mode="single",
        default=default_label,
        key="date_pills",
        help="Choose the day for your meal log",
    )
    if choice in labels:
        st.session_state.selected_date = days[labels.index(choice)]


def render_meal_tabs() -> None:
    choice = st.segmented_control(
        "Meal period",
        options=list(MEAL_OPTIONS),
        default=st.session_state.selected_meal,
        key="meal_seg",
        width="stretch",
    )
    if choice:
        st.session_state.selected_meal = choice


def render_exercises(kcal: float | None, columns: int = 5) -> None:
    st.markdown("#### Burn it off")
    st.caption("Estimated minutes to offset these calories (educational averages).")
    plan = exercise_plan(kcal)
    cols = st.columns(min(columns, len(plan)), gap="medium")
    for col, item in zip(cols, plan):
        with col:
            with st.container(border=True):
                img = item.get("image")
                if img and Path(img).exists():
                    st.image(str(img), width="stretch", alt=item["name"])
                st.markdown(f"**{item['name']}**")
                st.caption(item["blurb"])
                st.metric("Time", f"{item['minutes']} min", delta=f"~{item['burn_target']} kcal")


def render_food_card(entry: dict[str, Any]) -> None:
    kcal = entry.get("calories")
    protein = entry.get("protein")
    carbs = entry.get("carbs")
    fats = entry.get("fats")
    thumb = entry.get("thumb")
    kcal_txt = f"{int(kcal)} kcal" if kcal is not None else "— kcal"
    # Keep titles readable — avoid giant headings that wrap into a skinny column.
    import html as html_lib

    title = str(entry.get("name") or "Food item")
    safe_title = html_lib.escape(title)

    with st.container(border=True):
        media, body = st.columns([1, 3.2], gap="large")
        with media:
            if thumb and Path(thumb).exists():
                st.image(thumb, width="stretch", alt=title)
        with body:
            st.html(f'<p class="food-title">{safe_title}</p>')
            st.caption(f"🔥 {kcal_txt} · {entry.get('serving') or '—'}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Calories", f"{int(kcal)}" if kcal is not None else "—")
            m2.metric("Protein", f"{protein:g}g" if protein is not None else "—")
            m3.metric("Carbs", f"{carbs:g}g" if carbs is not None else "—")
            m4.metric("Fat", f"{fats:g}g" if fats is not None else "—")
            st.button(
                "View nutrition",
                key=f"open_{entry['id']}",
                icon=":material/chevron_right:",
                type="primary",
                width="content",
                on_click=open_detail,
                args=(entry["id"],),
            )


@st.dialog("Nutrition details", width="large", on_dismiss=close_detail)
def nutrition_dialog(entry: dict[str, Any], out_of_scope_message: str) -> None:
    """Modal detail view — Back / X always returns to the main dashboard."""
    result = entry.get("result")
    if st.button(
        "Back to main window",
        icon=":material/arrow_back:",
        type="primary",
        key=f"dialog_back_{entry['id']}",
        width="stretch",
    ):
        close_detail()
        st.rerun()

    left, right = st.columns([1.1, 1.2], gap="large")
    hero = entry.get("thumb") or (str(HERO_IMAGE) if HERO_IMAGE.exists() else None)

    with left:
        if hero and Path(hero).exists():
            st.image(hero, width="stretch", alt=entry["name"])
        h1, h2 = st.columns([2, 1])
        with h1:
            st.markdown(f"## {entry['name']}")
            st.caption("Nutrition values")
        with h2:
            kcal = entry.get("calories")
            st.markdown(
                f"**{entry.get('serving') or '100g'}**  \n"
                f"{int(kcal) if kcal is not None else '—'} Kcal"
            )
        render_macro_bar("Protein", entry.get("protein"), TARGET_PROTEIN_G, "#69F0AE")
        render_macro_bar("Carbs", entry.get("carbs"), TARGET_CARBS_G, "#FFB74D")
        render_macro_bar("Fat", entry.get("fats"), TARGET_FAT_G, "#4DD0E1")

        if result is not None and getattr(result, "in_scope", True):
            tabs = st.tabs(["Details", "Alternatives", "Meal plan", "Notes"])
            with tabs[0]:
                st.write(getattr(result, "nutritional_info", None) or "—")
            with tabs[1]:
                st.write(getattr(result, "alternatives", None) or "—")
            with tabs[2]:
                st.write(getattr(result, "meal_plan", None) or "—")
            with tabs[3]:
                st.write(getattr(result, "notes", None) or out_of_scope_message)
        elif result is not None:
            st.info(getattr(result, "message", None) or out_of_scope_message)

    with right:
        render_exercises(entry.get("calories"), columns=1)
        st.info(
            "A healthy body comes with good nutrition. Keep logging meals!",
            icon=":material/favorite:",
        )


def sidebar(runtime: dict[str, Any]) -> list[str]:
    get_settings = runtime["get_settings"]
    ping_supabase = runtime["ping_supabase"]
    index_seed_knowledge_base = runtime["index_seed_knowledge_base"]
    index_uploaded_file = runtime["index_uploaded_file"]
    process_image_query = runtime["process_image_query"]

    settings = get_settings()
    missing = settings.missing_keys()
    st.sidebar.markdown("### Setup")
    if missing:
        st.sidebar.error("Missing: " + ", ".join(missing))
    else:
        st.sidebar.success("Groq + Supabase connected", icon=":material/check_circle:")

    if st.sidebar.button("Check Supabase", width="stretch", key="sb_ping"):
        try:
            ping_supabase()
            st.sidebar.success("Supabase OK")
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"Supabase error: {exc}")

    st.sidebar.divider()
    st.sidebar.markdown("### Knowledge base")
    if st.sidebar.button(
        "Index seed knowledge base", type="primary", width="stretch", key="sb_index"
    ):
        with st.sidebar.status("Indexing…"):
            try:
                results = index_seed_knowledge_base()
                total = sum(r.get("chunk_count", 0) for r in results)
                st.sidebar.success(f"Indexed {len(results)} files ({total} chunks).")
            except Exception as exc:  # noqa: BLE001
                st.sidebar.error(f"Seed indexing failed: {exc}")

    uploaded = st.sidebar.file_uploader(
        "Upload nutrition PDF / DOCX / TXT",
        type=["pdf", "docx", "txt", "md"],
        key="kb_upload",
    )
    if uploaded is not None and st.sidebar.button(
        "Ingest document", width="stretch", key="sb_ingest"
    ):
        with st.sidebar.status(f"Indexing {uploaded.name}…"):
            try:
                meta = index_uploaded_file(uploaded.name, uploaded.getvalue())
                st.sidebar.success(
                    f"Indexed {meta['file_name']} ({meta['chunk_count']} chunks)."
                )
            except Exception as exc:  # noqa: BLE001
                st.sidebar.error(f"Ingest failed: {exc}")

    st.sidebar.divider()
    st.sidebar.markdown("### Food photo")
    image = st.sidebar.file_uploader(
        "Upload a food photo",
        type=["png", "jpg", "jpeg", "webp"],
        key="food_image_uploader",
    )
    image_note = st.sidebar.text_input(
        "Optional note",
        placeholder="e.g. Estimate macros for this plate",
        key="food_image_note",
    )
    if image is not None and st.sidebar.button(
        "Analyze food image", type="primary", width="stretch", key="sb_analyze"
    ):
        if missing:
            st.sidebar.error("Fill `.env` keys before analyzing images.")
        else:
            session_id = ensure_chat_session(runtime)
            with st.spinner("Analyzing food photo…"):
                try:
                    from src.services.food_images import save_uploaded_image

                    raw = image.getvalue()
                    saved_thumb = save_uploaded_image(image.name, raw)
                    result = process_image_query(
                        raw,
                        filename=image.name,
                        mime_type=image.type,
                        session_id=session_id,
                        user_note=image_note,
                    )
                    query = f"[Food image: {image.name}] {image_note}".strip()
                    entry = _entry_from_result(
                        result,
                        st.session_state.selected_meal,
                        query,
                        thumb_path=saved_thumb,
                    )
                    st.session_state.food_log.insert(0, entry)
                    st.session_state.last_result = result
                    st.session_state.ask_prompt = ""
                    st.sidebar.success(f"Added {entry['name']}")
                except Exception as exc:  # noqa: BLE001
                    st.sidebar.error(f"Image analysis failed: {exc}")
    return missing


def _handle_prompt(prompt: str, runtime: dict[str, Any], missing: list[str]) -> None:
    prompt = prompt.strip()
    if not prompt:
        return
    if missing:
        st.error("Fill missing `.env` keys: " + ", ".join(missing))
        return

    session_id = ensure_chat_session(runtime)
    try:
        result = runtime["process_text_query"](prompt, session_id=session_id)
        st.session_state.last_result = result
        with st.status("Finding a matching food photo…", expanded=False) as status:
            entry = _entry_from_result(result, st.session_state.selected_meal, prompt)
            if entry.get("thumb"):
                status.update(label="Food photo ready", state="complete")
            else:
                status.update(label="Using fallback photo", state="complete")
        st.session_state.food_log.insert(0, entry)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append(
            {"role": "assistant", "content": result.message, "result": result}
        )
        st.success(
            f"Added **{entry['name']}** to {entry['meal']} with a matching dish photo. "
            "Click **View nutrition** for the full card."
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Query failed")
        st.error(f"Something went wrong: {exc}")


def render_ask_panel() -> None:
    st.markdown("#### Ask about a food")
    quick = st.pills(
        "Quick starts",
        ["apple", "pineapple", "grilled chicken", "avocado toast"],
        selection_mode="single",
        key="quick_pill",
        label_visibility="collapsed",
    )
    if quick and not (st.session_state.get("ask_prompt") or "").strip():
        st.session_state.ask_prompt = quick

    st.text_input(
        "Search foods",
        placeholder="Search foods or ask a nutrition question…",
        key="ask_prompt",
        label_visibility="collapsed",
    )
    st.button(
        "Ask nutrition crew",
        type="primary",
        icon=":material/restaurant_menu:",
        width="stretch",
        key="ask_submit",
        on_click=queue_ask,
    )


def process_pending_ask(runtime: dict[str, Any], missing: list[str]) -> None:
    pending = st.session_state.get("pending_ask")
    if not pending:
        return
    st.session_state.pending_ask = None
    with st.spinner("Nutrition crew is working…"):
        _handle_prompt(pending, runtime, missing)


def render_food_grid(entries: list[dict[str, Any]]) -> None:
    if not entries:
        st.caption("No foods logged for this meal yet — ask above to add one.")
        return
    # One wide card per row so titles/macros never collapse into a skinny column.
    for entry in entries:
        render_food_card(entry)


def render_home_dashboard(missing: list[str], out_of_scope_message: str) -> None:
    render_hero()
    if missing:
        st.error("Fill `.env` keys, then restart: " + ", ".join(missing), icon=":material/key:")

    # Full-width control strip
    c1, c2, c3 = st.columns([1.2, 1.0, 1.3], gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("##### Calendar")
            render_date_strip()
    with c2:
        with st.container(border=True):
            st.markdown("##### Meal")
            render_meal_tabs()
    with c3:
        with st.container(border=True):
            render_ask_panel()

    day_key = st.session_state.selected_date.isoformat()
    meal = st.session_state.selected_meal
    entries = [
        e
        for e in st.session_state.food_log
        if e.get("day") == day_key and e.get("meal") == meal
    ]

    st.markdown(f"### {meal} log")
    log_col, burn_col = st.columns([2.2, 1], gap="large")

    with log_col:
        if not entries and HERO_IMAGE.exists() and not st.session_state.food_log:
            st.image(str(HERO_IMAGE), width="stretch", alt="Healthy meal inspiration")
            st.markdown(
                "Search any food above to build your log. Each item gets a matching dish photo, "
                "macros, and a **View nutrition** panel with burn-off workouts."
            )
        render_food_grid(entries)

    with burn_col:
        sample_kcal = None
        if entries and entries[0].get("calories") is not None:
            sample_kcal = entries[0]["calories"]
        elif st.session_state.last_result is not None:
            macros = getattr(st.session_state.last_result, "macros", None) or {}
            sample_kcal = _parse_number(macros.get("calories"))
        render_exercises(sample_kcal or 300, columns=1)

    # Open detail as a modal (Back / X always returns to this main window).
    detail_id = st.session_state.get("detail_food_id")
    if detail_id:
        entry = next((e for e in st.session_state.food_log if e["id"] == detail_id), None)
        if entry is None:
            close_detail()
        else:
            nutrition_dialog(entry, out_of_scope_message)

    st.caption("Educational nutrition information only — not medical advice.")


def main() -> None:
    init_session_state()
    inject_app_styles()

    try:
        runtime = _load_runtime()
    except Exception as exc:  # noqa: BLE001
        _env_error_page(exc)
        return

    missing = sidebar(runtime)
    process_pending_ask(runtime, missing)
    render_home_dashboard(missing, runtime["OUT_OF_SCOPE_MESSAGE"])


main()
