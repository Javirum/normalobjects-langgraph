# Complaint Workflow

A multi-step complaint processing system built with [LangGraph](https://github.com/langchain-ai/langgraph). Complaints are categorized, validated, investigated in parallel, resolved, and closed — with full audit trails.

## How It Works

```
START → Intake → Validation → Investigation (parallel) → Resolution → Closure → END
                      ↓ (no valid categories)
                    Closure
```

1. **Intake** — Classifies the complaint into categories (portal, monster, psychic, environmental)
2. **Validation** — Checks each category against specific rules
3. **Investigation** — Fans out to parallel investigations per valid category using the LangGraph `Send` API
4. **Resolution** — Synthesizes all findings into a unified resolution
5. **Closure** — Verifies satisfaction and generates a closure log

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=sk-...
```

## Usage

### CLI

```bash
python main.py "The portal keeps opening at different times each day"
```

### Web Server

```bash
uvicorn server:app --reload --port 8000
```

Then open http://localhost:8000 to submit and track complaints through the browser.

### Test Suite

```bash
python run_tests.py
```

Runs several sample complaints (single-category, multi-category, invalid) and saves results to `results.json`.

## Project Structure

```
complaint_workflow/
  __init__.py          # Package exports (app, compile_graph, ComplaintState)
  state.py             # State definitions with typed reducers
  graph.py             # Workflow graph (build_workflow, compile_graph)
  llm.py               # Shared ChatOpenAI instance
  nodes/
    intake.py          # Category classification
    validation.py      # Category-specific validation
    investigation.py   # Parallel investigation per category
    resolution.py      # Finding synthesis + escalation check
    closure.py         # Satisfaction verification + closure log
main.py                # CLI entry point
server.py              # FastAPI web app with REST API + HTML frontend
database.py            # SQLite persistence layer (SQLAlchemy)
run_tests.py           # Sample complaint test runner
```
