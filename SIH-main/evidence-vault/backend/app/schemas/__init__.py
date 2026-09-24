"""Pydantic schemas for request/response validation"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field


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
    rank_level: int = 3
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
    rank_level: Optional[int] = Field(None, ge=1, le=6)
    department: str = ""
    badge_number: str = ""


# --- Cases ---
class CaseCreate(BaseModel):
    title: str
    description: str = ""
    case_type: str = "GENERAL"
    priority: str = "MEDIUM"
    investigating_officer: str = ""


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    case_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    investigating_officer: Optional[str] = None


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
    evidence_id: int
    actor_name: str
    actor_role: str
    action: str
    location: str
    evidence_condition: str
    notes: str
    sha256_hash: str
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustodyTransferRequest(BaseModel):
    recipient_user_id: Optional[int] = None
    target_user_id: Optional[int] = None
    location: str = "Digital Evidence Lab"
    condition: str = "INTACT"
    notes: str = ""


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
