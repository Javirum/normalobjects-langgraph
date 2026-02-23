import logging
import sys

from dotenv import load_dotenv
load_dotenv()

from complaint_workflow import app, ComplaintState

logger = logging.getLogger("complaint_workflow")

NODE_LABELS = {
    "intake": "Intake",
    "validation": "Validation",
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

    # Separate investigation steps (parallel) from sequential steps
    investigation_steps = [s for s in path if s.startswith("investigation:")]
    sequential_steps = [s for s in path if not s.startswith("investigation:")]

    # Build ordered display: sequential steps with investigation fork inserted
    display_order: list[str] = []
    investigation_inserted = False
    for step in path:
        if step.startswith("investigation:") and not investigation_inserted:
            display_order.append("__investigations__")
            investigation_inserted = True
        elif not step.startswith("investigation:"):
            display_order.append(step)

    step_idx = 0
    for entry in display_order:
        if entry == "__investigations__":
            # Render parallel fork
            if step_idx > 0:
                lines.append("      |")
                lines.append("      v")
            categories = [s.split(":", 1)[1] for s in investigation_steps]
            lines.append(f"  --> Investigation (parallel: {', '.join(categories)})")
            findings = state.get("investigation_findings", {})
            for cat in categories:
                has = "yes" if cat in findings and findings[cat] else "none"
                lines.append(f"        [{cat}]  findings={has}")
            logger.info(
                "Step %d: Investigation (parallel: %s)",
                step_idx + 1,
                ", ".join(categories),
            )
            step_idx += 1
        else:
            label = NODE_LABELS.get(entry, entry)
            if step_idx > 0:
                lines.append("      |")
                lines.append("      v")

            detail = ""
            if entry == "intake":
                detail = f'  categories={state.get("categories", [])}'
            elif entry == "validation":
                results = state.get("validation_results", {})
                summaries = [f"{c}={r['status']}" for c, r in results.items()]
                detail = f"  [{', '.join(summaries)}]"
            elif entry == "resolution":
                detail = (
                    f'  effectiveness={state.get("effectiveness_rating", "")}'
                    f'  escalation={"yes" if state.get("requires_escalation") else "no"}'
                )
            elif entry == "closure":
                detail = (
                    f'  satisfied={"yes" if state.get("satisfaction_verified") else "no"}'
                    f'  follow_up={"yes" if state.get("follow_up_required") else "no"}'
                )

            lines.append(f"  --> {label}{detail}")
            logger.info("Step %d: %s%s", step_idx + 1, label, detail)
            step_idx += 1

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
        "categories": [],
        "resolution": "",
        "workflow_path": [],
        "status": "new",
        "validation_results": {},
        "investigation_findings": {},
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
