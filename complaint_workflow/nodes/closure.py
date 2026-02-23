from datetime import datetime

from langchain_core.messages import HumanMessage

from complaint_workflow.state import ComplaintState
from complaint_workflow.llm import llm


def closure_node(state: ComplaintState) -> dict:
    """Step 5: Closure - Verify resolution, log outcome, and close the complaint"""
    print("\n[CLOSURE] Processing closure...")

    workflow_path = state.get("workflow_path", [])

    # Check required sequential steps and at least one investigation
    required_steps = ["intake", "validation", "resolution"]
    has_all_steps = all(step in workflow_path for step in required_steps)
    has_investigation = any(step.startswith("investigation:") for step in workflow_path)

    if not (has_all_steps and has_investigation):
        missing = [s for s in required_steps if s not in workflow_path]
        if not has_investigation:
            missing.append("investigation")
        print(f"[CLOSURE] Cannot close - missing steps: {missing}")
        return {
            "closure_log": "",
            "satisfaction_verified": False,
            "follow_up_required": False,
            "closed_at": "",
            "workflow_path": ["closure_blocked"],
            "status": "closure_blocked",
        }

    if not state.get("resolution"):
        print("[CLOSURE] Cannot close - no resolution was applied")
        return {
            "closure_log": "",
            "satisfaction_verified": False,
            "follow_up_required": False,
            "closed_at": "",
            "workflow_path": ["closure_blocked"],
            "status": "closure_blocked",
        }

    complaint = state["complaint"]
    categories = state.get("categories", [])
    categories_label = ", ".join(categories)
    resolution = state["resolution"]
    effectiveness = state.get("effectiveness_rating", "medium")

    satisfaction_prompt = f"""You are a Downside Up closure agent verifying customer satisfaction.

Original complaint: {complaint}
Categories: {categories_label}
Resolution applied: {resolution}

Based on the resolution provided, assess whether this resolution adequately addresses the customer's complaint.
Respond with EXACTLY one word: SATISFIED or UNSATISFIED
Then on a new line, provide a brief explanation."""

    response = llm.invoke([HumanMessage(content=satisfaction_prompt)])
    result = response.content.strip()
    first_line = result.split("\n")[0].strip().upper()
    satisfaction_reason = "\n".join(result.split("\n")[1:]).strip()

    satisfied = first_line == "SATISFIED"
    follow_up_required = effectiveness == "low"

    timestamp = datetime.now().isoformat()

    # List which categories were investigated
    investigated = [
        step.split(":", 1)[1]
        for step in workflow_path
        if step.startswith("investigation:")
    ]

    closure_log = (
        f"=== COMPLAINT CLOSURE LOG ===\n"
        f"Timestamp: {timestamp}\n"
        f"Categories: {categories_label}\n"
        f"Investigated: {', '.join(investigated)} (parallel)\n"
        f"Resolution: {resolution}\n"
        f"Outcome: {'Satisfied' if satisfied else 'Unsatisfied'}\n"
        f"Satisfaction Detail: {satisfaction_reason}\n"
        f"Effectiveness Rating: {effectiveness}\n"
        f"Follow-up Required: {'Yes - 30-day checkpoint scheduled' if follow_up_required else 'No'}\n"
        f"Workflow Path: {' -> '.join(workflow_path + ['closure'])}\n"
        f"=============================="
    )

    print(f"[CLOSURE] Satisfaction: {'SATISFIED' if satisfied else 'UNSATISFIED'}")
    if follow_up_required:
        print("[CLOSURE] Low effectiveness - 30-day follow-up checkpoint scheduled")
    print(f"[CLOSURE] Complaint closed at {timestamp}")

    return {
        "closure_log": closure_log,
        "satisfaction_verified": satisfied,
        "follow_up_required": follow_up_required,
        "closed_at": timestamp,
        "workflow_path": ["closure"],
        "status": "closed",
    }
