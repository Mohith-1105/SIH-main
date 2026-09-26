"""Security utilities: JWT, password hashing, encryption, RBAC"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.database import get_db
from app.models.user import User
from sqlalchemy.orm import Session

# JWT
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# --- File Encryption (canonical implementation in encryption.py) ---
def encrypt_file(data: bytes) -> bytes:
    from app.security.encryption import encrypt_file as _encrypt
    return _encrypt(data)


def decrypt_file(data: bytes) -> bytes:
    from app.security.encryption import decrypt_file as _decrypt
    return _decrypt(data)


# --- SHA-256 Hashing ---
def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- Password ---
def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode('utf-8'), _bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# --- JWT ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# --- Current User Dependency ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# --- Role Normalization & Canonical RBAC Mapping ---
ROLE_ALIASES = {
    "ADMIN": "ADMIN",
    "SYSTEM_ADMIN": "ADMIN",
    "INVESTIGATOR": "INVESTIGATOR",
    "IO": "INVESTIGATOR",
    "DETECTIVE": "INVESTIGATOR",
    "FORENSIC_OFFICER": "FORENSIC_OFFICER",
    "FORENSIC_SPECIALIST": "FORENSIC_OFFICER",
    "LAB_ANALYST": "FORENSIC_OFFICER",
    "LEGAL_OFFICER": "LEGAL_OFFICER",
    "PROSECUTOR": "LEGAL_OFFICER",
    "COURT_OFFICIAL": "LEGAL_OFFICER",
    "AUDITOR": "AUDITOR",
    "COMPLIANCE_AUDITOR": "AUDITOR",
    "CUSTODIAN": "CUSTODIAN",
    "MALKHANA_CUSTODIAN": "CUSTODIAN",
}


def normalize_role(role: str) -> str:
    if not role:
        return "INVESTIGATOR"
    return ROLE_ALIASES.get(role.upper(), role.upper())


# --- Enterprise 6-Role Permissions Matrix ---
ROLE_PERMISSIONS = {
    "ADMIN": {
        "users.read", "users.write",
        "system.health", "system.backup", "system.storage", "system.mfa_policy",
        "privilege.approve",
        "auth.audit.read",  # Login/access logs only; ZERO evidence content or case investigation access
    },
    "INVESTIGATOR": {
        "cases.read", "cases.write",
        "evidence.upload", "evidence.read", "evidence.transfer",
        "evidence.request_deletion",
        "blockchain.read",
        "reports.bsa_receipt",
        "ai.analyze",
        "demo.tamper",
    },
    "FORENSIC_OFFICER": {
        "cases.read",
        "evidence.read",
        "evidence.verify",
        "evidence.upload_child_report",
        "evidence.version",
        "evidence.transfer_return",
        "blockchain.read",
        "ai.analyze",
        "reports.forensic",
    },
    "LEGAL_OFFICER": {
        "cases.read",
        "evidence.read",
        "evidence.watermarked_view",
        "evidence.court_export",
        "cases.approve_court_ready",
        "blockchain.read",
        "reports.case_dossier",
    },
    "AUDITOR": {
        "cases.read",
        "evidence.read",  # Metadata & hash only
        "audit.read",  # Global immutable audit logs
        "cases.quarantine",
        "evidence.quarantine",
        "evidence.approve_deletion",
        "evidence.unseal_warrant",
        "blockchain.read", "blockchain.verify",
        "compliance.scorecard",
        "reports.compliance",
    },
    "CUSTODIAN": {
        "cases.read",
        "evidence.read",  # Physical profile only (barcode, shelf, status)
        "malkhana.read",
        "malkhana.update_location",
        "malkhana.check_in_out",
        "malkhana.approve_physical_release",
        "reports.physical_inventory",
    },
}


def check_permission(user: User, permission: str):
    role = normalize_role(user.role)
    perms = ROLE_PERMISSIONS.get(role, set())
    if permission not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user.role}' lacks permission '{permission}'"
        )


def has_permission(user: User, permission: str) -> bool:
    role = normalize_role(user.role)
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(permission: str):
    """Dependency factory for RBAC."""
    def _checker(user: User = Depends(get_current_user)):
        check_permission(user, permission)
        return user
    return _checker


def require_any_permission(*permissions: str):
    def _checker(user: User = Depends(get_current_user)):
        role = normalize_role(user.role)
        perms = ROLE_PERMISSIONS.get(role, set())
        if not any(p in perms for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' lacks required permissions",
            )
        return user
    return _checker


def visible_case_ids(user: User, db: Session):
    """
    ABAC filter:
    - INVESTIGATOR: Only cases assigned to them or created by them.
    - FORENSIC_OFFICER, LEGAL_OFFICER, AUDITOR, CUSTODIAN: All cases relevant to their respective workflows.
    - ADMIN: No case narrative access.
    """
    from app.models.case import Case
    role = normalize_role(user.role)
    if role == "ADMIN":
        return []  # Admin has zero case investigation data access
    if role in {"AUDITOR", "LEGAL_OFFICER", "FORENSIC_OFFICER", "CUSTODIAN"}:
        return None
    rows = db.query(Case.id).filter(
        (Case.assigned_user_id == user.id) | (Case.created_by == user.id)
    ).all()
    return [r[0] for r in rows]


def ensure_case_access(user: User, case, db: Session):
    role = normalize_role(user.role)
    if role == "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Separation of Duties: System Administrators are restricted from viewing case narratives or investigation details."
        )
    ids = visible_case_ids(user, db)
    if ids is not None and case.id not in ids:
        raise HTTPException(status_code=403, detail="ABAC Policy: You are not authorized to access this case file.")


def ensure_evidence_access(user: User, evidence, db: Session):
    """ABAC check for general evidence metadata access."""
    role = normalize_role(user.role)
    if role == "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Separation of Duties: System Administrators have zero access to evidence items, hashes, or case records."
        )
    if role == "INVESTIGATOR":
        from app.models.case import Case
        case = db.query(Case).filter(Case.id == evidence.case_id).first()
        is_owner = (evidence.uploaded_by == user.id) or (case and (case.assigned_user_id == user.id or case.created_by == user.id))
        if not is_owner:
            raise HTTPException(status_code=403, detail="ABAC Policy: Investigating Officers can only access evidence in their assigned cases.")


def ensure_evidence_content_access(user: User, evidence, db: Session):
    """
    Strict ABAC check for viewing/downloading the raw decrypted evidence file:
    - ADMIN: 403 Forbidden (Separation of duties).
    - CUSTODIAN: 403 Forbidden (Physical inventory tracking only).
    - AUDITOR: 403 Forbidden unless explicitly unsealed via valid judicial warrant.
    - INVESTIGATOR (IO): Only their own assigned cases.
    - FORENSIC_OFFICER: Allowed for laboratory examination.
    - LEGAL_OFFICER: Allowed for court trial preparation (watermarked).
    """
    role = normalize_role(user.role)
    if role == "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Separation of Duties Policy: System Administrators have zero access to evidence file content, case narratives, or suspect PII."
        )
    if role == "CUSTODIAN":
        raise HTTPException(
            status_code=403,
            detail="Physical Custody Restriction: Malkhana Custodians only manage physical barcoded inventory and have no digital file content access."
        )
    if role == "AUDITOR":
        if not getattr(evidence, "is_unsealed_by_warrant", False):
            raise HTTPException(
                status_code=403,
                detail="Warrant Required: Compliance Auditors can only inspect audit logs and hashes. Evidence file contents are locked unless unsealed with a judicial court warrant."
            )
        return
    if role == "INVESTIGATOR":
        from app.models.case import Case
        case = db.query(Case).filter(Case.id == evidence.case_id).first()
        is_owner = (evidence.uploaded_by == user.id) or (case and (case.assigned_user_id == user.id or case.created_by == user.id))
        if not is_owner:
            raise HTTPException(
                status_code=403,
                detail="ABAC Policy: Investigating Officers can only access evidence within their assigned cases."
            )
        return
    if role == "FORENSIC_OFFICER":
        return
    if role == "LEGAL_OFFICER":
        return

