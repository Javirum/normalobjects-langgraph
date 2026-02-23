from langchain_core.messages import HumanMessage

from complaint_workflow.state import ComplaintState
from complaint_workflow.llm import llm


def resolution_node(state: ComplaintState) -> dict:
    """Step 4: Resolution - Propose a resolution based on all investigation findings"""
    print("\n[RESOLUTION] Generating resolution...")

    findings = state.get("investigation_findings", {})
    if not findings:
        print("[RESOLUTION] Cannot proceed - no documented investigation results")
        return {
            "resolution": "",
            "effectiveness_rating": "",
            "requires_escalation": False,
            "workflow_path": ["resolution_blocked"],
            "status": "resolution_blocked",
        }

    complaint = state["complaint"]
    categories = list(findings.keys())
    categories_label = ", ".join(categories)

    all_findings = "\n\n".join(
        f"--- {cat.upper()} INVESTIGATION ---\n{text}" for cat, text in findings.items()
    )

    resolution_prompt = f"""You are resolving a Downside Up complaint that spans these categories: {categories_label}.

Investigation findings across all categories:
{all_findings}

Original complaint: {complaint}

Generate a resolution following these rules:
1. The resolution must address ALL investigated categories ({categories_label}).
2. Reference established Downside Up procedures or protocols (e.g., "Per Downside Up Protocol DU-XXX...").
3. If any category is "environmental" or "monster", determine whether this requires escalation to a specialized team (Hawkins Environmental Response Unit or Creature Containment Division). Set ESCALATION to YES or NO.
4. Include a predicted effectiveness rating: HIGH, MEDIUM, or LOW based on the evidence strength and resolution fit.

Format your response EXACTLY as:

RESOLUTION:
[detailed resolution referencing Downside Up procedures]

ESCALATION: [YES or NO]

EFFECTIVENESS: [HIGH, MEDIUM, or LOW]"""

    response = llm.invoke([HumanMessage(content=resolution_prompt)])
    result = response.content.strip()

    # Parse effectiveness rating
    effectiveness = "medium"
    for line in result.split("\n"):
        if line.strip().upper().startswith("EFFECTIVENESS:"):
            rating = line.split(":", 1)[1].strip().lower()
            if rating in ("high", "medium", "low"):
                effectiveness = rating
            break

    # Parse escalation flag
    requires_escalation = False
    escalation_categories = {"environmental", "monster"}
    if escalation_categories & set(categories):
        for line in result.split("\n"):
            if line.strip().upper().startswith("ESCALATION:"):
                requires_escalation = "YES" in line.upper()
                break

    print(f"[RESOLUTION] Categories addressed: {categories_label}")
    print(f"[RESOLUTION] Effectiveness: {effectiveness}")
    if requires_escalation:
        print(f"[RESOLUTION] Escalation required")

    return {
        "resolution": result,
        "effectiveness_rating": effectiveness,
        "requires_escalation": requires_escalation,
        "workflow_path": ["resolution"],
        "status": "escalated_resolution" if requires_escalation else "resolved",
    }
