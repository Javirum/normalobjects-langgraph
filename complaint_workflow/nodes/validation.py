from langchain_core.messages import HumanMessage

from complaint_workflow.state import ComplaintState
from complaint_workflow.llm import llm


def validation_node(state: ComplaintState) -> dict:
    """Step 2: Validate - Check complaint meets criteria for each identified category"""
    print("\n[VALIDATION] Validating complaint...")

    complaint = state["complaint"]
    categories = state["categories"]
    validation_results: dict[str, dict] = {}

    for category in categories:
        if category == "other":
            print(f"[VALIDATION] '{category}' -> auto-escalated for manual review")
            validation_results[category] = {
                "status": "escalate",
                "message": "Complaint categorized as 'other'. Escalated for manual review.",
            }
            continue

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
            status = "valid"
            message = reason or "Complaint meets category-specific criteria."
            print(f"[VALIDATION] {category}: VALID - {message}")
        else:
            status = "rejected"
            message = reason or "Complaint lacks sufficient detail."
            print(f"[VALIDATION] {category}: REJECTED - {message}")

        validation_results[category] = {"status": status, "message": message}

    has_valid = any(r["status"] == "valid" for r in validation_results.values())
    all_escalated = all(r["status"] == "escalate" for r in validation_results.values())

    if has_valid:
        overall_status = "validated"
    elif all_escalated:
        overall_status = "escalated"
    else:
        overall_status = "rejected"

    return {
        "validation_results": validation_results,
        "workflow_path": ["validation"],
        "status": overall_status,
    }
