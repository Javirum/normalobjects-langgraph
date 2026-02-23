from langchain_core.messages import HumanMessage

from complaint_workflow.state import ComplaintState
from complaint_workflow.llm import llm


def investigation_node(state: ComplaintState) -> ComplaintState:
    """Step 3: Investigate - Gather evidence based on category-specific protocols"""
    print("\n[INVESTIGATION] Starting investigation...")

    if state.get("validation_status") != "valid":
        print("[INVESTIGATION] Cannot proceed - complaint has not passed validation")
        return {
            **state,
            "investigation_findings": "",
            "workflow_path": state.get("workflow_path", []) + ["investigation_blocked"],
            "status": "investigation_blocked",
        }

    complaint = state["complaint"]
    category = state["category"]

    investigation_prompt = f"""You are investigating a validated Downside Up complaint categorized as "{category}".

Follow the investigation protocol for "{category}":

- portal: Investigate temporal patterns (when does the portal appear/disappear?), location consistency (does it always open in the same place?), and environmental factors (what conditions surround portal activity?).
- monster: Gather behavioral data (what is the creature doing?), interaction patterns (how does it respond to people/stimuli?), and environmental triggers (what conditions provoke or calm it?).
- psychic: Document ability specifications (what powers are affected?), tested limitations (what specifically fails or malfunctions?), and contextual factors (when/where do the issues occur?).
- environmental: Analyze power line activity (electrical anomalies?), atmospheric conditions (weather patterns, temperature shifts?), and anomaly correlation (how do phenomena relate to each other?).

Complaint: {complaint}

Produce a structured investigation report with documented evidence and findings. Format it as:

EVIDENCE GATHERED:
- [list key evidence points]

ANALYSIS:
[brief analysis of the evidence]

CONCLUSION:
[summary finding that can inform resolution]"""

    response = llm.invoke([HumanMessage(content=investigation_prompt)])
    findings = response.content.strip()

    print("[INVESTIGATION] Investigation complete")

    return {
        **state,
        "investigation_findings": findings,
        "workflow_path": state.get("workflow_path", []) + ["investigation"],
        "status": "investigated",
    }
