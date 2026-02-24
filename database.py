from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///complaints.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String, primary_key=True)
    complaint = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="submitted")
    categories = Column(Text, default="[]")
    findings = Column(Text, default="{}")
    resolution = Column(Text, default="")
    closure_log = Column(Text, default="")
    state_json = Column(Text, default="{}")
    error = Column(Text, default="")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_complaint(text: str) -> dict:
    db = SessionLocal()
    try:
        complaint = Complaint(
            id=str(uuid.uuid4()),
            complaint=text,
            status="submitted",
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        return {"id": complaint.id, "status": complaint.status}
    finally:
        db.close()


def get_complaint(complaint_id: str) -> dict | None:
    db = SessionLocal()
    try:
        row = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not row:
            return None
        return _row_to_dict(row)
    finally:
        db.close()


def list_complaints() -> list[dict]:
    db = SessionLocal()
    try:
        rows = db.query(Complaint).order_by(Complaint.created_at.desc()).all()
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


def mark_processing(complaint_id: str):
    db = SessionLocal()
    try:
        row = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if row:
            row.status = "processing"
            row.updated_at = _now()
            db.commit()
    finally:
        db.close()


def save_workflow_result(complaint_id: str, state: dict):
    db = SessionLocal()
    try:
        row = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not row:
            return
        row.status = "closed"
        row.categories = json.dumps(state.get("categories", []))
        row.findings = json.dumps(state.get("investigation_findings", {}))
        row.resolution = state.get("resolution", "")
        row.closure_log = state.get("closure_log", "")
        # Serialize the full state — skip non-serializable Document objects
        serializable = {k: v for k, v in state.items() if k != "context"}
        row.state_json = json.dumps(serializable, default=str)
        row.updated_at = _now()
        db.commit()
    finally:
        db.close()


def mark_error(complaint_id: str, error_msg: str):
    db = SessionLocal()
    try:
        row = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if row:
            row.status = "error"
            row.error = error_msg
            row.updated_at = _now()
            db.commit()
    finally:
        db.close()


def _row_to_dict(row: Complaint) -> dict:
    return {
        "id": row.id,
        "complaint": row.complaint,
        "status": row.status,
        "categories": json.loads(row.categories or "[]"),
        "findings": json.loads(row.findings or "{}"),
        "resolution": row.resolution or "",
        "closure_log": row.closure_log or "",
        "state_json": json.loads(row.state_json or "{}"),
        "error": row.error or "",
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
