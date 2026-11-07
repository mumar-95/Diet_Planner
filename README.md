# AI Food & Nutrition Assistant

Streamlit app that answers food and nutrition questions using **CrewAI** agents, **LangChain** chunking, **Supabase pgvector** RAG, and **Groq** (text + vision).

## What it does

1. Nutritional information  
2. Calories, protein, carbohydrates, and fats  
3. Healthy food alternatives  
4. Daily meal recommendations  
5. Answers grounded in a nutrition knowledge base  

Out-of-scope questions return:

> Hello boss, I am here to assist you on food and its nutritions

## Agents (CrewAI)

| Agent | Responsibility |
|-------|----------------|
| Nutrition Research Agent | Finds relevant nutrition facts from the KB |
| Food Analysis Agent | Analyzes ingredients and macros |
| Meal Planner Agent | Suggests meal combinations |
| Recommendation Agent | Personalized healthy suggestions |

## Inputs

- **Text** food name or nutrition question  
- **Food image** (Groq vision identifies the food, then the crew analyzes it)  
- **PDF / DOCX** upload into the Supabase nutrition knowledge base  

## Requirements

- **Python 3.10–3.13** (CrewAI does not support 3.14 yet). This repo’s `.venv` should be created with 3.12 if your default is 3.14:

```bash
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv
.venv\Scripts\activate
```

## Setup

1. Create a Supabase project and run [`sql/schema.sql`](sql/schema.sql) in the SQL Editor.  
2. Copy `.env.example` to `.env` and fill in keys:

```env
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_VISION_MODEL=qwen/qwen3.8-27b
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

3. Install and run (always use the project `.venv`, not system Python 3.14):

```bash
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Or double-click / run `run.bat` from the project folder.

4. In the sidebar, click **Index seed knowledge base** once so pgvector has the starter nutrition docs.

## Project layout

```
app.py
sql/schema.sql
knowledge_base/
src/
  config.py
  db/
  rag/
  llm/
  agents/
  services/
```

## Notes

- Embeddings use local **fastembed** MiniLM (384 dimensions) — no OpenAI key.  
- Educational nutrition info only; not medical advice.
