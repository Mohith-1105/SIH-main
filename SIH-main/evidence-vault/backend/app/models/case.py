from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    case_type = Column(String(100), default="GENERAL")
    status = Column(String(50), default="OPEN")
    priority = Column(String(20), default="MEDIUM")
    investigating_officer = Column(String(255), default="")
    assigned_user_id = Column(Integer, nullable=True)
    created_by = Column(Integer, nullable=True)
    
    # Stage 1 — Case Creation Required Metadata
    incident_date = Column(DateTime, nullable=True)
    incident_location = Column(String(500), default="")
    reporting_authority = Column(String(255), default="")
    assigned_team = Column(String(255), default="Special Investigation Unit")
    persons_involved = Column(Text, default="")
    jurisdiction = Column(String(255), default="Delhi NCT Central")
    retention_category = Column(String(100), default="STANDARD_5YR")
    confidentiality_level = Column(String(100), default="CONFIDENTIAL")

    # Auditor Freeze/Quarantine
    is_frozen = Column(Boolean, default=False)
    quarantine_reason = Column(Text, default="")

    # Legal Prosecutor Court Approval & Dockets
    is_court_ready = Column(Boolean, default=False)
    court_docket_number = Column(String(100), default="")

    # Stage 6 — Closure, Archival & Legal Hold
    legal_hold = Column(Boolean, default=False)
    closure_checklist_json = Column(Text, default="{}")
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(Integer, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

