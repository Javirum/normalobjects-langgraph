from typing import Literal

from langgraph.graph import StateGraph, START, END

from complaint_workflow.state import ComplaintState
from complaint_workflow.nodes import (
    intake_node,
    validation_node,
    investigation_node,
    resolution_node,
    closure_node,
)


def route_after_validation(state: ComplaintState) -> Literal["investigate", "close"]:
    """Route based on validation result: valid complaints get investigated,
    rejected/escalated ones skip straight to closure."""
    if state.get("validation_status") == "valid":
        return "investigate"
    return "close"


workflow = StateGraph(ComplaintState)

workflow.add_node("intake", intake_node)
workflow.add_node("validate", validation_node)
workflow.add_node("investigate", investigation_node)
workflow.add_node("resolve", resolution_node)
workflow.add_node("close", closure_node)

workflow.add_edge(START, "intake")
workflow.add_edge("intake", "validate")
workflow.add_conditional_edges("validate", route_after_validation)
workflow.add_edge("investigate", "resolve")
workflow.add_edge("resolve", "close")
workflow.add_edge("close", END)

app = workflow.compile()
