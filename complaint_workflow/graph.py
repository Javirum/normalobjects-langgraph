from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from complaint_workflow.state import ComplaintState
from complaint_workflow.nodes import (
    intake_node,
    validation_node,
    investigate_category_node,
    resolution_node,
    closure_node,
)


def fan_out_investigations(state: ComplaintState):
    """Fan out to parallel investigations for each valid category.

    Returns Send objects for parallel execution, or routes to 'close'
    if no categories passed validation.
    """
    validation_results = state.get("validation_results", {})
    valid_categories = [
        cat
        for cat, result in validation_results.items()
        if result["status"] == "valid"
    ]

    if not valid_categories:
        return "close"

    return [
        Send(
            "investigate_category",
            {"complaint": state["complaint"], "category": cat},
        )
        for cat in valid_categories
    ]


def build_workflow() -> StateGraph:
    """Build the workflow StateGraph (not yet compiled)."""
    workflow = StateGraph(ComplaintState)

    workflow.add_node("intake", intake_node)
    workflow.add_node("validate", validation_node)
    workflow.add_node("investigate_category", investigate_category_node)
    workflow.add_node("resolve", resolution_node)
    workflow.add_node("close", closure_node)

    workflow.add_edge(START, "intake")
    workflow.add_edge("intake", "validate")
    workflow.add_conditional_edges(
        "validate", fan_out_investigations, ["investigate_category", "close"]
    )
    workflow.add_edge("investigate_category", "resolve")
    workflow.add_edge("resolve", "close")
    workflow.add_edge("close", END)

    return workflow


def compile_graph(checkpointer=None):
    """Compile the workflow with an optional checkpointer."""
    return build_workflow().compile(checkpointer=checkpointer)


app = compile_graph()
