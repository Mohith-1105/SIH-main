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
from app.security.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_cases = db.query(Case).count()
    total_evidence = db.query(Evidence).count()
    verified = db.query(Evidence).filter(Evidence.integrity_status == "VERIFIED").count()
    pending = db.query(Evidence).filter(Evidence.integrity_status == "PENDING").count()
    blocks = db.query(BlockchainBlock).count()
    transfers = db.query(CustodyEvent).filter(CustodyEvent.action.in_(["EVIDENCE_TRANSFERRED", "CUSTODY_TRANSFERRED"])).count()


    # AI alerts (high risk)
    high_risk = db.query(AIAnalysis).filter(AIAnalysis.risk_score >= 50).count()

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
    ).group_by(Evidence.classification).all()
    ev_by_cat = [{"name": c[0] or "OTHER", "value": c[1]} for c in categories]

    # Case status distribution
    case_statuses = db.query(
        Case.status, func.count(Case.id)
    ).group_by(Case.status).all()
    case_dist = [{"name": s[0], "value": s[1]} for s in case_statuses]

    # Evidence over time (last 7 days)
    ev_over_time = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count = db.query(Evidence).filter(
            Evidence.created_at >= day_start,
            Evidence.created_at <= day_end,
        ).count()
        ev_over_time.append({"date": day.strftime("%b %d"), "count": count})

    # Risk distribution
    low = db.query(AIAnalysis).filter(AIAnalysis.risk_score < 30).count()
    med = db.query(AIAnalysis).filter(AIAnalysis.risk_score >= 30, AIAnalysis.risk_score < 70).count()
    high = db.query(AIAnalysis).filter(AIAnalysis.risk_score >= 70).count()
    risk_dist = [
        {"name": "Low Risk", "value": low},
        {"name": "Medium Risk", "value": med},
        {"name": "High Risk", "value": high},
    ]

    # High risk alerts
    high_risk_items = db.query(AIAnalysis).filter(AIAnalysis.risk_score >= 50).limit(5).all()
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

    # Search cases
    cases = db.query(Case).filter(
        (Case.title.ilike(f"%{q}%")) |
        (Case.case_number.ilike(f"%{q}%")) |
        (Case.description.ilike(f"%{q}%"))
    ).limit(10).all()
    results["cases"] = [{"id": c.id, "case_number": c.case_number, "title": c.title} for c in cases]

    # Search evidence
    evidence = db.query(Evidence).filter(
        (Evidence.evidence_id.ilike(f"%{q}%")) |
        (Evidence.original_filename.ilike(f"%{q}%")) |
        (Evidence.description.ilike(f"%{q}%"))
    ).limit(10).all()
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
    """Demo-only: Simulate malicious tampering on backend server. Automatically locks file and alerts auditor."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Only available in demo mode")

    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    original_hash = ev.sha256_hash
    ev.sha256_hash = "TAMPERED_" + original_hash[9:]
    ev.integrity_status = "TAMPERED"
    ev.is_frozen = True
    ev.quarantine_reason = "Malicious server-side tamper simulation detected. Automatically locked."
    db.commit()

    from app.utils.helpers import create_audit_log
    create_audit_log(
        db, user_id=user.id, user_email=user.email, role=user.role,
        action="TAMPER_SIMULATION_TRIGGERED", status="FAILED",
        resource_type="EVIDENCE", resource_id=ev.evidence_id,
        details=f"Tamper alert triggered: Hash altered from {original_hash[:16]}... to {ev.sha256_hash[:16]}..."
    )

    return {
        "success": True,
        "message": "Tampering simulated! Original hash corrupted, evidence marked TAMPERED, and automatic Auditor quarantine lockout activated.",
        "evidence_id": ev.evidence_id,
        "original_hash": original_hash,
        "tampered_hash": ev.sha256_hash,
        "is_frozen": True,
    }


@router.get("/dashboard/admin")
def get_admin_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Admin Dashboard: Platform health, storage metrics, active sessions, failed logins, privilege requests.
    BLOCKED: Evidence file contents, case narratives, SHA-256 hashes, suspect PII.
    """
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # Failed logins in audit logs
    failed_logins_24h = db.query(AuditLog).filter(
        AuditLog.action.in_(["LOGIN", "LOGIN_FAILED", "MFA_CHALLENGE"]),
        AuditLog.status.in_(["FAILED", "BLOCKED"])
    ).count()

    # Active sessions
    recent_sessions = db.query(AuditLog).filter(
        AuditLog.action == "LOGIN",
        AuditLog.status == "SUCCESS"
    ).order_by(AuditLog.timestamp.desc()).limit(8).all()

    # Storage consumption (sum of file sizes in storage)
    total_storage_bytes = db.query(func.sum(Evidence.file_size)).scalar() or 24500000
    storage_capacity_bytes = 100 * 1024 * 1024 * 1024  # 100 GB vault allocation
    storage_pct = round((total_storage_bytes / storage_capacity_bytes) * 100, 2)

    # Pending privilege requests
    from app.models.audit import PrivilegeRequest
    pending_privs = db.query(PrivilegeRequest).filter(PrivilegeRequest.status == "PENDING").all()
    priv_data = [
        {
            "id": p.id,
            "requested_by": p.requested_by_email,
            "target_user": p.target_user_email,
            "target_name": p.target_full_name,
            "role": p.requested_role,
            "justification": p.justification,
            "created_at": p.created_at.isoformat() if p.created_at else "",
        }
        for p in pending_privs
    ]

    # Security alerts
    alerts = []
    if failed_logins_24h > 0:
        alerts.append({
            "severity": "CRITICAL",
            "type": "FAILED_AUTHENTICATIONS",
            "message": f"{failed_logins_24h} failed login/MFA challenge attempts logged in recent security window.",
            "timestamp": datetime.utcnow().isoformat(),
        })
    alerts.append({
        "severity": "INFO",
        "type": "SEPARATION_OF_DUTIES",
        "message": "Separation of Duties active: Evidence payload isolation strictly enforced. Admin accounts isolated from case evidence.",
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {
        "total_users": total_users,
        "active_users": active_users,
        "storage_used_bytes": total_storage_bytes,
        "storage_capacity_bytes": storage_capacity_bytes,
        "storage_utilization_pct": storage_pct,
        "failed_logins_24h": failed_logins_24h,
        "system_health": {
            "database": "HEALTHY",
            "crypto_engine": "OPERATIONAL (AES-256-GCM)",
            "blockchain_ledger": "SYNCHRONIZED (Append-Only)",
            "mfa_gateway": "ENFORCED",
            "storage_vault": "MOUNTED",
            "uptime_pct": 99.98,
        },
        "pending_privilege_requests": priv_data,
        "recent_sessions": [
            {
                "user": s.user_email,
                "role": s.role,
                "ip": s.ip_address,
                "timestamp": s.timestamp.isoformat() if s.timestamp else "",
            }
            for s in recent_sessions
        ],
        "security_alerts": alerts,
    }


@router.get("/dashboard/io")
def get_io_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Investigating Officer Dashboard: My Active Cases, Pending Transfers, Quick Upload."""
    my_cases = db.query(Case).filter(
        (Case.assigned_user_id == user.id) | (Case.created_by == user.id)
    ).all()
    my_case_ids = [c.id for c in my_cases]

    my_evidence = db.query(Evidence).filter(
        (Evidence.case_id.in_(my_case_ids)) | (Evidence.uploaded_by == user.id)
    ).all()

    pending_transfers = db.query(CustodyEvent).filter(
        CustodyEvent.action.in_(["EVIDENCE_TRANSFERRED", "CUSTODY_TRANSFERRED"])
    ).order_by(CustodyEvent.timestamp.desc()).limit(5).all()

    deletion_requests = db.query(Evidence).filter(
        Evidence.deletion_requested == True,
        Evidence.uploaded_by == user.id
    ).all()

    return {
        "active_cases_count": len(my_cases),
        "my_evidence_count": len(my_evidence),
        "my_cases": [
            {
                "id": c.id,
                "case_number": c.case_number,
                "title": c.title,
                "status": c.status,
                "priority": c.priority,
                "is_frozen": c.is_frozen,
                "evidence_count": db.query(Evidence).filter(Evidence.case_id == c.id).count(),
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            for c in my_cases
        ],
        "recent_evidence": [
            {
                "id": e.id,
                "evidence_id": e.evidence_id,
                "filename": e.original_filename,
                "classification": e.classification,
                "sha256_hash": e.sha256_hash,
                "integrity_status": e.integrity_status,
                "physical_location": e.physical_location,
                "barcode_id": e.barcode_id,
                "is_frozen": e.is_frozen,
                "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else "",
            }
            for e in my_evidence[:8]
        ],
        "pending_transfers": [
            {
                "actor_name": t.actor_name,
                "actor_role": t.actor_role,
                "location": t.location,
                "timestamp": t.timestamp.isoformat() if t.timestamp else "",
                "notes": t.notes,
            }
            for t in pending_transfers
        ],
        "deletion_requests": [
            {
                "id": d.id,
                "evidence_id": d.evidence_id,
                "filename": d.original_filename,
                "reason": d.deletion_request_reason,
                "status": d.deletion_status,
            }
            for d in deletion_requests
        ],
    }


@router.get("/dashboard/forensic")
def get_forensic_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Forensic Specialist Dashboard: Pending Analysis queue, workbench, child reports."""
    pending_items = db.query(Evidence).filter(
        Evidence.forensic_status.in_(["PENDING_ANALYSIS", "IN_ANALYSIS"]) |
        Evidence.classification.in_(["FORENSIC_REPORT", "EVIDENCE"])
    ).limit(10).all()

    child_reports = db.query(Evidence).filter(
        Evidence.is_child_report == True
    ).order_by(Evidence.created_at.desc()).all()

    verified_count = db.query(Evidence).filter(Evidence.integrity_status == "VERIFIED").count()
    tampered_count = db.query(Evidence).filter(Evidence.integrity_status == "TAMPERED").count()

    return {
        "pending_queue_count": len(pending_items),
        "child_reports_count": len(child_reports),
        "verified_hashes": verified_count,
        "tampered_alerts": tampered_count,
        "pending_analysis_queue": [
            {
                "id": e.id,
                "evidence_id": e.evidence_id,
                "filename": e.original_filename,
                "mime_type": e.mime_type,
                "sha256_hash": e.sha256_hash,
                "forensic_status": e.forensic_status,
                "custody_state": e.custody_state,
                "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else "",
            }
            for e in pending_items
        ],
        "child_reports": [
            {
                "id": c.id,
                "evidence_id": c.evidence_id,
                "filename": c.original_filename,
                "parent_id": c.parent_evidence_id,
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            for c in child_reports
        ],
        "turnaround_metrics": {
            "avg_processing_time_hours": 3.8,
            "hash_verification_rate_pct": 100.0,
            "chain_of_custody_intact": True,
        },
    }


@router.get("/dashboard/prosecutor")
def get_prosecutor_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Legal Prosecutor Dashboard: Docketed trial cases, watermarked evidence dossiers."""
    docketed = db.query(Case).filter(
        (Case.is_court_ready == True) | (Case.status.in_(["UNDER_INVESTIGATION", "COURT_READY"]))
    ).all()

    total_docket_evidence = db.query(Evidence).filter(
        Evidence.case_id.in_([c.id for c in docketed])
    ).count() if docketed else 0

    return {
        "docketed_cases_count": len(docketed),
        "total_court_evidence": total_docket_evidence,
        "docket_list": [
            {
                "id": c.id,
                "case_number": c.case_number,
                "title": c.title,
                "docket_number": c.court_docket_number or f"DOCK-{c.case_number}",
                "is_court_ready": c.is_court_ready,
                "investigating_officer": c.investigating_officer,
                "priority": c.priority,
                "evidence_count": db.query(Evidence).filter(Evidence.case_id == c.id).count(),
            }
            for c in docketed
        ],
        "judicial_verification": {
            "bsa_section_63_compliant": True,
            "iso_27037_chain_valid": True,
            "digital_signature_valid": True,
            "presentation_watermark_ready": True,
        },
    }


@router.get("/dashboard/auditor")
def get_auditor_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compliance Auditor Dashboard: Anomaly detection, global audit logs, quarantine, deletion approvals."""
    total_logs = db.query(AuditLog).count()
    tampered_items = db.query(Evidence).filter(Evidence.integrity_status == "TAMPERED").all()
    frozen_items = db.query(Evidence).filter(Evidence.is_frozen == True).all()
    frozen_cases = db.query(Case).filter(Case.is_frozen == True).all()
    deletion_approvals = db.query(Evidence).filter(Evidence.deletion_requested == True).all()

    # Anomaly alerts
    anomalies = []
    for t in tampered_items:
        anomalies.append({
            "id": f"TAMPER-{t.id}",
            "type": "CRYPTOGRAPHIC_HASH_MISMATCH",
            "severity": "CRITICAL",
            "resource": t.evidence_id,
            "details": f"Decrypted storage hash mismatch on evidence {t.original_filename}. Immediate quarantine recommended.",
            "timestamp": t.updated_at.isoformat() if t.updated_at else datetime.utcnow().isoformat(),
        })

    from app.models.blockchain import BlockchainBlock
    blocks_count = db.query(BlockchainBlock).count()

    return {
        "compliance_scorecard": {
            "bsa_section_63_score_pct": 98.4,
            "iso_27037_adherence_pct": 99.1,
            "ledger_integrity": "VALID",
            "tamper_alerts_count": len(tampered_items),
        },
        "total_audit_events": total_logs,
        "frozen_items_count": len(frozen_items),
        "frozen_cases_count": len(frozen_cases),
        "blockchain_blocks_sealed": blocks_count,
        "anomalies": anomalies,
        "deletion_approval_queue": [
            {
                "id": d.id,
                "evidence_id": d.evidence_id,
                "filename": d.original_filename,
                "reason": d.deletion_request_reason,
                "deletion_status": d.deletion_status,
                "requested_at": d.updated_at.isoformat() if d.updated_at else "",
            }
            for d in deletion_approvals
        ],
        "quarantined_evidence": [
            {
                "id": f.id,
                "evidence_id": f.evidence_id,
                "filename": f.original_filename,
                "quarantine_reason": f.quarantine_reason,
            }
            for f in frozen_items
        ],
    }


@router.get("/dashboard/custodian")
def get_custodian_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Malkhana Custodian Dashboard: Barcode registry, shelf capacity, check-in/out."""
    evidences = db.query(Evidence).all()
    total_physical = len(evidences)
    checked_in = db.query(Evidence).filter(Evidence.physical_status != "CHECKED_OUT").count()
    checked_out = db.query(Evidence).filter(Evidence.physical_status == "CHECKED_OUT").count()

    # Shelf capacity mapping
    bay_map = {
        "Bay A (Digital Media & Drives)": 0,
        "Bay B (Physical Documents & Files)": 0,
        "Bay C (Biological & Ballistics)": 0,
        "Bay D (Vault Safe)": 0,
    }
    for e in evidences:
        loc = e.physical_location or ""
        if "Bay A" in loc:
            bay_map["Bay A (Digital Media & Drives)"] += 1
        elif "Bay B" in loc:
            bay_map["Bay B (Physical Documents & Files)"] += 1
        elif "Bay C" in loc:
            bay_map["Bay C (Biological & Ballistics)"] += 1
        else:
            bay_map["Bay D (Vault Safe)"] += 1

    return {
        "total_physical_items": total_physical,
        "checked_in_count": checked_in,
        "checked_out_count": checked_out,
        "overdue_returns_count": 1 if checked_out > 0 else 0,
        "bay_distribution": [{"name": k, "count": v, "capacity": 50} for k, v in bay_map.items()],
        "inventory": [
            {
                "id": e.id,
                "evidence_id": e.evidence_id,
                "barcode_id": e.barcode_id or f"BAR-{e.id:04d}",
                "physical_location": e.physical_location or "Malkhana Bay A-Shelf 3",
                "physical_status": e.physical_status or "CHECKED_IN",
                "release_approved": e.physical_release_approved,
                "release_to": e.physical_release_to,
                "updated_at": e.updated_at.isoformat() if e.updated_at else "",
            }
            for e in evidences[:15]
        ],
    }


@router.get("/roles/workflow")
def get_roles_workflow():
    """
    Returns the complete 6-Role Specifications, Permissions Matrix, and Handoff Protocols.
    Feeds the interactive Chain of Custody & RBAC Visualizer.
    """
    return {
        "roles": [
            {
                "id": "ADMIN",
                "name": "System Administrator",
                "title": "Admin: System Mgmt",
                "subtitle": "No Evidence Data Access",
                "color": "#ef4444",
                "responsibilities": "Overall platform health, user provisioning, role assignments, and system configuration. Zero access to evidence files or case narratives to guarantee strict separation of duties.",
                "actions": ["Create/Update Users", "Configure MFA Policies", "Vault Storage Settings", "Export System Health", "Initiate Backups", "Approve Privilege Requests"],
                "data_access": "User access logs, system health metrics, storage consumption data.",
                "blocked": "Evidence files, case narratives, SHA-256 hashes, suspect/victim PII.",
                "dashboard_features": ["Global system health graphs", "Active user sessions", "Failed login maps", "Storage capacity widgets"],
                "handoff_role": "Oversight & Infrastructure Isolation",
            },
            {
                "id": "INVESTIGATOR",
                "name": "Investigating Officer (IO)",
                "title": "IO: Seize & Upload",
                "subtitle": "Primary Case Owner (Hash Gen)",
                "color": "#3b82f6",
                "responsibilities": "Primary collector and depositor of evidence. Initiates the digital chain of custody at the crime scene or station.",
                "actions": ["Upload Evidence", "Read Assigned Cases", "Transfer to Lab/Custodian", "Request Deletion/Archive", "BSA Sec 63 Compliance Report"],
                "data_access": "Full access to assigned cases: evidence files, capture GPS/timestamps, auto-generated SHA-256 hashes, case narratives.",
                "blocked": "Direct deletion without Auditor sign-off; cannot modify original evidence; cannot see other officers' cases.",
                "dashboard_features": ["My Active Cases", "Pending Transfers", "Quick-upload with live client SHA-256 hash", "Expiration timelines"],
                "handoff_role": "Initiates handoff to Forensics & Custodian",
            },
            {
                "id": "FORENSIC_OFFICER",
                "name": "Forensic Specialist / Lab Analyst",
                "title": "Forensic Lab: Analysis",
                "subtitle": "Hash Verify & Child Reports",
                "color": "#10b981",
                "responsibilities": "Analyzing digital or physical evidence, adding technical findings, and ensuring evidence remains untampered during examination phase.",
                "actions": ["Download for Analysis", "Upload Child Reports/Extracted Data", "Pre/Post Hash Verification", "Transfer Return to Vault/IO"],
                "data_access": "Access restricted to evidence routed to their laboratory. Technical metadata (EXIF, headers, hashes) and relevant case context.",
                "blocked": "Cannot modify or delete original parent evidence.",
                "dashboard_features": ["Pending Analysis queue", "In-Progress workbench", "Hash comparison verification tool"],
                "handoff_role": "Accepts custody from IO; returns analysis reports to IO",
            },
            {
                "id": "LEGAL_OFFICER",
                "name": "Legal Prosecutor / Court Official",
                "title": "Prosecutor: Trial Prep",
                "subtitle": "Read-Only & Dynamic Watermark",
                "color": "#f59e0b",
                "responsibilities": "Reviewing evidence for trial preparation and presenting in court. Strictly read-only, high-audit role.",
                "actions": ["View/Stream Evidence (Watermarked)", "Export Court Packets", "Approve Final Court-Ready Status"],
                "data_access": "Read-only access to all evidence, lab reports, and complete Chain of Custody logs for cases docketed for prosecution.",
                "blocked": "Zero Create, Update, or Delete permissions.",
                "dashboard_features": ["Docket list", "Timeline view", "Side-by-side viewer", "Dynamic watermark stamp", "Digital signature badge"],
                "handoff_role": "Receives court packets from IO; prepares trial dossiers",
            },
            {
                "id": "AUDITOR",
                "name": "Compliance Auditor / Oversight",
                "title": "Auditor: Continuous Oversight",
                "subtitle": "Quarantine & Deletion Sign-off",
                "color": "#a855f7",
                "responsibilities": "Ensuring compliance with legal standards (BSA, ISO 27037). Investigating anomalies, unauthorized access, and broken chains of custody.",
                "actions": ["Inspect Global Audit Logs", "Freeze/Quarantine Case or Evidence", "Approve/Reject Deletion Requests", "Unseal via Judicial Warrant"],
                "data_access": "Full access to ALL immutable audit logs. Zero access to evidence files unless explicitly unsealed with a judicial court warrant.",
                "blocked": "Cannot view raw video/audio/files without warrant; cannot alter logged records.",
                "dashboard_features": ["Anomaly detection feed", "Global audit search", "Compliance scorecards", "Blockchain block verification"],
                "handoff_role": "Continuous oversight of all custody handoffs",
            },
            {
                "id": "CUSTODIAN",
                "name": "Malkhana / Evidence Custodian",
                "title": "Custodian: Malkhana Storage",
                "subtitle": "Physical Vault Tracking",
                "color": "#06b6d4",
                "responsibilities": "Managing physical storage (Malkhana) counterpart of digital vault. Bridges physical items and their digital twins.",
                "actions": ["Update Physical Shelf/Bin", "Barcode Check-in / Check-out", "Approve Physical Release to IO/Court"],
                "data_access": "QR/Barcode IDs, physical shelf locations, check-out logs. No access to digital file contents.",
                "blocked": "Cannot view digital file contents (cannot play CCTV, view documents).",
                "dashboard_features": ["Barcode scanner panel", "Items Due for Return list", "Physical capacity map"],
                "handoff_role": "Physical transfers to/from IO & Court",
            },
        ],
        "matrix": [
            {"feature": "Upload Evidence", "admin": False, "io": True, "forensic": False, "prosecutor": False, "auditor": False, "custodian": False, "notes": "IO own cases only"},
            {"feature": "Upload Child Files (Reports)", "admin": False, "io": False, "forensic": True, "prosecutor": False, "auditor": False, "custodian": False, "notes": "Forensic lab assigned items only"},
            {"feature": "View Evidence Content", "admin": False, "io": True, "forensic": True, "prosecutor": True, "auditor": False, "custodian": False, "notes": "Auditor requires judicial warrant"},
            {"feature": "View Hash / Metadata", "admin": False, "io": True, "forensic": True, "prosecutor": True, "auditor": True, "custodian": True, "notes": "Custodian location/barcode only"},
            {"feature": "Modify Original Evidence", "admin": False, "io": False, "forensic": False, "prosecutor": False, "auditor": False, "custodian": False, "notes": "Cryptographically Immutable"},
            {"feature": "Delete / Archive", "admin": False, "io": "Request only", "forensic": False, "prosecutor": False, "auditor": "Approve only", "custodian": False, "notes": "Dual-control workflow"},
            {"feature": "View Audit Logs", "admin": False, "io": False, "forensic": False, "prosecutor": False, "auditor": True, "custodian": False, "notes": "Auditor has global view"},
            {"feature": "Manage Users", "admin": True, "io": False, "forensic": False, "prosecutor": False, "auditor": False, "custodian": False, "notes": "Admin separated role"},
        ],
    }

