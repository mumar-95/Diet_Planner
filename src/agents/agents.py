"""CrewAI agent definitions for the food & nutrition assistant."""

from __future__ import annotations

from crewai import Agent, LLM

from src.agents.groq_compat import patch_crewai_cache_breakpoint
from src.agents.tools import search_nutrition_kb
from src.config import refresh_settings

patch_crewai_cache_breakpoint()


def _litellm_groq_model(model_id: str) -> str:
    """Build a LiteLLM model id for Groq without double-prefixing."""
    model_id = (model_id or "").strip()
    if model_id.startswith("groq/"):
        return model_id
    return f"groq/{model_id}"


def build_llm() -> LLM:
    settings = refresh_settings()
    return LLM(
        model=_litellm_groq_model(settings.groq_model),
        api_key=settings.groq_api_key,
        temperature=0.2,
        is_litellm=True,
    )


def create_nutrition_research_agent(llm: LLM | None = None) -> Agent:
    return Agent(
        role="Nutrition Research Agent",
        goal=(
            "Find accurate, relevant nutrition information for the user's food "
            "or question using the knowledge base and sound nutrition principles."
        ),
        backstory=(
            "You are a meticulous nutrition researcher. You prioritize evidence "
            "from the knowledge base, cite practical context, and clearly note "
            "when values are approximate educational estimates."
        ),
        tools=[search_nutrition_kb],
        llm=llm or build_llm(),
        verbose=False,
        allow_delegation=False,
    )


def create_food_analysis_agent(llm: LLM | None = None) -> Agent:
    return Agent(
        role="Food Analysis Agent",
        goal=(
            "Analyze food ingredients and estimate calories, protein, "
            "carbohydrates, and fats for a typical serving."
        ),
        backstory=(
            "You specialize in breaking foods into macronutrient estimates. "
            "You state serving size assumptions and keep numbers realistic."
        ),
        tools=[search_nutrition_kb],
        llm=llm or build_llm(),
        verbose=False,
        allow_delegation=False,
    )


def create_meal_planner_agent(llm: LLM | None = None) -> Agent:
    return Agent(
        role="Meal Planner Agent",
        goal=(
            "Suggest practical daily meal combinations that complement the "
            "user's food or nutrition goal."
        ),
        backstory=(
            "You design balanced day plans with breakfast, lunch, dinner, and "
            "snacks. You respect common dietary patterns and keep suggestions "
            "simple to cook or assemble."
        ),
        tools=[search_nutrition_kb],
        llm=llm or build_llm(),
        verbose=False,
        allow_delegation=False,
    )


def create_recommendation_agent(llm: LLM | None = None) -> Agent:
    return Agent(
        role="Recommendation Agent",
        goal=(
            "Generate personalized healthy alternatives and synthesize the "
            "final structured nutrition response for the user."
        ),
        backstory=(
            "You are a practical nutrition coach. You recommend healthier swaps "
            "and assemble a clear final answer from the research, analysis, and "
            "meal-planning findings."
        ),
        tools=[search_nutrition_kb],
        llm=llm or build_llm(),
        verbose=False,
        allow_delegation=False,
    )
