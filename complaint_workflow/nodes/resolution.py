from langchain_core.messages import HumanMessage

from complaint_workflow.state import ComplaintState
from complaint_workflow.llm import llm


def resolution_node(state: ComplaintState) -> ComplaintState:
    """Step 4: Resolution - Propose a resolution based on investigation findings"""
    print("\n[RESOLUTION] Generating resolution...")

    if not state.get("investigation_findings"):
        print("[RESOLUTION] Cannot proceed - no documented investigation results")
        return {
            **state,
            "resolution": "",
            "effectiveness_rating": "",
            "requires_escalation": False,
            "workflow_path": state.get("workflow_path", []) + ["resolution_blocked"],
            "status": "resolution_blocked",
        }

    complaint = state["complaint"]
    category = state["category"]
    findings = state["investigation_findings"]

    resolution_prompt = f"""You are resolving a Downside Up complaint categorized as "{category}".

Investigation findings:
{findings}

Original complaint: {complaint}

Generate a resolution following these rules:
1. The resolution must be specific to the "{category}" complaint type.
2. Reference established Downside Up procedures or protocols (e.g., "Per Downside Up Protocol DU-XXX...").
3. If the category is "environmental" or "monster", determine whether this requires escalation to a specialized team (Hawkins Environmental Response Unit or Creature Containment Division). Set ESCALATION to YES or NO.
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
    if category in ("environmental", "monster"):
        for line in result.split("\n"):
            if line.strip().upper().startswith("ESCALATION:"):
                requires_escalation = "YES" in line.upper()
                break

    resolution_text = result

    print(f"[RESOLUTION] Effectiveness: {effectiveness}")
    if requires_escalation:
        print(f"[RESOLUTION] Escalation required for {category} complaint")

    return {
        **state,
        "resolution": resolution_text,
        "effectiveness_rating": effectiveness,
        "requires_escalation": requires_escalation,
        "workflow_path": state.get("workflow_path", []) + ["resolution"],
        "status": "escalated_resolution" if requires_escalation else "resolved",
    }
