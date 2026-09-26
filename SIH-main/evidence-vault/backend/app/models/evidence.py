"""Evidence, Version, Custody, and Relationship models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from app.database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String(50), unique=True, index=True, nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), default="")
    evidence_type = Column(String(100), default="DOCUMENT")
    file_type = Column(String(50), default="DOCUMENT")
    mime_type = Column(String(100), default="")
    file_size = Column(Integer, default=0)
    sha256_hash = Column(String(64), nullable=False)
    encrypted_path = Column(String(1000), nullable=False)
    current_version = Column(Integer, default=1)
    status = Column(String(50), default="REGISTERED")
    current_custodian = Column(String(255), default="")
    custodian_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    classification = Column(String(100), default="UNCLASSIFIED")
    ai_confidence = Column(Float, default=0.0)
    integrity_status = Column(String(50), default="VERIFIED")
    blockchain_status = Column(String(50), default="REGISTERED")
    custody_count = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)
    description = Column(Text, default="")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Stage 2 — Evidence Intake Minimum Record Metadata
    source = Column(String(500), default="")
    collector = Column(String(255), default="")
    collection_datetime = Column(DateTime, nullable=True)
    collection_location = Column(String(500), default="")
    condition_at_intake = Column(String(100), default="INTACT")
    storage_location = Column(String(255), default="Digital Vault / Secure Repository")

    # Malkhana / Physical Storage Registry
    physical_location = Column(String(255), default="Malkhana Bay A-Shelf 3")
    barcode_id = Column(String(100), default="")
    physical_status = Column(String(50), default="CHECKED_IN")

    # Auditor Compliance & Case Quarantine / Warrant Unsealing
    is_frozen = Column(Boolean, default=False)
    quarantine_reason = Column(Text, default="")
    is_unsealed_by_warrant = Column(Boolean, default=False)
    warrant_number = Column(String(100), default="")

    # Deletion Approval Workflow (IO requests, Auditor approves)
    deletion_requested = Column(Boolean, default=False)
    deletion_request_reason = Column(Text, default="")
    deletion_status = Column(String(50), default="NONE")  # NONE, REQUESTED, APPROVED, REJECTED
    deletion_request_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Forensic & Custody Workflow
    forensic_status = Column(String(50), default="NOT_REQUIRED")  # NOT_REQUIRED, PENDING_ANALYSIS, IN_ANALYSIS, ANALYSIS_COMPLETE
    custody_state = Column(String(50), default="SECURE_VAULT")  # SECURE_VAULT, IN_TRANSIT_LAB, IN_FORENSIC_LAB, IN_MALKHANA, COURT_DOCKETED
    physical_release_approved = Column(Boolean, default=False)
    physical_release_to = Column(String(255), default="")

    # Forensic Child Reports
    parent_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    is_child_report = Column(Boolean, default=False)

    # Stage 3 — Laboratory Analysis Responsibilities (Forensic Specialist)
    lab_sample_id = Column(String(100), default="")
    lab_test_requested = Column(String(255), default="")
    lab_test_performed = Column(String(255), default="")
    lab_qc_status = Column(String(50), default="QC_PENDING")  # QC_PENDING, QC_PASSED, QC_FAILED
    lab_seal_intact = Column(Boolean, default=True)
    lab_findings = Column(Text, default="")
    lab_analyst = Column(String(255), default="")

    # Stage 5 — Court Presentation & Exhibit Management (Legal Prosecutor)
    court_exhibit_number = Column(String(100), default="")
    court_receipt_number = Column(String(100), default="")
    court_presentation_date = Column(DateTime, nullable=True)
    court_action = Column(String(50), default="PENDING")  # ADMITTED, REJECTED, DEFERRED, PENDING
    court_disposition_notes = Column(Text, default="")
    court_order_ref = Column(String(100), default="")

    # Stage 6 — Authorized Destruction Certificate
    destruction_certificate_id = Column(String(100), default="")
    destruction_timestamp = Column(DateTime, nullable=True)
    destruction_authority = Column(String(255), default="")
    destruction_method = Column(String(255), default="")
    is_destroyed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvidenceVersion(Base):
    __tablename__ = "evidence_versions"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    filename = Column(String(500), default="")
    sha256_hash = Column(String(64), nullable=False)
    encrypted_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, default=0)
    action = Column(String(100), default="UPLOADED")
    reason = Column(Text, default="")
    change_reason = Column(Text, default="")
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(255), default="")
    uploaded_by = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), default="")  # e.g. COC-000123
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(255), nullable=False)
    actor_role = Column(String(50), nullable=False)
    previous_custodian = Column(String(255), default="")
    new_custodian = Column(String(255), default="")
    action = Column(String(100), nullable=False)
    reason = Column(String(255), default="Custody Transfer")
    location = Column(String(255), default="Digital Evidence Lab")
    evidence_condition = Column(String(100), default="INTACT")
    integrity_state = Column(String(50), default="VERIFIED")
    authorization = Column(String(255), default="Standard Investigation Procedure")
    digital_signature = Column(String(255), default="")
    notes = Column(Text, default="")
    sha256_hash = Column(String(64), default="")
    previous_event_hash = Column(String(64), default="")
    current_event_hash = Column(String(64), default="")
    timestamp = Column(DateTime, default=datetime.utcnow)


class EvidenceRelationship(Base):
    __tablename__ = "evidence_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    target_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    target_case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    relationship_type = Column(String(50), nullable=False)  # BELONGS_TO, REFERENCES, etc.
    label = Column(String(255), default="")
    node_type = Column(String(50), default="EVIDENCE")  # CASE, EVIDENCE, PERSON, LOCATION, etc.
    node_label = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
