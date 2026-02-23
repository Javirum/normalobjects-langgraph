from langchain_core.messages import HumanMessage

from complaint_workflow.state import ComplaintState
from complaint_workflow.llm import llm


def validation_node(state: ComplaintState) -> ComplaintState:
    """Step 2: Validate - Check complaint meets category-specific criteria"""
    print("\n[VALIDATION] Validating complaint...")

    complaint = state["complaint"]
    category = state["category"]

    if category == "other":
        print("[VALIDATION] 'other' category -> auto-escalated for manual review")
        return {
            **state,
            "validation_status": "escalate",
            "validation_message": "Complaint categorized as 'other'. Escalated for manual review.",
            "workflow_path": state.get("workflow_path", []) + ["validation"],
            "status": "escalated",
        }

    validation_prompt = f"""You are validating a Downside Up complaint that was categorized as "{category}".

Apply the following validation rule for the "{category}" category:

- portal: The complaint is valid ONLY if it references a specific location or timing anomaly related to portals.
- monster: The complaint is valid ONLY if it describes specific creature behavior or interactions.
- psychic: The complaint is valid ONLY if it references specific ability limitations or malfunctions.
- environmental: The complaint is valid ONLY if it connects to electricity, weather, or observable physical phenomena.

Complaint: {complaint}

Does this complaint contain enough specific detail to satisfy the rule above?
Respond with EXACTLY one of these two words: VALID or REJECT
Then on a new line, provide a brief reason."""

    response = llm.invoke([HumanMessage(content=validation_prompt)])
    result = response.content.strip()
    first_line = result.split("\n")[0].strip().upper()
    reason = "\n".join(result.split("\n")[1:]).strip()

    if first_line == "VALID":
        validation_status = "valid"
        validation_message = reason or "Complaint meets category-specific criteria."
        print(f"[VALIDATION] VALID - {validation_message}")
    else:
        validation_status = "rejected"
        validation_message = reason or "Complaint lacks sufficient detail. Please provide more specifics."
        print(f"[VALIDATION] REJECTED - {validation_message}")

    return {
        **state,
        "validation_status": validation_status,
        "validation_message": validation_message,
        "workflow_path": state.get("workflow_path", []) + ["validation"],
        "status": "validated" if validation_status == "valid" else "rejected",
    }
