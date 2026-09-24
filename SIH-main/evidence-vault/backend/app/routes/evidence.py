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
)
from app.security.auth import (get_current_user, require_permission, require_any_permission,
                               ensure_evidence_access, ensure_case_access, scoped_case_filter,
                               encrypt_file, decrypt_file, compute_sha256)
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
    q = db.query(Evidence)
    scope = scoped_case_filter(user, db, Evidence.case_id)
    if scope is not None:
        q = q.filter(scope)
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
    user: User = Depends(require_any_permission("evidence.upload", "evidence.write")),
    db: Session = Depends(get_db),
):
    # Validate case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    ensure_case_access(user, case, db)

    # Read file
    file_bytes = await file.read()

    # Validate file (extension, MIME, max 25MB, filename)
    error = validate_file(file.filename or "unnamed", file.content_type or "", len(file_bytes), file_bytes=file_bytes)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # SHA-256 hash
    file_hash = compute_sha256(file_bytes)

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

    # Create evidence record
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
        classification=ai_result.get("document_type", "OTHER"),
        ai_confidence=ai_result.get("confidence", 0.0),
        integrity_status="VERIFIED",
        blockchain_status="REGISTERED",
        risk_score=ai_result.get("risk_score", 0.0),
        description=description,
        uploaded_by=user.id,
        uploaded_at=datetime.utcnow(),
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

    # Create custody event
    custody = CustodyEvent(
        evidence_id=evidence.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="EVIDENCE_CREATED",
        location="Digital Evidence Lab",
        evidence_condition="INTACT",
        notes=f"Evidence {ev_id} uploaded by {user.full_name}",
        sha256_hash=file_hash,
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
    ensure_evidence_access(user, ev, db)

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
    ensure_evidence_access(user, ev, db)

    storage_path = os.path.join(settings.STORAGE_DIR, ev.encrypted_path)
    if not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="Evidence file not found on disk")

    with open(storage_path, "rb") as f:
        encrypted_data = f.read()

    decrypted = decrypt_file(encrypted_data)

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="EVIDENCE_DOWNLOADED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id)

    return StreamingResponse(
        io.BytesIO(decrypted),
        media_type=ev.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"{ev.original_filename}\""},
    )


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
    ensure_evidence_access(user, ev, db)

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
    ensure_evidence_access(user, ev, db)

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
    ensure_evidence_access(user, ev, db)

    target_id = req.target_user_id or req.recipient_user_id
    if not target_id:
        raise HTTPException(status_code=400, detail="recipient_user_id or target_user_id is required")

    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    custody = CustodyEvent(
        evidence_id=ev.id,
        actor_id=user.id,
        actor_name=user.full_name,
        actor_role=user.role,
        action="EVIDENCE_TRANSFERRED",
        location=req.location or "Digital Evidence Lab",
        evidence_condition=req.condition or "INTACT",
        notes=f"Transferred from {user.full_name} to {target.full_name}. {req.notes or ''}",
        sha256_hash=ev.sha256_hash,
    )
    db.add(custody)

    ev.current_custodian = target.full_name
    ev.custodian_id = target.id
    ev.custody_count = (ev.custody_count or 0) + 1
    db.commit()

    add_block(db, ev.evidence_id, ev.sha256_hash, "CUSTODY_TRANSFER",
              user.full_name, user.role,
              {"from": user.full_name, "to": target.full_name})

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="EVIDENCE_TRANSFERRED", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id,
                    details=f"Transferred to {target.full_name} ({target.role})")

    return {"success": True, "message": f"Custody transferred to {target.full_name}"}


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
    ensure_evidence_access(user, ev, db)

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
    ensure_evidence_access(user, ev, db)
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
    ensure_evidence_access(user, ev, db)
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
    ensure_evidence_access(user, ev, db)

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
