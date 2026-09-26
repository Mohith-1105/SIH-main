"""Evidence routes: upload, passport, verify, transfer, versions, custody"""
import os
import uuid
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io

from app.database import get_db
from app.models.case import Case
from app.models.evidence import Evidence, EvidenceVersion, CustodyEvent, EvidenceRelationship
from app.models.user import User
from app.models.ai_analysis import AIAnalysis
from app.schemas import (
    EvidenceOut, EvidencePassport, VerifyResult, VersionOut,
    CustodyEventOut, CustodyTransferRequest, GraphData, GraphNode, GraphEdge,
    DeletionRequest, DeletionReviewRequest, QuarantineRequest, WarrantUnsealRequest,
    CustodianLocationRequest, CustodianCheckInOutRequest, PhysicalReleaseApprovalRequest,
    EvidenceStateTransitionRequest, LabAnalysisRequest, CourtActionRequest, AuthorizedDestructionRequest,
)
from app.security.auth import (
    get_current_user, require_permission, require_any_permission,
    encrypt_file, decrypt_file, compute_sha256, normalize_role,
    ensure_evidence_content_access, ensure_evidence_access,
)
from app.blockchain import add_block
from app.ai.pipeline import run_pipeline
from app.utils.helpers import (
    generate_evidence_id, create_audit_log, generate_qr_base64,
    validate_file, sanitize_filename,
)
from app.config import settings

router = APIRouter(prefix="/api/evidence", tags=["Evidence"])


def _evidence_to_out(ev: Evidence, db: Session) -> EvidenceOut:
    out = EvidenceOut.model_validate(ev)
    case = db.query(Case).filter(Case.id == ev.case_id).first()
    out.case_number = case.case_number if case else ""
    uploader = db.query(User).filter(User.id == ev.uploaded_by).first()
    out.uploaded_by_name = uploader.full_name if uploader else "System"
    return out


