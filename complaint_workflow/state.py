from typing import TypedDict, List
from langchain_core.documents import Document


class ComplaintState(TypedDict):
    complaint: str
    context: List[Document]
    category: str
    resolution: str
    workflow_path: List[str]
    status: str
    validation_status: str
    validation_message: str
    investigation_findings: str
    effectiveness_rating: str
    requires_escalation: bool
    closure_log: str
    satisfaction_verified: bool
    follow_up_required: bool
    closed_at: str
