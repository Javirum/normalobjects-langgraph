from langchain_core.messages import HumanMessage

from complaint_workflow.state import ComplaintState
from complaint_workflow.llm import llm

VALID_CATEGORIES = {"portal", "monster", "psychic", "environmental"}


def intake_node(state: ComplaintState) -> dict:
    """Step 1: Intake - Parse and categorize the complaint into one or more categories"""
    print("\n[INTAKE] Processing complaint...")

    complaint = state["complaint"]

    categorization_prompt = f"""Categorize this Downside Up complaint. A complaint may involve MULTIPLE categories.

Categories:
- portal: Issues with portal timing, location, or behavior
- monster: Issues with creature behavior (demogorgons, etc.)
- psychic: Issues with psychic abilities or limitations
- environmental: Issues with electricity, weather, or physical environment

Complaint: {complaint}

Return ONLY the matching category names separated by commas (e.g. portal,monster).
If none of the categories match, respond with: other"""

    response = llm.invoke([HumanMessage(content=categorization_prompt)])
    raw = response.content.strip().lower()
    categories = [c.strip() for c in raw.split(",") if c.strip() in VALID_CATEGORIES]
    if not categories:
        categories = ["other"]

    print(f"[INTAKE] Categorized as: {', '.join(categories)}")
    return {
        "categories": categories,
        "workflow_path": ["intake"],
        "status": "intake",
    }
