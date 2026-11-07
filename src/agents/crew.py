"""Assemble and run the nutrition CrewAI crew."""

from __future__ import annotations

from crewai import Crew, Process

from src.agents.agents import (
    build_llm,
    create_food_analysis_agent,
    create_meal_planner_agent,
    create_nutrition_research_agent,
    create_recommendation_agent,
)
from src.agents.groq_compat import patch_crewai_cache_breakpoint
from src.agents.tasks import (
    create_analysis_task,
    create_meal_plan_task,
    create_recommendation_task,
    create_research_task,
)

# CrewAI currently injects cache_breakpoint for all providers; Groq rejects it.
patch_crewai_cache_breakpoint()


def run_nutrition_crew(user_query: str, rag_context: str) -> str:
    """Run the sequential four-agent crew and return the final text output."""
    patch_crewai_cache_breakpoint()
    llm = build_llm()

    research_agent = create_nutrition_research_agent(llm)
    analysis_agent = create_food_analysis_agent(llm)
    planner_agent = create_meal_planner_agent(llm)
    recommend_agent = create_recommendation_agent(llm)

    research_task = create_research_task(research_agent, user_query, rag_context)
    analysis_task = create_analysis_task(analysis_agent, user_query, rag_context)
    meal_task = create_meal_plan_task(planner_agent, user_query, rag_context)
    recommend_task = create_recommendation_task(
        recommend_agent, user_query, rag_context
    )

    # Sequential context handoff
    analysis_task.context = [research_task]
    meal_task.context = [research_task, analysis_task]
    recommend_task.context = [research_task, analysis_task, meal_task]

    crew = Crew(
        agents=[research_agent, analysis_agent, planner_agent, recommend_agent],
        tasks=[research_task, analysis_task, meal_task, recommend_task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff()
    return str(result).strip()