@router.get("", response_model=list[EvidenceOut])
def list_evidence(
    case_id: Optional[int] = None,
    classification: Optional[str] = None,
    status: Optional[str] = None,
    custodian: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    role = normalize_role(user.role)
    if role == "ADMIN":
        # Separation of duties: Admin has zero access to evidence items, hashes, or case records
        return []

    q = db.query(Evidence)

    # ABAC Filter: Investigating Officers can only see evidence in their assigned cases
    if role == "INVESTIGATOR":
        assigned_case_ids = db.query(Case.id).filter(
            (Case.assigned_user_id == user.id) | (Case.created_by == user.id)
        ).all()
        allowed_case_ids = [r[0] for r in assigned_case_ids]
        q = q.filter((Evidence.case_id.in_(allowed_case_ids)) | (Evidence.uploaded_by == user.id))

    if case_id:
        q = q.filter(Evidence.case_id == case_id)
    if classification:
        q = q.filter(Evidence.classification == classification)
    if status:
        q = q.filter(Evidence.status == status)
    if custodian:
        q = q.filter(Evidence.current_custodian.ilike(f"%{custodian}%"))
    if search:
        q = q.filter(
            (Evidence.evidence_id.ilike(f"%{search}%")) |
            (Evidence.original_filename.ilike(f"%{search}%")) |
            (Evidence.description.ilike(f"%{search}%"))
        )
    evidences = q.order_by(Evidence.created_at.desc()).offset(skip).limit(limit).all()
    return [_evidence_to_out(e, db) for e in evidences]


@router.post("/upload", response_model=EvidenceOut)
async def upload_evidence(
    file: UploadFile = File(...),
    case_id: int = Form(...),
    description: str = Form(""),
    client_hash: Optional[str] = Form(None),
    source: str = Form(""),
    collector: str = Form(""),
    collection_location: str = Form(""),
    condition_at_intake: str = Form("INTACT"),
    storage_location: str = Form("Digital Vault / Secure Repository"),
    classification_override: Optional[str] = Form(None),
    user: User = Depends(require_permission("evidence.upload")),
    db: Session = Depends(get_db),
):
    # Validate case & ABAC ownership
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    role = normalize_role(user.role)
    if role == "INVESTIGATOR":
        if case.assigned_user_id and case.assigned_user_id != user.id and case.created_by != user.id:
            raise HTTPException(
                status_code=403,
                detail=f"ABAC Policy: Investigating Officers can only deposit evidence into their own assigned cases (Assigned to: {case.investigating_officer})."
            )

    # Read file
    file_bytes = await file.read()

    # Validate file (extension, MIME, max 25MB, filename)
    error = validate_file(file.filename or "unnamed", file.content_type or "", len(file_bytes), file_bytes=file_bytes)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # SHA-256 hash calculated by server
    file_hash = compute_sha256(file_bytes)

    # In-Transit Tamper Check (compares client calculated hash with vault server hash)
    if client_hash and client_hash.strip().lower() != file_hash.lower():
        create_audit_log(
            db, user_id=user.id, user_email=user.email, role=user.role,
            action="EVIDENCE_TRANSIT_TAMPER_ALERT", status="FAILED",
            resource_type="EVIDENCE", resource_id=case.case_number,
            details=f"In-Transit Tamper Detected: Client Hash ({client_hash[:16]}...) != Server Hash ({file_hash[:16]}...)"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Cryptographic Transit Tamper Detected: Client-side SHA-256 hash does not match vault server hash. File rejected."
        )


    # Encrypt file
    encrypted = encrypt_file(file_bytes)

    # Store encrypted file in backend/storage/evidence/
    safe_name = sanitize_filename(file.filename or "unnamed")
    storage_name = f"{uuid.uuid4().hex}_{safe_name}"
    storage_path = os.path.join(settings.STORAGE_DIR, storage_name)
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(encrypted)

    # Generate Evidence ID
    ev_id = generate_evidence_id(db)

    # Run AI pipeline
    ai_result = run_pipeline(
        file_bytes, file.content_type or "", file.filename or "",
        evidence_data={"file_size": len(file_bytes), "created_at": datetime.utcnow().isoformat()}
    )

    ev_classification = classification_override or ai_result.get("document_type", "OTHER")

    # Create evidence record with Stage 2 metadata
    evidence = Evidence(
        evidence_id=ev_id,
        case_id=case_id,
        original_filename=safe_name,
        stored_filename=storage_name,
        evidence_type=_mime_to_type(file.content_type),
        file_type=_mime_to_type(file.content_type),
        mime_type=file.content_type or "",
        file_size=len(file_bytes),
        sha256_hash=file_hash,
        encrypted_path=storage_name,
        status="REGISTERED",
        current_version=1,
        current_custodian=user.full_name,
        custodian_id=user.id,
        classification=ev_classification,
        ai_confidence=ai_result.get("confidence", 0.0),
        integrity_status="VERIFIED",
        blockchain_status="REGISTERED",
        risk_score=ai_result.get("risk_score", 0.0),
        description=description,
        uploaded_by=user.id,
        uploaded_at=datetime.utcnow(),
        source=source or f"Seized during {case.case_type} investigation",
        collector=collector or user.full_name,
        collection_datetime=datetime.utcnow(),
        collection_location=collection_location or case.incident_location or "Incident Scene",
        condition_at_intake=condition_at_intake or "INTACT",
        storage_location=storage_location or "Digital Vault / Secure Repository",
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # Create version record
    version = EvidenceVersion(
        evidence_id=evidence.id,
        version_number=1,
        filename=safe_name,
        sha256_hash=file_hash,
        encrypted_path=storage_name,
        file_size=len(file_bytes),
        action="EVIDENCE_UPLOADED",
        reason="Initial evidence upload",
        change_reason="Initial evidence upload",
        actor_id=user.id,
        actor_name=user.full_name,
        uploaded_by=user.full_name,
    )
    db.add(version)

    # Cryptographic Chain of Custody (Section 25)
    coc_event_id = f"COC-{ev_id[-6:]}-01"
    genesis_chain_hash = "GENESIS_CUSTODY_HASH"
    curr_coc_hash = compute_sha256(f"{genesis_chain_hash}:{ev_id}:{file_hash}:{user.full_name}:{datetime.utcnow().isoformat()}".encode())
    digital_sig = f"SIG-{user.role}-{file_hash[:16].upper()}"

    custody = CustodyEvent(
        event_id=coc_event_id,
        evidence_id=evidence.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        previous_custodian="Field Collection / Incident Scene",
        new_custodian=user.full_name,
        action="EVIDENCE_REGISTERED",
        reason="Evidence Intake & Cryptographic Registration",
        location=storage_location or "Digital Vault Repository",
        evidence_condition=condition_at_intake or "INTACT",
        integrity_state="VERIFIED",
        authorization=f"Intake Directive #{case.case_number}",
        digital_signature=digital_sig,
        notes=f"Evidence {ev_id} registered and hashed by {user.full_name}",
        sha256_hash=file_hash,
        previous_event_hash=genesis_chain_hash,
        current_event_hash=curr_coc_hash,
    )
    db.add(custody)
    evidence.custody_count = 1

    # Store AI analysis
    ai_record = AIAnalysis(
        evidence_id=evidence.id,
        document_type=ai_result.get("document_type", "OTHER"),
        confidence=ai_result.get("confidence", 0.0),
        extracted_text=ai_result.get("extracted_text", ""),
        summary=ai_result.get("summary", ""),
        entities_json=json.dumps(ai_result.get("entities", [])),
        risk_score=ai_result.get("risk_score", 0.0),
        risk_level=ai_result.get("risk_level", "LOW"),
        anomalies_json=json.dumps(ai_result.get("anomalies", [])),
        key_persons_count=ai_result.get("key_persons_count", 0),
        locations_count=ai_result.get("locations_count", 0),
        dates_count=ai_result.get("dates_count", 0),
        case_references_count=ai_result.get("case_references_count", 0),
        classification_method=ai_result.get("classification_method", "keyword"),
    )
    db.add(ai_record)

    # Create relationship to case
    rel = EvidenceRelationship(
        source_evidence_id=evidence.id,
        target_case_id=case_id,
        relationship_type="BELONGS_TO",
        label="Belongs to",
        node_type="CASE",
        node_label=case.case_number,
    )
    db.add(rel)

    db.commit()

    # Blockchain block
    add_block(db, ev_id, file_hash, "EVIDENCE_CREATED", user.full_name, user.role,
              {"case": case.case_number, "filename": safe_name})

    # Audit log
    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="EVIDENCE_UPLOADED", resource_type="EVIDENCE",
                    resource_id=ev_id, details=f"File: {safe_name}, Hash: {file_hash}")

    return _evidence_to_out(evidence, db)


@router.get("/{evidence_id_param}", response_model=EvidenceOut)
def get_evidence(
    evidence_id_param: int,
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="EVIDENCE_VIEWED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id)

    return _evidence_to_out(ev, db)


@router.get("/{evidence_id_param}/download")
def download_evidence(
    evidence_id_param: int,
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Enforce strict Separation of Duties & ABAC content access policy
    ensure_evidence_content_access(user, ev, db)

    # Check quarantine lock
    if ev.is_frozen:
        raise HTTPException(
            status_code=423,
            detail=f"Evidence Locked / Quarantined: This item was frozen by Compliance Oversight. Reason: {ev.quarantine_reason or 'Integrity audit under investigation'}"
        )

    storage_path = os.path.join(settings.STORAGE_DIR, ev.encrypted_path)
    if not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="Evidence file not found on disk")

    with open(storage_path, "rb") as f:
        encrypted_data = f.read()

    decrypted = decrypt_file(encrypted_data)

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="EVIDENCE_DOWNLOADED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=f"Downloaded by {user.full_name} ({user.role})")

    return StreamingResponse(
        io.BytesIO(decrypted),
        media_type=ev.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"{ev.original_filename}\""},
    )


@router.get("/{evidence_id_param}/watermarked-view")
def watermarked_view(
    evidence_id_param: int,
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    """
    Prosecutor & Court View: Returns decrypted file content decorated with an immutable dynamic digital watermark.
    Format: "CONFIDENTIAL COURT RECORD - PROSECUTOR VIEW - Adv. [Name] [Badge] - Timestamp: [UTC]"
    """
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    ensure_evidence_content_access(user, ev, db)

    storage_path = os.path.join(settings.STORAGE_DIR, ev.encrypted_path)
    if not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="Evidence file not found on disk")

    with open(storage_path, "rb") as f:
        encrypted_data = f.read()

    decrypted = decrypt_file(encrypted_data)
    watermark_stamp = f"CONFIDENTIAL COURT RECORD • PROSECUTION VIEW • Officer: {user.full_name} [{user.badge_number or 'LEG-102'}] • Access Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} • Evidence: {ev.evidence_id}"

    # Log specific watermarked prosecutor streaming
    create_audit_log(
        db, user_id=user.id, user_email=user.email, role=user.role,
        action="PROSECUTOR_WATERMARKED_VIEW", resource_type="EVIDENCE",
        resource_id=ev.evidence_id, details=watermark_stamp
    )

    # For text-based files, inject the watermark header directly
    if ev.mime_type and ("text" in ev.mime_type or "plain" in ev.mime_type):
        try:
            text_content = decrypted.decode("utf-8")
            watermarked_text = f"================================================================================\n{watermark_stamp}\n================================================================================\n\n{text_content}"
            decrypted = watermarked_text.encode("utf-8")
        except Exception:
            pass

    return StreamingResponse(
        io.BytesIO(decrypted),
        media_type=ev.mime_type or "application/octet-stream",
        headers={
            "X-Evidence-Watermark": watermark_stamp,
            "Content-Disposition": f"inline; filename=\"watermarked_{ev.original_filename}\"",
        },
    )


@router.post("/{evidence_id_param}/request-deletion")
def request_evidence_deletion(
    evidence_id_param: int,
    req: DeletionRequest,
    user: User = Depends(require_permission("evidence.request_deletion")),
    db: Session = Depends(get_db),
):
    """Investigating Officer requests deletion/archival with mandatory justification. Cannot delete directly."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    ev.deletion_requested = True
    ev.deletion_status = "REQUESTED"
    ev.deletion_request_reason = req.reason
    ev.deletion_request_by = user.id

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="DELETION_REQUESTED",
        location="Investigation Desk",
        evidence_condition="INTACT",
        notes=f"Deletion/Archival requested by {user.full_name}. Reason: {req.reason}",
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)
    db.commit()

    add_block(db, ev.evidence_id, ev.sha256_hash, "DELETION_REQUESTED",
              user.full_name, user.role, {"reason": req.reason})

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="DELETION_REQUESTED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=f"Reason: {req.reason}")

    return {"message": "Deletion request submitted for Compliance Auditor sign-off.", "status": "REQUESTED"}


@router.post("/{evidence_id_param}/approve-deletion")
def approve_evidence_deletion(
    evidence_id_param: int,
    req: DeletionReviewRequest,
    user: User = Depends(require_permission("evidence.approve_deletion")),
    db: Session = Depends(get_db),
):
    """Compliance Auditor sign-off on evidence destruction / archival."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    if not ev.deletion_requested:
        raise HTTPException(status_code=400, detail="No pending deletion request on this evidence record.")

    if req.decision.upper() == "APPROVED":
        ev.deletion_status = "APPROVED"
        ev.status = "ARCHIVED"
        action_name = "DELETION_APPROVED"
        detail_msg = f"Auditor {user.full_name} approved permanent archival. Comments: {req.comments}"
    else:
        ev.deletion_status = "REJECTED"
        ev.deletion_requested = False
        action_name = "DELETION_REJECTED"
        detail_msg = f"Auditor {user.full_name} rejected deletion request. Comments: {req.comments}"

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action=action_name,
        location="Compliance Oversight Office",
        evidence_condition="INTACT",
        notes=detail_msg,
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)
    db.commit()

    add_block(db, ev.evidence_id, ev.sha256_hash, action_name,
              user.full_name, user.role, {"decision": req.decision, "comments": req.comments})

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action=action_name, resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=detail_msg)

    return {"message": f"Deletion request {req.decision.upper()}.", "deletion_status": ev.deletion_status}


