import logging
import sys

from dotenv import load_dotenv
load_dotenv()

from complaint_workflow import app, ComplaintState

logger = logging.getLogger("complaint_workflow")

NODE_LABELS = {
    "intake": "Intake",
    "validation": "Validation",
    "investigation": "Investigation",
    "investigation_blocked": "Investigation (blocked)",
    "resolution": "Resolution",
    "resolution_blocked": "Resolution (blocked)",
    "closure": "Closure",
    "closure_blocked": "Closure (blocked)",
}

STATUS_ICONS = {
    "closed": "[OK]",
    "resolved": "[OK]",
    "escalated": "[!!]",
    "escalated_resolution": "[!!]",
    "rejected": "[X]",
    "closure_blocked": "[X]",
    "investigation_blocked": "[X]",
    "resolution_blocked": "[X]",
}


def visualize_workflow_path(state: ComplaintState) -> str:
    """Build a formatted diagram of the workflow path taken and log each step.

    Returns the diagram as a string and logs each node transition at INFO level.
    """
    path = state.get("workflow_path", [])
    if not path:
        msg = "No workflow path recorded."
        logger.info(msg)
        return msg

    lines: list[str] = []
    lines.append("=" * 52)
    lines.append("  WORKFLOW PATH")
    lines.append("=" * 52)

    status_icon = STATUS_ICONS.get(state.get("status", ""), "[?]")

    for i, step in enumerate(path):
        label = NODE_LABELS.get(step, step)
        prefix = "  --> " if i == 0 else "      |"

        if i > 0:
            lines.append("      |")
            lines.append(f"      v")
            prefix = "  --> "

        detail = ""
        if step == "intake":
            detail = f'  category="{state.get("category", "")}"'
        elif step == "validation":
            detail = f'  status={state.get("validation_status", "")}'
        elif step == "investigation":
            has_findings = bool(state.get("investigation_findings"))
            detail = f"  findings={'yes' if has_findings else 'none'}"
        elif step == "resolution":
            detail = (
                f'  effectiveness={state.get("effectiveness_rating", "")}'
                f'  escalation={"yes" if state.get("requires_escalation") else "no"}'
            )
        elif step == "closure":
            detail = (
                f'  satisfied={"yes" if state.get("satisfaction_verified") else "no"}'
                f'  follow_up={"yes" if state.get("follow_up_required") else "no"}'
            )

        lines.append(f"{prefix} {label}{detail}")
        logger.info("Step %d: %s%s", i + 1, label, detail)

    lines.append("")
    lines.append(f"  Result: {status_icon} {state.get('status', 'unknown')}")
    if state.get("closed_at"):
        lines.append(f"  Closed at: {state['closed_at']}")
    lines.append("=" * 52)

    diagram = "\n".join(lines)
    logger.info("Final status: %s", state.get("status", "unknown"))
    return diagram


def run_complaint(text: str) -> ComplaintState:
    """Run a complaint through the full workflow and return the final state."""
    initial_state: ComplaintState = {
        "complaint": text,
        "context": [],
        "category": "",
        "resolution": "",
        "workflow_path": [],
        "status": "new",
        "validation_status": "",
        "validation_message": "",
        "investigation_findings": "",
        "effectiveness_rating": "",
        "requires_escalation": False,
        "closure_log": "",
        "satisfaction_verified": False,
        "follow_up_required": False,
        "closed_at": "",
    }
    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("Usage: python main.py \"<complaint text>\"")
        sys.exit(1)
    complaint_text = " ".join(sys.argv[1:])
    final_state = run_complaint(complaint_text)
    print("\n" + visualize_workflow_path(final_state))
    if final_state.get("closure_log"):
        print("\n" + final_state["closure_log"])
