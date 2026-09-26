"""Pydantic schemas for request/response validation"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr


# --- Auth ---
class LoginRequest(BaseModel):
    email: str
    password: str
    mfa_code: Optional[str] = None
    temp_token: Optional[str] = None


class MfaVerifyRequest(BaseModel):
    temp_token: str
    mfa_code: str


class LoginResponse(BaseModel):
    mfa_required: bool = False
    temp_token: Optional[str] = None
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional["UserOut"] = None
    officer_name: Optional[str] = None
    badge_number: Optional[str] = None
    role: Optional[str] = None
    mfa_type: Optional[str] = None
    message: Optional[str] = None
    demo_totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    department: str
    badge_number: str
    is_active: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "INVESTIGATOR"
    department: str = ""
    badge_number: str = ""


# --- Cases ---
class CaseCreate(BaseModel):
    title: str
    description: str = ""
    case_type: str = "GENERAL"
    priority: str = "MEDIUM"
    investigating_officer: str = ""
    incident_date: Optional[datetime] = None
    incident_location: Optional[str] = ""
    reporting_authority: Optional[str] = ""
    assigned_team: Optional[str] = "Special Investigation Unit"
    persons_involved: Optional[str] = ""
    jurisdiction: Optional[str] = "Delhi NCT Central"
    retention_category: Optional[str] = "STANDARD_5YR"
    confidentiality_level: Optional[str] = "CONFIDENTIAL"


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    case_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    investigating_officer: Optional[str] = None
    incident_date: Optional[datetime] = None
    incident_location: Optional[str] = None
    reporting_authority: Optional[str] = None
    assigned_team: Optional[str] = None
    persons_involved: Optional[str] = None
    jurisdiction: Optional[str] = None
    retention_category: Optional[str] = None
    confidentiality_level: Optional[str] = None
    legal_hold: Optional[bool] = None


class CaseOut(BaseModel):
    id: int
    case_number: str
    title: str
    description: str
    case_type: str
    status: str
    priority: str
    investigating_officer: str
    assigned_user_id: Optional[int] = None
    created_by: Optional[int] = None
    
    # Stage 1 metadata
    incident_date: Optional[datetime] = None
    incident_location: Optional[str] = ""
    reporting_authority: Optional[str] = ""
    assigned_team: Optional[str] = ""
    persons_involved: Optional[str] = ""
    jurisdiction: Optional[str] = ""
    retention_category: Optional[str] = "STANDARD_5YR"
    confidentiality_level: Optional[str] = "CONFIDENTIAL"

    # Auditor Freeze/Quarantine
    is_frozen: Optional[bool] = False
    quarantine_reason: Optional[str] = ""

    # Legal Prosecutor Court Approval
    is_court_ready: Optional[bool] = False
    court_docket_number: Optional[str] = ""

    # Stage 6 Closure & Legal Hold
    legal_hold: Optional[bool] = False
    closure_checklist_json: Optional[str] = "{}"
    closed_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    archived_at: Optional[datetime] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    evidence_count: int = 0

    class Config:
        from_attributes = True


# --- Evidence ---
class EvidenceOut(BaseModel):
    id: int
    evidence_id: str
    case_id: int
    case_number: Optional[str] = None
    original_filename: str
    stored_filename: Optional[str] = ""
    evidence_type: str
    file_type: Optional[str] = None
    mime_type: str
    file_size: int
    sha256_hash: str
    encrypted_path: Optional[str] = ""
    current_version: int
    status: Optional[str] = "REGISTERED"
    current_custodian: str
    classification: str
    ai_confidence: float
    integrity_status: str
    blockchain_status: str
    custody_count: int
    risk_score: float
    description: str
    uploaded_by: Optional[int] = None
    uploaded_by_name: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Stage 2 Minimum Evidence Record Metadata
    source: Optional[str] = ""
    collector: Optional[str] = ""
    collection_datetime: Optional[datetime] = None
    collection_location: Optional[str] = ""
    condition_at_intake: Optional[str] = "INTACT"
    storage_location: Optional[str] = "Digital Vault / Secure Repository"

    # Physical Storage Registry
    physical_location: Optional[str] = "Malkhana Bay A-Shelf 3"
    barcode_id: Optional[str] = ""
    physical_status: Optional[str] = "CHECKED_IN"
    physical_release_approved: Optional[bool] = False
    physical_release_to: Optional[str] = ""

    # Auditor Quarantine & Warrant
    is_frozen: Optional[bool] = False
    quarantine_reason: Optional[str] = ""
    is_unsealed_by_warrant: Optional[bool] = False
    warrant_number: Optional[str] = ""

    # Deletion Approval
    deletion_requested: Optional[bool] = False
    deletion_request_reason: Optional[str] = ""
    deletion_status: Optional[str] = "NONE"

    # Forensic & Custody states
    forensic_status: Optional[str] = "NOT_REQUIRED"
    custody_state: Optional[str] = "SECURE_VAULT"
    parent_evidence_id: Optional[int] = None
    is_child_report: Optional[bool] = False

    # Stage 3 Laboratory Testing (Forensic Specialist)
    lab_sample_id: Optional[str] = ""
    lab_test_requested: Optional[str] = ""
    lab_test_performed: Optional[str] = ""
    lab_qc_status: Optional[str] = "QC_PENDING"
    lab_seal_intact: Optional[bool] = True
    lab_findings: Optional[str] = ""
    lab_analyst: Optional[str] = ""

    # Stage 5 Court Presentation & Exhibits (Legal Prosecutor)
    court_exhibit_number: Optional[str] = ""
    court_receipt_number: Optional[str] = ""
    court_presentation_date: Optional[datetime] = None
    court_action: Optional[str] = "PENDING"
    court_disposition_notes: Optional[str] = ""
    court_order_ref: Optional[str] = ""

    # Stage 6 Authorized Destruction Certificate
    destruction_certificate_id: Optional[str] = ""
    destruction_timestamp: Optional[datetime] = None
    destruction_authority: Optional[str] = ""
    destruction_method: Optional[str] = ""
    is_destroyed: Optional[bool] = False

    class Config:
        from_attributes = True


# --- Workflow Requests ---
class DeletionRequest(BaseModel):
    reason: str


class DeletionReviewRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
    comments: Optional[str] = ""


class QuarantineRequest(BaseModel):
    reason: str
    freeze: bool = True


class WarrantUnsealRequest(BaseModel):
    warrant_number: str
    court_jurisdiction: str
    justification: str


class CustodianLocationRequest(BaseModel):
    physical_location: str
    notes: Optional[str] = ""


class CustodianCheckInOutRequest(BaseModel):
    action: str  # "CHECK_OUT" or "CHECK_IN"
    officer_name: str
    badge_number: str
    purpose: str


class PhysicalReleaseApprovalRequest(BaseModel):
    approved_recipient: str
    authorization_ref: str


class PrivilegeRequestCreate(BaseModel):
    target_user_email: str
    target_full_name: str
    requested_role: str
    justification: str


class PrivilegeRequestReview(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"


class PrivilegeRequestOut(BaseModel):
    id: int
    requested_by_email: str
    target_user_email: str
    target_full_name: str
    requested_role: str
    justification: str
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True



class EvidencePassport(BaseModel):
    evidence_id: str
    case_id: int
    case_number: str
    original_filename: str
    evidence_type: str
    document_type: Optional[str] = None
    mime_type: str
    file_size: int
    sha256_hash: str
    created_at: Optional[datetime] = None
    uploaded_at: Optional[datetime] = None
    current_version: int
    current_custodian: str
    uploaded_by: Optional[str] = None
    classification: str
    ai_confidence: float = 0
    integrity_status: str
    blockchain_status: str
    custody_count: int = 0
    qr_code: str = ""
    verification_url: Optional[str] = None


class VerifyResult(BaseModel):
    status: str  # VERIFIED, TAMPERED, UNKNOWN
    hash_match: bool
    stored_hash: str
    computed_hash: str
    blockchain_valid: bool
    details: str


# --- Versions ---
class VersionOut(BaseModel):
    id: int
    version_number: int
    filename: Optional[str] = ""
    sha256_hash: str
    file_size: int
    action: str
    reason: str
    change_reason: Optional[str] = ""
    actor_name: str
    uploaded_by: Optional[str] = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Custody ---
class CustodyEventOut(BaseModel):
    id: int
    event_id: Optional[str] = ""
    evidence_id: int
    actor_name: str
    actor_role: str
    previous_custodian: Optional[str] = ""
    new_custodian: Optional[str] = ""
    action: str
    reason: Optional[str] = "Custody Transfer"
    location: str
    evidence_condition: str
    integrity_state: Optional[str] = "VERIFIED"
    authorization: Optional[str] = "Standard Investigation Procedure"
    digital_signature: Optional[str] = ""
    notes: str
    sha256_hash: str
    previous_event_hash: Optional[str] = ""
    current_event_hash: Optional[str] = ""
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustodyTransferRequest(BaseModel):
    recipient_user_id: Optional[int] = None
    target_user_id: Optional[int] = None
    location: str = "Digital Evidence Lab"
    condition: str = "INTACT"
    reason: Optional[str] = "Forensic Examination"
    authorization: Optional[str] = "Investigating Officer Transfer Order"
    notes: str = ""


# --- End-to-End Workflow Requests ---
class EvidenceStateTransitionRequest(BaseModel):
    new_state: str  # REGISTERED, SECURED, ASSIGNED, IN_EXAMINATION, ANALYSIS_COMPLETE, RETURNED, LEGAL_REVIEW, COURT_SUBMITTED, COURT_DISPOSITION, CASE_CLOSED, ARCHIVED, RETENTION_EXPIRED, AUTHORIZED_DESTRUCTION
    reason: str
    notes: Optional[str] = ""


class LabAnalysisRequest(BaseModel):
    sample_id: str
    test_requested: str
    test_performed: str
    qc_status: str = "QC_PASSED"  # QC_PASSED, QC_FAILED, QC_PENDING
    seal_intact: bool = True
    findings: str
    analyst: Optional[str] = None


class CourtActionRequest(BaseModel):
    exhibit_number: str
    court_receipt_number: str
    court_action: str  # ADMITTED, REJECTED, DEFERRED, PENDING
    presentation_notes: Optional[str] = ""
    court_order_ref: Optional[str] = ""


class AuthorizedDestructionRequest(BaseModel):
    retention_verified: bool = True
    legal_hold_verified: bool = True
    destruction_method: str = "NIST SP 800-88 Cryptographic Shredding"
    reason: str = "Statutory Retention Period Expired"


class LegalHoldRequest(BaseModel):
    legal_hold: bool
    reason: str


class CaseCloseRequest(BaseModel):
    closure_reason: str = "Investigation & Legal Proceedings Complete"
    notes: Optional[str] = ""


# --- AI ---
class AIAnalysisOut(BaseModel):
    id: int
    evidence_id: int
    document_type: str
    confidence: float
    summary: str
    entities_json: str
    risk_score: float
    risk_level: str
    anomalies_json: str
    key_persons_count: int
    locations_count: int
    dates_count: int
    case_references_count: int
    classification_method: str
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Blockchain ---
class BlockOut(BaseModel):
    id: int
    block_index: int
    timestamp: Optional[datetime] = None
    previous_hash: str
    current_hash: str
    evidence_id: str
    document_hash: str
    action: str
    actor: str
    actor_role: str
    metadata_json: str

    class Config:
        from_attributes = True


class ChainVerifyResult(BaseModel):
    valid: bool
    blocks_checked: int
    message: str
    errors: List[dict] = []


# --- Audit ---
class AuditLogOut(BaseModel):
    id: int
    timestamp: Optional[datetime] = None
    user_id: Optional[int] = None
    user_email: str
    role: str
    action: str
    resource_type: str
    resource_id: str
    ip_address: str
    status: str
    details: str

    class Config:
        from_attributes = True


# --- Graph ---
class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    data: dict = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    type: str


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# --- Dashboard ---
class DashboardStats(BaseModel):
    total_cases: int = 0
    total_evidence: int = 0
    verified_evidence: int = 0
    pending_review: int = 0
    custody_transfers: int = 0
    ai_alerts: int = 0
    blockchain_blocks: int = 0
    recent_activity: List[dict] = []
    evidence_by_category: List[dict] = []
    case_status_distribution: List[dict] = []
    evidence_over_time: List[dict] = []
    risk_distribution: List[dict] = []
    high_risk_alerts: List[dict] = []


# --- Generic ---
class ErrorResponse(BaseModel):
    success: bool = False
    error: dict


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str = ""


# Update forward reference
TokenResponse.model_rebuild()