@router.post("/{evidence_id_param}/quarantine")
def quarantine_evidence(
    evidence_id_param: int,
    req: QuarantineRequest,
    user: User = Depends(require_permission("evidence.quarantine")),
    db: Session = Depends(get_db),
):
    """Compliance Auditor freezes or quarantines evidence if tampering or broken custody is suspected."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    ev.is_frozen = req.freeze
    ev.quarantine_reason = req.reason if req.freeze else ""
    action_name = "EVIDENCE_FROZEN" if req.freeze else "EVIDENCE_UNFROZEN"

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action=action_name,
        location="Compliance Oversight Office",
        evidence_condition="QUARANTINED" if req.freeze else "INTACT",
        notes=f"Quarantine status set to {req.freeze}. Reason: {req.reason}",
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)
    db.commit()

    add_block(db, ev.evidence_id, ev.sha256_hash, action_name,
              user.full_name, user.role, {"freeze": req.freeze, "reason": req.reason})

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action=action_name, resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=f"Frozen: {req.freeze}. Reason: {req.reason}")

    return {"message": f"Evidence quarantine status updated to {req.freeze}", "is_frozen": ev.is_frozen}


@router.post("/{evidence_id_param}/unseal-warrant")
def unseal_warrant(
    evidence_id_param: int,
    req: WarrantUnsealRequest,
    user: User = Depends(require_permission("evidence.unseal_warrant")),
    db: Session = Depends(get_db),
):
    """Compliance Auditor unseals evidence file content upon presenting a valid judicial court warrant."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    ev.is_unsealed_by_warrant = True
    ev.warrant_number = req.warrant_number

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="WARRANT_UNSEALED",
        location=f"Court Jurisdiction: {req.court_jurisdiction}",
        evidence_condition="INTACT",
        notes=f"Warrant #{req.warrant_number} unsealed content. Justification: {req.justification}",
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)
    db.commit()

    add_block(db, ev.evidence_id, ev.sha256_hash, "WARRANT_UNSEALED",
              user.full_name, user.role, {"warrant": req.warrant_number, "court": req.court_jurisdiction})

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="WARRANT_UNSEALED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=f"Warrant: {req.warrant_number} ({req.court_jurisdiction})")

    return {"message": f"Evidence unsealed under Judicial Warrant #{req.warrant_number}", "is_unsealed": True}


