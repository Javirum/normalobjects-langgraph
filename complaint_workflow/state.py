import operator
from typing import Annotated, TypedDict, List

from langchain_core.documents import Document


def merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


class ComplaintState(TypedDict):
    complaint: str
    context: List[Document]
    categories: list[str]
    resolution: str
    workflow_path: Annotated[list[str], operator.add]
    status: str
    validation_results: dict  # {category: {status, message}}
    investigation_findings: Annotated[dict, merge_dicts]  # {category: findings}
    effectiveness_rating: str
    requires_escalation: bool
    closure_log: str
    satisfaction_verified: bool
    follow_up_required: bool
    closed_at: str


class CategoryInvestigationState(TypedDict):
    """Minimal state sent to each parallel investigation via Send."""
    complaint: str
    category: str
