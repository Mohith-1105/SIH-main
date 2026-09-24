"""Dashboard & utility routes"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models.case import Case
from app.models.evidence import Evidence, CustodyEvent
from app.models.blockchain import BlockchainBlock
from app.models.audit import AuditLog
from app.models.ai_analysis import AIAnalysis
from app.models.user import User
from app.schemas import DashboardStats
from app.security.auth import get_current_user, visible_case_ids
from app.config import settings

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ids = visible_case_ids(user, db)
    case_scope = [] if ids is not None else None
    if ids is not None:
        case_scope = Case.id.in_(ids)
        ev_scope = Evidence.case_id.in_(ids)
    else:
        ev_scope = None

    total_cases = db.query(Case).count() if case_scope is None else db.query(Case).filter(case_scope).count()
    total_evidence = db.query(Evidence).count() if ev_scope is None else db.query(Evidence).filter(ev_scope).count()
    verified_q = db.query(Evidence).filter(Evidence.integrity_status == "VERIFIED")
    pending_q = db.query(Evidence).filter(Evidence.integrity_status == "PENDING")
    high_risk_q = db.query(AIAnalysis).join(Evidence, AIAnalysis.evidence_id == Evidence.id)
    high_risk_q = high_risk_q.filter(AIAnalysis.risk_score >= 50)
    if ev_scope is not None:
        verified_q = verified_q.filter(ev_scope)
        pending_q = pending_q.filter(ev_scope)
        high_risk_q = high_risk_q.filter(ev_scope)
    verified = verified_q.count()
    pending = pending_q.count()
    high_risk = high_risk_q.count()
    blocks = db.query(BlockchainBlock).count()
    transfers = db.query(CustodyEvent).filter(CustodyEvent.action.in_(["EVIDENCE_TRANSFERRED", "CUSTODY_TRANSFERRED"])).count()

    # Recent activity (filter out auth logins to keep dashboard focused on evidence & case operations)
    recent_logs = (
        db.query(AuditLog)
        .filter(AuditLog.action.notin_(["LOGIN", "LOGOUT"]))
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )
    if not recent_logs:
        recent_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()

    recent = [
        {
            "action": l.action,
            "user": l.user_email,
            "resource": f"{l.resource_type} {l.resource_id}".strip(),
            "timestamp": l.timestamp.isoformat() if l.timestamp else "",
            "status": l.status,
        }
        for l in recent_logs
    ]

    # Evidence by category
    categories = db.query(
        Evidence.classification, func.count(Evidence.id)
    )
    if ev_scope is not None:
        categories = categories.filter(ev_scope)
    categories = categories.group_by(Evidence.classification).all()
    ev_by_cat = [{"name": c[0] or "OTHER", "value": c[1]} for c in categories]

    # Case status distribution
    case_statuses = db.query(
        Case.status, func.count(Case.id)
    )
    if case_scope is not None:
        case_statuses = case_statuses.filter(case_scope)
    case_statuses = case_statuses.group_by(Case.status).all()
    case_dist = [{"name": s[0], "value": s[1]} for s in case_statuses]

    # Evidence over time (last 7 days)
    ev_over_time = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count_q = db.query(Evidence).filter(
            Evidence.created_at >= day_start,
            Evidence.created_at <= day_end,
        )
        if ev_scope is not None:
            count_q = count_q.filter(ev_scope)
        ev_over_time.append({"date": day.strftime("%b %d"), "count": count_q.count()})

    # Risk distribution
    def _risk_count(lo, hi):
        q = db.query(AIAnalysis).join(Evidence, AIAnalysis.evidence_id == Evidence.id)
        q = q.filter(AIAnalysis.risk_score >= lo, AIAnalysis.risk_score < hi)
        if ev_scope is not None:
            q = q.filter(ev_scope)
        return q.count()

    low = _risk_count(0, 30)
    med = _risk_count(30, 70)
    high = _risk_count(70, 999)
    risk_dist = [
        {"name": "Low Risk", "value": low},
        {"name": "Medium Risk", "value": med},
        {"name": "High Risk", "value": high},
    ]

    # High risk alerts
    high_risk_items = high_risk_q.limit(5).all()
    alerts = []
    for a in high_risk_items:
        ev = db.query(Evidence).filter(Evidence.id == a.evidence_id).first()
        if ev:
            alerts.append({
                "evidence_id": ev.evidence_id,
                "filename": ev.original_filename,
                "risk_score": a.risk_score,
                "risk_level": a.risk_level,
            })

    return DashboardStats(
        total_cases=total_cases,
        total_evidence=total_evidence,
        verified_evidence=verified,
        pending_review=pending,
        custody_transfers=transfers,
        ai_alerts=high_risk,
        blockchain_blocks=blocks,
        recent_activity=recent,
        evidence_by_category=ev_by_cat,
        case_status_distribution=case_dist,
        evidence_over_time=ev_over_time,
        risk_distribution=risk_dist,
        high_risk_alerts=alerts,
    )



@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Check database
    db_status = "connected"
    try:
        db.execute(func.count(User.id).select())
    except Exception:
        db_status = "error"

    # Check storage
    import os
    storage_status = "available" if os.path.isdir(settings.STORAGE_DIR) else "unavailable"

    return {
        "status": "healthy",
        "database": db_status,
        "storage": storage_status,
        "ai": "available",
        "blockchain": "operational",
        "demo_mode": settings.DEMO_MODE,
    }


@router.get("/search")
def global_search(
    q: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = {"cases": [], "evidence": [], "people": []}

    ids = visible_case_ids(user, db)
    case_scope = [] if ids is None else Case.id.in_(ids)

    # Search cases
    cases = db.query(Case).filter(
        (Case.title.ilike(f"%{q}%")) |
        (Case.case_number.ilike(f"%{q}%")) |
        (Case.description.ilike(f"%{q}%"))
    )
    if case_scope is not None:
        cases = cases.filter(case_scope)
    cases = cases.limit(10).all()
    results["cases"] = [{"id": c.id, "case_number": c.case_number, "title": c.title} for c in cases]

    # Search evidence
    evidence = db.query(Evidence).filter(
        (Evidence.evidence_id.ilike(f"%{q}%")) |
        (Evidence.original_filename.ilike(f"%{q}%")) |
        (Evidence.description.ilike(f"%{q}%"))
    )
    if case_scope is not None:
        evidence = evidence.filter(Evidence.case_id.in_(ids))
    evidence = evidence.limit(10).all()
    results["evidence"] = [{"id": e.id, "evidence_id": e.evidence_id,
                           "filename": e.original_filename} for e in evidence]

    # Search users
    users = db.query(User).filter(
        (User.full_name.ilike(f"%{q}%")) |
        (User.email.ilike(f"%{q}%"))
    ).limit(5).all()
    results["people"] = [{"id": u.id, "name": u.full_name, "role": u.role} for u in users]

    return results


@router.post("/demo/simulate-tamper")
def simulate_tamper(
    evidence_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Demo-only: Simulate tampering by modifying stored hash."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Only available in demo mode")

    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Modify the hash to simulate tampering
    original_hash = ev.sha256_hash
    ev.sha256_hash = "TAMPERED_" + original_hash[9:]
    ev.integrity_status = "TAMPERED"
    db.commit()

    from app.utils.helpers import create_audit_log
    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="DEMO_TAMPER_SIMULATION", resource_type="EVIDENCE",
                    resource_id=ev.evidence_id, details="Simulated tampering for demo")

    return {
        "success": True,
        "message": "Tampering simulated. Original hash modified.",
        "original_hash": original_hash,
        "tampered_hash": ev.sha256_hash,
    }