@router.post("/{evidence_id_param}/child-report", response_model=EvidenceOut)
async def upload_child_report(
    evidence_id_param: int,
    file: UploadFile = File(...),
    description: str = Form(""),
    user: User = Depends(require_permission("evidence.upload_child_report")),
    db: Session = Depends(get_db),
):
    """Forensic Specialist uploads child forensic report or extracted analysis data linked to parent evidence."""
    parent_ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not parent_ev:
        raise HTTPException(status_code=404, detail="Parent evidence not found")

    file_bytes = await file.read()
    error = validate_file(file.filename or "unnamed", file.content_type or "", len(file_bytes), file_bytes=file_bytes)
    if error:
        raise HTTPException(status_code=400, detail=error)

    file_hash = compute_sha256(file_bytes)
    encrypted = encrypt_file(file_bytes)

    safe_name = sanitize_filename(file.filename or "unnamed")
    storage_name = f"child_{uuid.uuid4().hex[:8]}_{safe_name}"
    storage_path = os.path.join(settings.STORAGE_DIR, storage_name)
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(encrypted)

    ev_id = generate_evidence_id(db)
    child_ev = Evidence(
        evidence_id=ev_id,
        case_id=parent_ev.case_id,
        original_filename=safe_name,
        stored_filename=storage_name,
        evidence_type="FORENSIC_REPORT",
        file_type="FORENSIC_REPORT",
        mime_type=file.content_type or "application/pdf",
        file_size=len(file_bytes),
        sha256_hash=file_hash,
        encrypted_path=storage_name,
        status="ANALYSIS_REPORT",
        current_custodian=user.full_name,
        custodian_id=user.id,
        classification="FORENSIC_REPORT",
        integrity_status="VERIFIED",
        blockchain_status="REGISTERED",
        description=f"Child forensic analysis report for parent item {parent_ev.evidence_id}: {description}",
        uploaded_by=user.id,
        parent_evidence_id=parent_ev.id,
        is_child_report=True,
        forensic_status="ANALYSIS_COMPLETE",
        custody_state="IN_FORENSIC_LAB",
    )
    db.add(child_ev)
    db.flush()

    # Link parent and child in relationships
    rel = EvidenceRelationship(
        source_evidence_id=child_ev.id,
        target_evidence_id=parent_ev.id,
        relationship_type="CHILD_REPORT_OF",
        label=f"Forensic Report for {parent_ev.evidence_id}",
        node_type="EVIDENCE",
        node_label=parent_ev.evidence_id,
    )
    db.add(rel)

    # Custody event
    custody = CustodyEvent(
        evidence_id=parent_ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="CHILD_REPORT_ATTACHED",
        location="Forensic Science Laboratory",
        evidence_condition="INTACT",
        notes=f"Forensic Analyst {user.full_name} generated child report {child_ev.evidence_id} ({safe_name})",
        sha256_hash=file_hash,
    )
    db.add(custody)
    parent_ev.forensic_status = "ANALYSIS_COMPLETE"

    db.commit()
    db.refresh(child_ev)

    add_block(db, child_ev.evidence_id, file_hash, "CHILD_FORENSIC_REPORT",
              user.full_name, user.role, {"parent_id": parent_ev.evidence_id, "report_file": safe_name})

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="CHILD_REPORT_ATTACHED", resource_type="EVIDENCE",
                    resource_id=child_ev.evidence_id, details=f"Linked to {parent_ev.evidence_id}")

    return _evidence_to_out(child_ev, db)


@router.put("/{evidence_id_param}/malkhana/location")
def update_malkhana_location(
    evidence_id_param: int,
    req: CustodianLocationRequest,
    user: User = Depends(require_permission("malkhana.update_location")),
    db: Session = Depends(get_db),
):
    """Custodian updates physical Malkhana storage shelf/bin."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    old_loc = ev.physical_location
    ev.physical_location = req.physical_location

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="PHYSICAL_LOCATION_UPDATED",
        location=req.physical_location,
        evidence_condition="INTACT",
        notes=f"Physical location updated from [{old_loc}] to [{req.physical_location}]. {req.notes or ''}",
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)
    db.commit()

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="PHYSICAL_LOCATION_UPDATED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=f"New Location: {req.physical_location}")

    return {"message": "Malkhana physical storage location updated", "physical_location": ev.physical_location}


@router.post("/{evidence_id_param}/malkhana/check-in-out")
def check_in_out_malkhana(
    evidence_id_param: int,
    req: CustodianCheckInOutRequest,
    user: User = Depends(require_permission("malkhana.check_in_out")),
    db: Session = Depends(get_db),
):
    """Custodian tracks physical check-in and check-out (e.g. for court appearance or lab)."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    new_status = "CHECKED_OUT" if req.action.upper() == "CHECK_OUT" else "CHECKED_IN"
    ev.physical_status = new_status

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action=f"PHYSICAL_{new_status}",
        location=ev.physical_location,
        evidence_condition="INTACT",
        notes=f"Physical item {new_status} by Custodian {user.full_name}. Handed to: {req.officer_name} [{req.badge_number}]. Purpose: {req.purpose}",
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)
    db.commit()

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action=f"PHYSICAL_{new_status}", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=f"Officer: {req.officer_name}, Purpose: {req.purpose}")

    return {"message": f"Physical item marked as {new_status}", "physical_status": ev.physical_status}


