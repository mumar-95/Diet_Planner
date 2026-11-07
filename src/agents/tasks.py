"""CrewAI task definitions."""

from __future__ import annotations

from crewai import Agent, Task


def create_research_task(agent: Agent, user_query: str, rag_context: str) -> Task:
    return Task(
        description=(
            "Research nutrition facts for this user request.\n\n"
            f"USER REQUEST:\n{user_query}\n\n"
            f"RETRIEVED KNOWLEDGE BASE CONTEXT:\n{rag_context}\n\n"
            "Use the Search nutrition knowledge base tool if you need more detail. "
            "Summarize nutritional information, benefits, cautions, and serving notes."
        ),
        expected_output=(
            "A clear nutritional information summary grounded in the knowledge base."
        ),
        agent=agent,
    )


def create_analysis_task(agent: Agent, user_query: str, rag_context: str) -> Task:
    return Task(
        description=(
            "Analyze macros for the food or meal in the user request.\n\n"
            f"USER REQUEST:\n{user_query}\n\n"
            f"RETRIEVED KNOWLEDGE BASE CONTEXT:\n{rag_context}\n\n"
            "Estimate calories, protein (g), carbohydrates (g), and fats (g) for a "
            "typical serving. State the assumed serving size. Use prior research "
            "context when available."
        ),
        expected_output=(
            "Macro breakdown with serving size, calories, protein, carbohydrates, and fats."
        ),
        agent=agent,
    )


def create_meal_plan_task(agent: Agent, user_query: str, rag_context: str) -> Task:
    return Task(
        description=(
            "Create daily meal recommendations related to the user request.\n\n"
            f"USER REQUEST:\n{user_query}\n\n"
            f"RETRIEVED KNOWLEDGE BASE CONTEXT:\n{rag_context}\n\n"
            "Provide breakfast, lunch, dinner, and 1–2 snacks that form a balanced day. "
            "Build on research and analysis findings."
        ),
        expected_output=(
            "A practical one-day meal plan with brief reasons for each meal."
        ),
        agent=agent,
    )


def create_recommendation_task(agent: Agent, user_query: str, rag_context: str) -> Task:
    return Task(
        description=(
            "Synthesize the final answer for the user.\n\n"
            f"USER REQUEST:\n{user_query}\n\n"
            f"RETRIEVED KNOWLEDGE BASE CONTEXT:\n{rag_context}\n\n"
            "Combine prior agent findings into EXACTLY this section format:\n\n"
            "===NUTRITIONAL_INFO===\n"
            "<nutrition narrative>\n"
            "===MACROS===\n"
            "Food: <name>\n"
            "Serving: <serving size>\n"
            "Calories: <number> kcal\n"
            "Protein: <number> g\n"
            "Carbohydrates: <number> g\n"
            "Fats: <number> g\n"
            "===ALTERNATIVES===\n"
            "<healthy alternatives>\n"
            "===MEAL_PLAN===\n"
            "<daily meal recommendations>\n"
            "===NOTES===\n"
            "<short KB-backed notes and disclaimer that this is educational, not medical advice>\n\n"
            "Do not omit section headers. Keep content practical and concise."
        ),
        expected_output=(
            "A final response with NUTRITIONAL_INFO, MACROS, ALTERNATIVES, "
            "MEAL_PLAN, and NOTES sections."
        ),
        agent=agent,
    )
