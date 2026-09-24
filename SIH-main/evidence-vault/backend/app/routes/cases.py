"""Case management routes"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.case import Case
from app.models.evidence import Evidence, CustodyEvent
from app.models.ai_analysis import AIAnalysis
from app.models.blockchain import BlockchainBlock
from app.models.user import User
from app.schemas import CaseCreate, CaseUpdate, CaseOut
from app.security.auth import get_current_user, require_permission, ensure_case_access, scoped_case_filter
from app.utils.helpers import generate_case_number, create_audit_log

router = APIRouter(prefix="/api/cases", tags=["Cases"])


@router.get("", response_model=list[CaseOut])
def list_cases(
    status: Optional[str] = None,
    case_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(require_permission("cases.read")),
    db: Session = Depends(get_db),
):
    q = db.query(Case)
    scope = scoped_case_filter(user, db, Case.id)
    if scope is not None:
        q = q.filter(scope)
    if status:
        q = q.filter(Case.status == status)
    if case_type:
        q = q.filter(Case.case_type == case_type)
    if search:
        q = q.filter(
            (Case.title.ilike(f"%{search}%")) |
            (Case.case_number.ilike(f"%{search}%")) |
            (Case.description.ilike(f"%{search}%"))
        )
    cases = q.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for c in cases:
        out = CaseOut.model_validate(c)
        out.evidence_count = db.query(Evidence).filter(Evidence.case_id == c.id).count()
        result.append(out)
    return result


@router.post("", response_model=CaseOut)
def create_case(
    req: CaseCreate,
    user: User = Depends(require_permission("cases.write")),
    db: Session = Depends(get_db),
):
    case = Case(
        case_number=generate_case_number(db),
        title=req.title,
        description=req.description,
        case_type=req.case_type,
        priority=req.priority,
        investigating_officer=req.investigating_officer or user.full_name,
        assigned_user_id=user.id,
        created_by=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="CASE_CREATED", resource_type="CASE",
                    resource_id=case.case_number)

    out = CaseOut.model_validate(case)
    out.evidence_count = 0
    return out


@router.get("/{case_id}", response_model=CaseOut)
def get_case(
    case_id: int,
    user: User = Depends(require_permission("cases.read")),
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    ensure_case_access(user, case, db)
    out = CaseOut.model_validate(case)
    out.evidence_count = db.query(Evidence).filter(Evidence.case_id == case.id).count()
    return out


@router.put("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    req: CaseUpdate,
    user: User = Depends(require_permission("cases.write")),
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    ensure_case_access(user, case, db)

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(case, field, value)
    db.commit()
    db.refresh(case)

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="CASE_UPDATED", resource_type="CASE",
                    resource_id=case.case_number)

    out = CaseOut.model_validate(case)
    out.evidence_count = db.query(Evidence).filter(Evidence.case_id == case.id).count()
    return out


@router.get("/{case_id}/evidence")
def list_case_evidence(
    case_id: int,
    user: User = Depends(require_permission("evidence.read")),
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    ensure_case_access(user, case, db)
    
    evidences = db.query(Evidence).filter(Evidence.case_id == case_id).order_by(Evidence.created_at.desc()).all()
    from app.routes.evidence import _evidence_to_out
    return [_evidence_to_out(e, db) for e in evidences]


@router.get("/{case_id}/flow")
def get_case_flow(
    case_id: int,
    user: User = Depends(require_permission("cases.read")),
    db: Session = Depends(get_db),
):
    """Retrieve end-to-end investigation workflow stages and ReactFlow graph nodes for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    ensure_case_access(user, case, db)

    evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    ev_count = len(evidences)
    ev_ids = [e.id for e in evidences]
    ai_records = db.query(AIAnalysis).filter(AIAnalysis.evidence_id.in_(ev_ids)).all() if ev_ids else []
    custody_records = db.query(CustodyEvent).filter(CustodyEvent.evidence_id.in_(ev_ids)).order_by(CustodyEvent.timestamp).all() if ev_ids else []

    ev_str_ids = [e.evidence_id for e in evidences]
    blocks = db.query(BlockchainBlock).filter(BlockchainBlock.evidence_id.in_(ev_str_ids)).all() if ev_str_ids else []

    is_closed = (case.status == "CLOSED")
    is_under_inv = (case.status == "UNDER_INVESTIGATION")

    # Determine stage statuses
    s1_status = "COMPLETED"
    s2_status = "COMPLETED" if ev_count > 0 else "CURRENT"
    s3_status = "COMPLETED" if (len(ai_records) > 0 or ev_count >= 2) else ("CURRENT" if ev_count > 0 else "PENDING")
    s4_status = "COMPLETED" if is_closed else ("CURRENT" if (is_under_inv or ev_count > 0) else "PENDING")
    s5_status = "COMPLETED" if is_closed else ("CURRENT" if (len(blocks) > 0 and ev_count >= 2) else "PENDING")
    s6_status = "COMPLETED" if is_closed else ("CURRENT" if (len(blocks) > 0 and is_under_inv) else "PENDING")
    s7_status = "COMPLETED" if is_closed else "PENDING"

    # If case closed, all prior are completed
    if is_closed:
        s1_status = s2_status = s3_status = s4_status = s5_status = s6_status = s7_status = "COMPLETED"

    stages = [
        {
            "id": "fir_registration",
            "step": 1,
            "name": "FIR & Incident Intake",
            "shortName": "FIR Registered",
            "status": s1_status,
            "description": f"First Information Report filed. Case Number {case.case_number} registered under {case.case_type} category.",
            "completed_at": case.created_at.strftime("%Y-%m-%d %H:%M") if case.created_at else None,
            "actor": case.investigating_officer or "Duty Officer",
            "checklist": [
                {"task": "FIR Lodged in Police Daily Diary", "done": True},
                {"task": "Case Number & Unique Hash Assigned", "done": True},
                {"task": "Primary Investigating Officer Appointed", "done": True},
            ],
        },
        {
            "id": "evidence_collection",
            "step": 2,
            "name": "Crime Scene & Evidence Seizure",
            "shortName": "Evidence Seizure",
            "status": s2_status,
            "description": f"Evidence vault catalogued {ev_count} physical/digital assets with SHA-256 hashes and AES-256 encryption." if ev_count > 0 else "Crime scene search underway; waiting for seized item intake.",
            "completed_at": evidences[0].created_at.strftime("%Y-%m-%d %H:%M") if ev_count > 0 and evidences[0].created_at else None,
            "actor": "Forensics & Field Team",
            "checklist": [
                {"task": "Crime Scene Cordoned & Surveyed", "done": ev_count > 0},
                {"task": "Physical/Digital Evidence Seized & Catalogued", "done": ev_count > 0},
                {"task": "Cryptographic Hash & Vault Storage", "done": ev_count > 0},
            ],
        },
        {
            "id": "forensic_analysis",
            "step": 3,
            "name": "Forensic & AI Risk Analysis",
            "shortName": "Forensic Lab",
            "status": s3_status,
            "description": "Laboratory tests, ballistics, autopsy examination, and AI entity verification." if (len(ai_records) > 0 or ev_count >= 2) else "Awaiting complete lab examination reports.",
            "completed_at": None,
            "actor": "State Forensic Science Laboratory (SFSL)",
            "checklist": [
                {"task": "Forensic Examination Reports Catalogued", "done": len(ai_records) > 0 or ev_count >= 2},
                {"task": "AI Document Classification & NER Extraction", "done": len(ai_records) > 0},
                {"task": "Integrity Verification & Risk Scoring", "done": len(ai_records) > 0 or ev_count >= 2},
            ],
        },
        {
            "id": "active_investigation",
            "step": 4,
            "name": "Active Investigation & Inquiries",
            "shortName": "Investigation",
            "status": s4_status,
            "description": "Interrogating persons of interest, recording witness statements under Section 161 CrPC, and tracking custody.",
            "completed_at": None,
            "actor": case.investigating_officer or "Lead Investigator",
            "checklist": [
                {"task": "Witness & Complainant Statements Recorded", "done": ev_count >= 2 or is_under_inv},
                {"task": "Custody Transfers Formally Handed Over", "done": len(custody_records) > 0},
                {"task": "Suspect Interrogation & Alibi Verification", "done": is_closed or is_under_inv},
            ],
        },
        {
            "id": "chargesheet_filed",
            "step": 5,
            "name": "Chargesheet Formulation & Blockchain Seal",
            "shortName": "Chargesheet",
            "status": s5_status,
            "description": "Final police report formulated under Section 173 CrPC. Complete evidence manifest anchored onto blockchain ledger.",
            "completed_at": None,
            "actor": "Investigating Agency & Legal Branch",
            "checklist": [
                {"task": "Final Police Investigation Report / Chargesheet Drafted", "done": is_closed},
                {"task": "Evidence Hashes Anchored to Cryptographic Block", "done": len(blocks) > 0},
                {"task": "Public Prosecutor Pre-Trial Legal Review", "done": is_closed},
            ],
        },
        {
            "id": "court_trial",
            "step": 6,
            "name": "Court Trial & Judicial Submission",
            "shortName": "Court Trial",
            "status": s6_status,
            "description": "Evidence passport and tamper-evident QR code presented before the Hon'ble Magistrate / Court.",
            "completed_at": None,
            "actor": "Sessions / District Court",
            "checklist": [
                {"task": "Evidence Digital Passport Submitted to Court", "done": is_closed},
                {"task": "Expert Witness & Forensic Testimony", "done": is_closed},
                {"task": "Magistrate Verification of Chain-of-Custody", "done": is_closed},
            ],
        },
        {
            "id": "case_closed",
            "step": 7,
            "name": "Judicial Disposal & Case Closed",
            "shortName": "Case Closed",
            "status": s7_status,
            "description": "Final judicial verdict pronounced. Case disposition recorded and archived in permanent cold ledger.",
            "completed_at": None,
            "actor": "Court of Law & Record Room",
            "checklist": [
                {"task": "Final Judgment & Order Recorded", "done": is_closed},
                {"task": "Evidence Archive or Return Protocol Executed", "done": is_closed},
            ],
        },
    ]

    # Calculate completed progress percentage
    completed_steps = sum(1 for s in stages if s["status"] == "COMPLETED")
    progress_pct = int((completed_steps / len(stages)) * 100)

    # --- Build ReactFlow Node Graph ---
    nodes = []
    edges = []

    # 1. Case Root Node
    nodes.append({
        "id": f"case-{case.id}",
        "type": "input",
        "position": {"x": 320, "y": 30},
        "data": {
            "label": f"📁 {case.case_number}\n{case.title[:30]}...",
            "case_number": case.case_number,
            "title": case.title,
            "case_type": case.case_type,
            "status": case.status,
            "node_type": "case",
        },
        "style": {
            "background": "#1e293b",
            "color": "#ffffff",
            "border": "2px solid #6366f1",
            "borderRadius": "12px",
            "padding": "12px",
            "fontSize": "11px",
            "width": 240,
            "fontWeight": "bold",
        }
    })

    # 2. Investigating Officer Node
    nodes.append({
        "id": f"officer-{case.id}",
        "position": {"x": 40, "y": 140},
        "data": {
            "label": f"👮 Lead Officer:\n{case.investigating_officer or 'Investigator'}",
            "node_type": "officer",
        },
        "style": {
            "background": "#0f172a",
            "color": "#93c5fd",
            "border": "1.5px solid #3b82f6",
            "borderRadius": "10px",
            "padding": "10px",
            "fontSize": "11px",
            "width": 170,
        }
    })
    edges.append({
        "id": f"e-case-officer",
        "source": f"case-{case.id}",
        "target": f"officer-{case.id}",
        "label": "ASSIGNED_TO",
        "animated": False,
        "style": {"stroke": "#3b82f6", "strokeWidth": 2},
    })

    # 3. Evidence Items (up to 4 for graph clarity)
    display_evidences = evidences[:4]
    ev_start_x = 260
    for idx, ev in enumerate(display_evidences):
        ev_node_id = f"ev-{ev.id}"
        x_pos = ev_start_x + (idx * 210)
        nodes.append({
            "id": ev_node_id,
            "position": {"x": x_pos, "y": 170},
            "data": {
                "label": f"🛡️ {ev.evidence_id}\n{ev.original_filename[:20]}",
                "evidence_id": ev.evidence_id,
                "classification": ev.classification,
                "integrity": ev.integrity_status,
                "node_type": "evidence",
            },
            "style": {
                "background": "#0f172a",
                "color": "#e0e7ff",
                "border": "1.5px solid #6366f1",
                "borderRadius": "10px",
                "padding": "10px",
                "fontSize": "10.5px",
                "width": 180,
            }
        })
        edges.append({
            "id": f"e-case-{ev_node_id}",
            "source": f"case-{case.id}",
            "target": ev_node_id,
            "label": "CONTAINS",
            "animated": True,
            "style": {"stroke": "#6366f1", "strokeWidth": 2},
        })

        # 4. Forensics / AI Node for this evidence
        ai_match = next((a for a in ai_records if a.evidence_id == ev.id), None)
        if ai_match:
            ai_node_id = f"ai-{ai_match.id}"
            nodes.append({
                "id": ai_node_id,
                "position": {"x": x_pos - 20, "y": 310},
                "data": {
                    "label": f"🔬 AI/Forensic Report\nRisk: {ai_match.risk_score:.0f}/100",
                    "doc_type": ai_match.document_type,
                    "risk": ai_match.risk_score,
                    "node_type": "forensic",
                },
                "style": {
                    "background": "#0f172a",
                    "color": "#fde68a",
                    "border": "1.5px solid #f59e0b",
                    "borderRadius": "10px",
                    "padding": "8px",
                    "fontSize": "10px",
                    "width": 160,
                }
            })
            edges.append({
                "id": f"e-{ev_node_id}-{ai_node_id}",
                "source": ev_node_id,
                "target": ai_node_id,
                "label": "ANALYZED",
                "style": {"stroke": "#f59e0b", "strokeDasharray": "4 4"},
            })

    # 5. Blockchain Ledger Anchor Node
    nodes.append({
        "id": f"bc-anchor-{case.id}",
        "position": {"x": 360, "y": 450},
        "data": {
            "label": f"⛓️ Blockchain Ledger Block\n{len(blocks)} Proof-of-Custody Blocks Sealed",
            "node_type": "blockchain",
        },
        "style": {
            "background": "#0f172a",
            "color": "#67e8f9",
            "border": "2px solid #06b6d4",
            "borderRadius": "12px",
            "padding": "12px",
            "fontSize": "11px",
            "width": 240,
            "fontWeight": "bold",
        }
    })

    # Connect evidence nodes to blockchain
    for ev in display_evidences:
        edges.append({
            "id": f"e-ev-{ev.id}-bc",
            "source": f"ev-{ev.id}",
            "target": f"bc-anchor-{case.id}",
            "label": "SEALED",
            "animated": True,
            "style": {"stroke": "#06b6d4", "strokeWidth": 1.5},
        })

    # 6. Court & Judicial Outcome Node
    nodes.append({
        "id": f"court-verdict-{case.id}",
        "type": "output",
        "position": {"x": 360, "y": 580},
        "data": {
            "label": f"⚖️ Court of Law\nStatus: {case.status.replace('_', ' ')}",
            "node_type": "court",
        },
        "style": {
            "background": "#0f172a",
            "color": "#86efac",
            "border": "2px solid #10b981",
            "borderRadius": "12px",
            "padding": "12px",
            "fontSize": "11px",
            "width": 240,
            "fontWeight": "bold",
        }
    })
    edges.append({
        "id": f"e-bc-court",
        "source": f"bc-anchor-{case.id}",
        "target": f"court-verdict-{case.id}",
        "label": "PROSECUTION_READY",
        "style": {"stroke": "#10b981", "strokeWidth": 2.5},
    })

    return {
        "case_id": case.id,
        "case_number": case.case_number,
        "title": case.title,
        "status": case.status,
        "priority": case.priority,
        "stages": stages,
        "progress_pct": progress_pct,
        "current_stage": next((s["name"] for s in stages if s["status"] == "CURRENT"), "Case Closed" if is_closed else "Active Investigation"),
        "graph": {
            "nodes": nodes,
            "edges": edges,
        },
    }


@router.post("/{case_id}/advance-stage")
def advance_case_stage(
    case_id: int,
    stage_id: str = Query(..., description="Stage identifier to update or advance to"),
    user: User = Depends(require_permission("cases.write")),
    db: Session = Depends(get_db),
):
    """Advance or update case workflow status with automated audit tracking."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    ensure_case_access(user, case, db)

    if stage_id in ["case_closed", "closed"]:
        case.status = "CLOSED"
    elif stage_id in ["chargesheet_filed", "court_trial", "active_investigation"]:
        case.status = "UNDER_INVESTIGATION"
    else:
        case.status = "OPEN"

    db.commit()
    db.refresh(case)

    create_audit_log(
        db,
        user_id=user.id,
        user_email=user.email,
        role=user.role,
        action="CASE_STAGE_ADVANCED",
        resource_type="CASE",
        resource_id=f"{case.case_number} -> {stage_id.upper()}",
    )

    return {"message": f"Case advanced to stage {stage_id}", "status": case.status}