@router.post("/{evidence_id_param}/malkhana/approve-release")
def approve_physical_release(
    evidence_id_param: int,
    req: PhysicalReleaseApprovalRequest,
    user: User = Depends(require_permission("malkhana.approve_physical_release")),
    db: Session = Depends(get_db),
):
    """Custodian digitally authorizes physical release of item to IO or Court Official."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    ev.physical_release_approved = True
    ev.physical_release_to = req.approved_recipient

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="PHYSICAL_RELEASE_APPROVED",
        location=ev.physical_location,
        evidence_condition="INTACT",
        notes=f"Physical release authorized to {req.approved_recipient}. Ref: {req.authorization_ref}",
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)
    db.commit()

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="PHYSICAL_RELEASE_APPROVED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=f"To: {req.approved_recipient}, Ref: {req.authorization_ref}")

    return {"message": f"Physical release approved for {req.approved_recipient}", "physical_release_approved": True}



@router.get("/{evidence_id_param}/passport", response_model=EvidencePassport)
def get_passport(
    evidence_id_param: int,
    request: Request,
    host: Optional[str] = Query(None, description="Client host override for mobile or laptop scanning"),
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case = db.query(Case).filter(Case.id == ev.case_id).first()
    uploader = db.query(User).filter(User.id == ev.uploaded_by).first()

    from app.routes.public import get_base_client_url
    base_url = get_base_client_url(request, host)
    verification_url = f"{base_url}/verify/evidence/{ev.evidence_id}"
    qr = generate_qr_base64(verification_url)

    return EvidencePassport(
        evidence_id=ev.evidence_id,
        case_id=ev.case_id,
        case_number=case.case_number if case else "",
        original_filename=ev.original_filename,
        evidence_type=ev.evidence_type,
        document_type=ev.classification or ev.evidence_type,
        mime_type=ev.mime_type,
        file_size=ev.file_size,
        sha256_hash=ev.sha256_hash,
        created_at=ev.created_at,
        uploaded_at=ev.uploaded_at or ev.created_at,
        current_version=ev.current_version,
        current_custodian=ev.current_custodian,
        uploaded_by=uploader.full_name if uploader else "System",
        classification=ev.classification,
        ai_confidence=ev.ai_confidence,
        integrity_status=ev.integrity_status,
        blockchain_status=ev.blockchain_status,
        custody_count=ev.custody_count or 1,
        qr_code=qr,
        verification_url=verification_url,
    )


@router.post("/{evidence_id_param}/verify", response_model=VerifyResult)
def verify_evidence(
    evidence_id_param: int,
    user: User = Depends(require_any_permission("evidence.verify", "evidence.read")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Recalculate hash by decrypting stored file
    storage_path = os.path.join(settings.STORAGE_DIR, ev.encrypted_path)
    computed_hash = ""
    hash_match = False

    if os.path.exists(storage_path):
        with open(storage_path, "rb") as f:
            encrypted_data = f.read()
        try:
            decrypted = decrypt_file(encrypted_data)
            computed_hash = compute_sha256(decrypted)
            hash_match = (computed_hash == ev.sha256_hash)
        except Exception:
            computed_hash = "DECRYPTION_FAILED"
    else:
        computed_hash = "FILE_NOT_FOUND"

    from app.blockchain import verify_evidence_blocks
    bc_result = verify_evidence_blocks(db, ev.evidence_id)
    bc_valid = bc_result.get("valid", True)

    if hash_match:
        status_str = "VERIFIED"
        ev.integrity_status = "VERIFIED"
        details = "✓ INTEGRITY VERIFIED: Original file decrypted and SHA-256 hash matches stored record."
    else:
        status_str = "TAMPERED"
        ev.integrity_status = "TAMPERED"
        details = "⚠ TAMPERING DETECTED: Stored SHA-256 hash does not match decrypted storage."

    # Custody event for verification
    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="EVIDENCE_VERIFIED",
        location="Digital Evidence Lab",
        evidence_condition="INTACT" if hash_match else "COMPROMISED",
        notes=f"Verification performed by {user.full_name}: {status_str}",
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)
    ev.custody_count = (ev.custody_count or 0) + 1

    db.commit()

    add_block(db, ev.evidence_id, ev.sha256_hash, "EVIDENCE_VERIFIED",
              user.full_name, user.role, {"result": status_str})

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="EVIDENCE_VERIFIED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=status_str)

    return VerifyResult(
        status=status_str,
        hash_match=hash_match,
        stored_hash=ev.sha256_hash,
        computed_hash=computed_hash,
        blockchain_valid=bc_valid,
        details=details,
    )


@router.post("/{evidence_id_param}/transfer")
def transfer_custody(
    evidence_id_param: int,
    req: CustodyTransferRequest,
    user: User = Depends(require_any_permission("evidence.transfer", "evidence.write")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    target_id = req.target_user_id or req.recipient_user_id
    if not target_id:
        raise HTTPException(status_code=400, detail="recipient_user_id or target_user_id is required")

    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Cryptographic Hash Chaining (Section 25)
    last_event = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).order_by(CustodyEvent.id.desc()).first()
    prev_hash = last_event.current_event_hash if (last_event and last_event.current_event_hash) else "GENESIS_CUSTODY_HASH"
    curr_hash = compute_sha256(f"{prev_hash}:{ev.evidence_id}:{ev.sha256_hash}:{user.full_name}:{target.full_name}:{datetime.utcnow().isoformat()}".encode())
    digital_sig = f"SIG-{user.role}-{curr_hash[:16].upper()}"
    new_event_id = f"COC-{ev.evidence_id[-6:]}-{(ev.custody_count or 0) + 1:02d}"

    custody = CustodyEvent(
        event_id=new_event_id,
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        previous_custodian=ev.current_custodian or user.full_name,
        new_custodian=target.full_name,
        action="EVIDENCE_TRANSFERRED",
        reason=req.reason or "Forensic Examination / Laboratory Testing",
        location=req.location or "Digital Evidence Lab",
        evidence_condition=req.condition or "INTACT",
        integrity_state="VERIFIED",
        authorization=req.authorization or "Investigating Officer Transfer Order",
        digital_signature=digital_sig,
        notes=f"Transferred from {user.full_name} to {target.full_name}. {req.notes or ''}",
        sha256_hash=ev.sha256_hash,
        previous_event_hash=prev_hash,
        current_event_hash=curr_hash,
    )
    db.add(custody)

    ev.current_custodian = target.full_name
    ev.custodian_id = target.id
    ev.custody_count = (ev.custody_count or 0) + 1
    
    # Update custody state
    if "FORENSIC" in target.role:
        ev.custody_state = "IN_FORENSIC_LAB"
        ev.forensic_status = "IN_ANALYSIS"
        ev.status = "IN_EXAMINATION"
    elif "LEGAL" in target.role:
        ev.custody_state = "LEGAL_REVIEW"
        ev.status = "LEGAL_REVIEW"
    else:
        ev.custody_state = "SECURE_VAULT"

    db.commit()

    add_block(db, ev.evidence_id, ev.sha256_hash, "CUSTODY_TRANSFER",
              user.full_name, user.role,
              {"from": user.full_name, "to": target.full_name, "event_id": new_event_id, "prev_hash": prev_hash[:16], "curr_hash": curr_hash[:16]})

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="EVIDENCE_TRANSFERRED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id,
                    details=f"Transferred to {target.full_name} ({target.role}) [Event #{new_event_id}]")

    return {
        "success": True,
        "message": f"Custody transferred to {target.full_name}",
        "event_id": new_event_id,
        "current_event_hash": curr_hash,
        "previous_event_hash": prev_hash,
        "digital_signature": digital_sig,
    }


@router.post("/{evidence_id_param}/transition-state", response_model=EvidenceOut)
def transition_evidence_state(
    evidence_id_param: int,
    req: EvidenceStateTransitionRequest,
    user: User = Depends(require_any_permission("evidence.write", "evidence.transfer", "cases.quarantine")),
    db: Session = Depends(get_db),
):
    """
    Enforces the Section 26 Evidence State Machine:
    REGISTERED -> SECURED -> ASSIGNED -> IN_EXAMINATION -> ANALYSIS_COMPLETE -> RETURNED -> LEGAL_REVIEW -> COURT_SUBMITTED -> COURT_DISPOSITION -> CASE_CLOSED -> ARCHIVED -> RETENTION_EXPIRED -> AUTHORIZED_DESTRUCTION
    Exceptions: DISCREPANCY_FLAGGED, CONTAMINATION_SUSPECTED, INTEGRITY_FAILURE, ACCESS_REVIEW_REQUIRED, LEGAL_HOLD, RETAINED
    """
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    old_state = ev.status
    ev.status = req.new_state

    # Log state machine transition
    last_event = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).order_by(CustodyEvent.id.desc()).first()
    prev_hash = last_event.current_event_hash if (last_event and last_event.current_event_hash) else "GENESIS_CUSTODY_HASH"
    curr_hash = compute_sha256(f"{prev_hash}:{ev.evidence_id}:{req.new_state}:{user.full_name}:{datetime.utcnow().isoformat()}".encode())
    digital_sig = f"SIG-{user.role}-{curr_hash[:16].upper()}"

    coc = CustodyEvent(
        event_id=f"COC-{ev.evidence_id[-6:]}-{(ev.custody_count or 0) + 1:02d}",
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        previous_custodian=ev.current_custodian or user.full_name,
        new_custodian=ev.current_custodian or user.full_name,
        action=f"STATE_TRANSITION_{req.new_state}",
        reason=req.reason,
        location="Digital Evidence Vault",
        evidence_condition=ev.condition_at_intake or "INTACT",
        integrity_state="EXCEPTION" if "FLAGGED" in req.new_state or "FAILURE" in req.new_state else "VERIFIED",
        authorization=f"Authorized by {user.role} {user.full_name}",
        digital_signature=digital_sig,
        notes=f"State changed from {old_state} to {req.new_state}. {req.notes or ''}",
        sha256_hash=ev.sha256_hash,
        previous_event_hash=prev_hash,
        current_event_hash=curr_hash,
    )
    db.add(coc)
    ev.custody_count = (ev.custody_count or 0) + 1

    if req.new_state in ["DISCREPANCY_FLAGGED", "INTEGRITY_FAILURE", "CONTAMINATION_SUSPECTED"]:
        ev.integrity_status = "TAMPERED" if req.new_state == "INTEGRITY_FAILURE" else "FLAGGED"
        ev.is_frozen = True
        ev.quarantine_reason = f"Exception Flagged: {req.reason}"

    db.commit()
    db.refresh(ev)

    add_block(db, ev.evidence_id, ev.sha256_hash, f"STATE_{req.new_state}",
              user.full_name, user.role, {"old_state": old_state, "new_state": req.new_state, "reason": req.reason})

    create_audit_log(
        db, user_id=user.id, user_email=user.email, role=user.role,
        action=f"EVIDENCE_STATE_{req.new_state}", resource_type="EVIDENCE", resource_id=ev.evidence_id,
        details=f"Evidence state transitioned {old_state} -> {req.new_state}. Reason: {req.reason}"
    )

    return _evidence_to_out(ev, db)


@router.post("/{evidence_id_param}/lab-analysis", response_model=EvidenceOut)
def record_laboratory_analysis(
    evidence_id_param: int,
    req: LabAnalysisRequest,
    user: User = Depends(require_any_permission("evidence.read", "evidence.version")),
    db: Session = Depends(get_db),
):
    """
    Forensic Specialist laboratory testing workflow (Section 10):
    Sample registration, Seal/condition verification, Testing method, Quality Control (QC), Results & Findings.
    """
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    ev.lab_sample_id = req.sample_id
    ev.lab_test_requested = req.test_requested
    ev.lab_test_performed = req.test_performed
    ev.lab_qc_status = req.qc_status
    ev.lab_seal_intact = req.seal_intact
    ev.lab_findings = req.findings
    ev.lab_analyst = req.analyst or user.full_name
    ev.forensic_status = "ANALYSIS_COMPLETE"
    ev.status = "ANALYSIS_COMPLETE"

    # Add custody event for laboratory testing completion
    last_event = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).order_by(CustodyEvent.id.desc()).first()
    prev_hash = last_event.current_event_hash if (last_event and last_event.current_event_hash) else "GENESIS_CUSTODY_HASH"
    curr_hash = compute_sha256(f"{prev_hash}:{ev.evidence_id}:LAB_QC_{req.qc_status}:{user.full_name}:{datetime.utcnow().isoformat()}".encode())
    digital_sig = f"SIG-{user.role}-{curr_hash[:16].upper()}"

    coc = CustodyEvent(
        event_id=f"COC-{ev.evidence_id[-6:]}-{(ev.custody_count or 0) + 1:02d}",
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        previous_custodian=ev.current_custodian or user.full_name,
        new_custodian=ev.current_custodian or user.full_name,
        action="LABORATORY_ANALYSIS_COMPLETED",
        reason=f"Testing performed: {req.test_performed}",
        location="Forensic Science Laboratory (FSL)",
        evidence_condition="INTACT" if req.seal_intact else "SEAL_COMPROMISED",
        integrity_state="VERIFIED" if req.qc_status == "QC_PASSED" else "QC_FLAGGED",
        authorization="Forensic Examination Mandate",
        digital_signature=digital_sig,
        notes=f"Sample {req.sample_id} analyzed. QC: {req.qc_status}. Findings: {req.findings[:100]}",
        sha256_hash=ev.sha256_hash,
        previous_event_hash=prev_hash,
        current_event_hash=curr_hash,
    )
    db.add(coc)
    ev.custody_count = (ev.custody_count or 0) + 1
    db.commit()
    db.refresh(ev)

    add_block(db, ev.evidence_id, ev.sha256_hash, "LAB_ANALYSIS_COMPLETED",
              user.full_name, user.role, {
                  "sample_id": req.sample_id,
                  "test": req.test_performed,
                  "qc_status": req.qc_status,
              })

    create_audit_log(
        db, user_id=user.id, user_email=user.email, role=user.role,
        action="LABORATORY_TESTING_COMPLETED", resource_type="EVIDENCE", resource_id=ev.evidence_id,
        details=f"Laboratory test {req.test_performed} recorded by {user.full_name}. QC: {req.qc_status}"
    )

    return _evidence_to_out(ev, db)


@router.post("/{evidence_id_param}/court-action", response_model=EvidenceOut)
def record_court_presentation(
    evidence_id_param: int,
    req: CourtActionRequest,
    user: User = Depends(require_any_permission("cases.approve_court_ready", "evidence.read")),
    db: Session = Depends(get_db),
):
    """
    Legal Prosecutor court presentation & exhibit workflow (Section 13):
    Exhibit assignment, Court receipt, Presentation, Judicial action (ADMITTED / REJECTED / DEFERRED), Court order.
    """
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    ev.court_exhibit_number = req.exhibit_number
    ev.court_receipt_number = req.court_receipt_number
    ev.court_presentation_date = datetime.utcnow()
    ev.court_action = req.court_action
    ev.court_disposition_notes = req.presentation_notes or ""
    ev.court_order_ref = req.court_order_ref or ""
    ev.status = f"COURT_{req.court_action}"

    last_event = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).order_by(CustodyEvent.id.desc()).first()
    prev_hash = last_event.current_event_hash if (last_event and last_event.current_event_hash) else "GENESIS_CUSTODY_HASH"
    curr_hash = compute_sha256(f"{prev_hash}:{ev.evidence_id}:{req.exhibit_number}:{req.court_action}:{datetime.utcnow().isoformat()}".encode())
    digital_sig = f"SIG-COURT-{curr_hash[:16].upper()}"

    coc = CustodyEvent(
        event_id=f"COC-{ev.evidence_id[-6:]}-{(ev.custody_count or 0) + 1:02d}",
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        previous_custodian=ev.current_custodian or user.full_name,
        new_custodian="Judicial Court Docket / High Court Registry",
        action=f"COURT_PRESENTED_{req.court_action}",
        reason=f"Exhibit {req.exhibit_number} presented in judicial trial",
        location="Judicial District Courtroom",
        evidence_condition="INTACT",
        integrity_state="VERIFIED",
        authorization=f"Court Docket Order #{req.court_order_ref or req.court_receipt_number}",
        digital_signature=digital_sig,
        notes=f"Exhibit {req.exhibit_number} recorded. Action: {req.court_action}. Notes: {req.presentation_notes}",
        sha256_hash=ev.sha256_hash,
        previous_event_hash=prev_hash,
        current_event_hash=curr_hash,
    )
    db.add(coc)
    ev.custody_count = (ev.custody_count or 0) + 1
    db.commit()
    db.refresh(ev)

    add_block(db, ev.evidence_id, ev.sha256_hash, f"COURT_{req.court_action}",
              user.full_name, user.role, {
                  "exhibit_number": req.exhibit_number,
                  "court_receipt": req.court_receipt_number,
                  "court_action": req.court_action,
              })

    create_audit_log(
        db, user_id=user.id, user_email=user.email, role=user.role,
        action="COURT_ACTION_RECORDED", resource_type="EVIDENCE", resource_id=ev.evidence_id,
        details=f"Court action recorded: Exhibit {req.exhibit_number} marked as {req.court_action} by {user.full_name}"
    )

    return _evidence_to_out(ev, db)


@router.post("/{evidence_id_param}/authorized-destruction", response_model=EvidenceOut)
def execute_authorized_destruction(
    evidence_id_param: int,
    req: AuthorizedDestructionRequest,
    user: User = Depends(require_any_permission("cases.quarantine", "users.write")),
    db: Session = Depends(get_db),
):
    """
    Section 33 Evidence Destruction Workflow:
    Destruction must never be a normal delete operation.
    Retention Expired -> Legal Hold Check -> Compliance Verification -> Authorized Approval -> Destruction Scheduled -> Destruction Performed -> Destruction Certificate/Record -> Immutable Audit Event.
    """
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case = db.query(Case).filter(Case.id == ev.case_id).first()
    if case and case.legal_hold:
        raise HTTPException(status_code=400, detail="Destruction blocked: Case is subject to active Legal Hold.")

    if not req.retention_verified or not req.legal_hold_verified:
        raise HTTPException(status_code=400, detail="Statutory verification failed: Retention expiry and legal hold absence must be confirmed.")

    cert_id = f"CERT-DEST-{uuid.uuid4().hex[:12].upper()}"
    ev.destruction_certificate_id = cert_id
    ev.destruction_timestamp = datetime.utcnow()
    ev.destruction_authority = f"{user.full_name} ({user.role})"
    ev.destruction_method = req.destruction_method
    ev.is_destroyed = True
    ev.status = "AUTHORIZED_DESTRUCTION"
    ev.custody_state = "PERMANENTLY_DESTROYED"

    # Secure shredding of encrypted payload
    if ev.encrypted_path:
        storage_path = os.path.join(settings.STORAGE_DIR, ev.encrypted_path)
        if os.path.exists(storage_path):
            try:
                file_size = os.path.getsize(storage_path)
                with open(storage_path, "wb") as f:
                    f.write(os.urandom(file_size))  # Overwrite with random bytes
                os.remove(storage_path)  # Delete file
            except Exception as e:
                print(f"Warning: payload removal exception: {e}")

    # Cryptographic Chain of Custody Terminal Node
    last_event = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).order_by(CustodyEvent.id.desc()).first()
    prev_hash = last_event.current_event_hash if (last_event and last_event.current_event_hash) else "GENESIS_CUSTODY_HASH"
    curr_hash = compute_sha256(f"{prev_hash}:{ev.evidence_id}:{cert_id}:DESTROYED:{datetime.utcnow().isoformat()}".encode())
    digital_sig = f"SIG-DEST-{curr_hash[:16].upper()}"

    coc = CustodyEvent(
        event_id=f"COC-{ev.evidence_id[-6:]}-{(ev.custody_count or 0) + 1:02d}",
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        previous_custodian=ev.current_custodian or user.full_name,
        new_custodian="DESTROYED_RETENTION_EXPIRED",
        action="AUTHORIZED_DESTRUCTION_EXECUTED",
        reason=req.reason,
        location="Cryptographic Shredding Facility",
        evidence_condition="PERMANENTLY_DESTROYED",
        integrity_state="DESTROYED_CERTIFIED",
        authorization=f"Destruction Certificate #{cert_id}",
        digital_signature=digital_sig,
        notes=f"Cryptographic destruction executed via {req.destruction_method}. Certificate: {cert_id}",
        sha256_hash=ev.sha256_hash,
        previous_event_hash=prev_hash,
        current_event_hash=curr_hash,
    )
    db.add(coc)
    ev.custody_count = (ev.custody_count or 0) + 1
    db.commit()
    db.refresh(ev)

    add_block(db, ev.evidence_id, ev.sha256_hash, "AUTHORIZED_DESTRUCTION",
              user.full_name, user.role, {
                  "certificate_id": cert_id,
                  "method": req.destruction_method,
                  "reason": req.reason,
              })

    create_audit_log(
        db, user_id=user.id, user_email=user.email, role=user.role,
        action="DESTRUCTION_COMPLETED", resource_type="EVIDENCE", resource_id=ev.evidence_id,
        details=f"Evidence destroyed under Certificate {cert_id} by {user.full_name} ({user.role})"
    )

    return _evidence_to_out(ev, db)


@router.post("/{evidence_id_param}/versions", response_model=VersionOut)
async def create_version(
    evidence_id_param: int,
    file: UploadFile = File(...),
    change_reason: str = Form("Version update"),
    user: User = Depends(require_any_permission("evidence.version", "evidence.write")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    file_bytes = await file.read()
    error = validate_file(file.filename or "unnamed", file.content_type or "", len(file_bytes), file_bytes=file_bytes)
    if error:
        raise HTTPException(status_code=400, detail=error)

    file_hash = compute_sha256(file_bytes)
    encrypted = encrypt_file(file_bytes)
    safe_name = sanitize_filename(file.filename or "unnamed")
    storage_name = f"{uuid.uuid4().hex}_{safe_name}"
    storage_path = os.path.join(settings.STORAGE_DIR, storage_name)
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(encrypted)

    new_version_num = ev.current_version + 1
    ev.current_version = new_version_num
    ev.sha256_hash = file_hash
    ev.encrypted_path = storage_name
    ev.stored_filename = storage_name
    ev.file_size = len(file_bytes)
    ev.updated_at = datetime.utcnow()

    version = EvidenceVersion(
        evidence_id=ev.id,
        version_number=new_version_num,
        filename=safe_name,
        sha256_hash=file_hash,
        encrypted_path=storage_name,
        file_size=len(file_bytes),
        action="VERSION_CREATED",
        reason=change_reason,
        change_reason=change_reason,
        actor_id=user.id,
        actor_name=user.full_name,
        uploaded_by=user.full_name,
    )
    db.add(version)

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="VERSION_CREATED",
        location="Digital Evidence Lab",
        evidence_condition="INTACT",
        notes=f"Version {new_version_num} created by {user.full_name}. Reason: {change_reason}",
        sha256_hash=file_hash,
    )
    db.add(custody)
    ev.custody_count = (ev.custody_count or 0) + 1

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="VERSION_CREATED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details=f"Version {new_version_num}: {change_reason}")

    db.commit()
    db.refresh(version)
    return VersionOut.model_validate(version)


@router.get("/{evidence_id_param}/versions", response_model=list[VersionOut])
def get_versions(
    evidence_id_param: int,
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    versions = db.query(EvidenceVersion).filter(
        EvidenceVersion.evidence_id == ev.id
    ).order_by(EvidenceVersion.version_number).all()
    return [VersionOut.model_validate(v) for v in versions]



@router.get("/{evidence_id_param}/custody", response_model=list[CustodyEventOut])
def get_custody(
    evidence_id_param: int,
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    events = db.query(CustodyEvent).filter(
        CustodyEvent.evidence_id == ev.id
    ).order_by(CustodyEvent.timestamp).all()
    return [CustodyEventOut.model_validate(e) for e in events]


@router.get("/{evidence_id_param}/graph", response_model=GraphData)
def get_evidence_graph(
    evidence_id_param: int,
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id_param).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    nodes = []
    edges = []

    # Case node
    case = db.query(Case).filter(Case.id == ev.case_id).first()
    if case:
        nodes.append(GraphNode(id=f"case-{case.id}", type="case",
                              label=case.case_number, data={"title": case.title}))
        edges.append(GraphEdge(id=f"e-{ev.id}-case-{case.id}", source=f"ev-{ev.id}",
                              target=f"case-{case.id}", label="BELONGS_TO", type="BELONGS_TO"))

    # Evidence node
    nodes.append(GraphNode(id=f"ev-{ev.id}", type="evidence",
                          label=ev.evidence_id,
                          data={"filename": ev.original_filename, "classification": ev.classification}))

    # Related evidence in same case
    related = db.query(Evidence).filter(
        Evidence.case_id == ev.case_id, Evidence.id != ev.id
    ).limit(10).all()
    for r in related:
        nodes.append(GraphNode(id=f"ev-{r.id}", type="evidence",
                              label=r.evidence_id,
                              data={"filename": r.original_filename, "classification": r.classification}))
        edges.append(GraphEdge(id=f"e-{ev.id}-{r.id}", source=f"ev-{ev.id}",
                              target=f"ev-{r.id}", label="RELATED_TO", type="RELATED_TO"))

    # AI analysis entities as nodes
    ai = db.query(AIAnalysis).filter(AIAnalysis.evidence_id == ev.id).first()
    if ai and ai.entities_json:
        try:
            entities = json.loads(ai.entities_json)
            person_count = 0
            loc_count = 0
            for ent in entities[:15]:
                if ent.get("type") == "PERSON" and person_count < 5:
                    nid = f"person-{ent['value'][:20].replace(' ', '_')}"
                    nodes.append(GraphNode(id=nid, type="person", label=ent["value"]))
                    edges.append(GraphEdge(id=f"e-{ev.id}-{nid}", source=f"ev-{ev.id}",
                                          target=nid, label="REFERENCES", type="REFERENCES"))
                    person_count += 1
                elif ent.get("type") == "LOCATION" and loc_count < 3:
                    nid = f"loc-{ent['value'][:20].replace(' ', '_')}"
                    nodes.append(GraphNode(id=nid, type="location", label=ent["value"]))
                    edges.append(GraphEdge(id=f"e-{ev.id}-{nid}", source=f"ev-{ev.id}",
                                          target=nid, label="REFERENCES", type="REFERENCES"))
                    loc_count += 1
        except json.JSONDecodeError:
            pass

    # Custodian nodes
    custody_events = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).all()
    seen_actors = set()
    for ce in custody_events:
        if ce.actor_name not in seen_actors:
            seen_actors.add(ce.actor_name)
            nid = f"actor-{ce.actor_name.replace(' ', '_')}"
            nodes.append(GraphNode(id=nid, type="person",
                                  label=ce.actor_name, data={"role": ce.actor_role}))
            edges.append(GraphEdge(id=f"e-{ev.id}-{nid}", source=f"ev-{ev.id}",
                                  target=nid, label="HANDLED_BY", type="HANDLED_BY"))

    return GraphData(nodes=nodes, edges=edges)


def _mime_to_type(mime: str) -> str:
    if not mime:
        return "DOCUMENT"
    if "pdf" in mime:
        return "PDF"
    if "image" in mime:
        return "IMAGE"
    if "word" in mime or "docx" in mime:
        return "DOCX"
    if "text" in mime:
        return "TEXT"
    return "DOCUMENT"
