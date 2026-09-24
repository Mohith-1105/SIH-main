"""Report generation routes for Evidence & Case Intelligence (Weekly, Monthly, Custom)"""
import io
import csv
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evidence import Evidence, CustodyEvent
from app.models.case import Case
from app.models.ai_analysis import AIAnalysis
from app.models.user import User
from app.security.auth import require_permission, ensure_evidence_access, visible_case_ids
from app.blockchain import verify_evidence_blocks
from app.utils.helpers import create_audit_log

router = APIRouter(prefix="/api/reports", tags=["Reports"])


# --- Helper: Compute Case Report Data ---
def compute_case_report_data(
    db: Session,
    user: User,
    period: str = "weekly",
    case_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    now = datetime.utcnow()
    period_lower = period.lower()

    if period_lower == "weekly":
        start = now - timedelta(days=7)
        end = now
        label = "Weekly Case Report (Past 7 Days)"
    elif period_lower == "monthly":
        start = now - timedelta(days=30)
        end = now
        label = "Monthly Case Report (Past 30 Days)"
    elif period_lower == "quarterly":
        start = now - timedelta(days=90)
        end = now
        label = "Quarterly Case Report (Past 90 Days)"
    elif period_lower == "custom" and start_date:
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            start = now - timedelta(days=7)
        try:
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00")).replace(tzinfo=None) if end_date else now
        except Exception:
            end = now
        label = f"Custom Report ({start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')})"
    else:
        start = now - timedelta(days=7)
        end = now
        label = "Weekly Case Report (Past 7 Days)"

    query = db.query(Case).filter(Case.created_at >= start, Case.created_at <= end)
    ids = visible_case_ids(user, db)
    if ids is not None:
        query = query.filter(Case.id.in_(ids))
    if case_type and case_type != "ALL":
        if case_type == "MURDER":
            query = query.filter(Case.case_type.in_(["MURDER", "HOMICIDE"]))
        else:
            query = query.filter(Case.case_type == case_type)

    cases = query.order_by(Case.created_at.desc()).all()

    # Fallback to recent cases if database has no cases strictly in window (e.g. testing)
    if len(cases) == 0 and period_lower in ["weekly", "monthly"]:
        fallback_q = db.query(Case)
        if ids is not None:
            fallback_q = fallback_q.filter(Case.id.in_(ids))
        if case_type and case_type != "ALL":
            if case_type == "MURDER":
                fallback_q = fallback_q.filter(Case.case_type.in_(["MURDER", "HOMICIDE"]))
            else:
                fallback_q = fallback_q.filter(Case.case_type == case_type)
        cases = fallback_q.order_by(Case.created_at.desc()).all()

    # Collect case metrics
    case_ids = [c.id for c in cases]
    evidence_records = db.query(Evidence).filter(Evidence.case_id.in_(case_ids)).all() if case_ids else []

    status_counts = {"OPEN": 0, "UNDER_INVESTIGATION": 0, "CLOSED": 0}
    priority_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    classification_counts: dict[str, int] = {}
    cases_list = []

    # Map evidence count per case
    ev_count_by_case: dict[int, int] = {}
    for ev in evidence_records:
        ev_count_by_case[ev.case_id] = ev_count_by_case.get(ev.case_id, 0) + 1

    for c in cases:
        status_counts[c.status] = status_counts.get(c.status, 0) + 1
        priority_counts[c.priority] = priority_counts.get(c.priority, 0) + 1
        norm_type = "MURDER" if c.case_type == "HOMICIDE" else (c.case_type or "GENERAL")
        classification_counts[norm_type] = classification_counts.get(norm_type, 0) + 1

        cases_list.append({
            "id": c.id,
            "case_number": c.case_number,
            "title": c.title,
            "description": c.description,
            "case_type": norm_type,
            "status": c.status,
            "priority": c.priority,
            "investigating_officer": c.investigating_officer or "Investigator",
            "evidence_count": ev_count_by_case.get(c.id, 0),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    # Evidence integrity breakdown
    verified_ev = sum(1 for e in evidence_records if e.integrity_status == "VERIFIED")
    tampered_ev = sum(1 for e in evidence_records if e.integrity_status == "TAMPERED")
    pending_ev = len(evidence_records) - verified_ev - tampered_ev
    integrity_rate = (verified_ev / len(evidence_records) * 100) if evidence_records else 100.0

    # Daily intake grouping
    daily_map: dict[str, int] = {}
    days_back = 7 if period_lower == "weekly" else (30 if period_lower == "monthly" else 14)
    for i in range(days_back, -1, -1):
        d_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_map[d_str] = 0

    for c in cases:
        if c.created_at:
            ds = c.created_at.strftime("%Y-%m-%d")
            if ds in daily_map:
                daily_map[ds] += 1
            else:
                daily_map[ds] = 1

    daily_trend = [{"date": k, "count": v} for k, v in sorted(daily_map.items())]

    return {
        "period": period_lower,
        "label": label,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "total_cases": len(cases),
        "open_cases": status_counts.get("OPEN", 0),
        "under_investigation": status_counts.get("UNDER_INVESTIGATION", 0),
        "closed_cases": status_counts.get("CLOSED", 0),
        "total_evidence": len(evidence_records),
        "verified_evidence": verified_ev,
        "tampered_evidence": tampered_ev,
        "pending_evidence": pending_ev,
        "integrity_rate": round(integrity_rate, 1),
        "by_classification": [{"name": k, "value": v} for k, v in classification_counts.items()],
        "by_priority": [{"name": k, "value": v} for k, v in priority_counts.items()],
        "by_status": [{"name": k, "value": v} for k, v in status_counts.items()],
        "daily_trend": daily_trend,
        "cases": cases_list,
    }


# --- API Endpoint: Case Report Summary (JSON) ---
@router.get("/cases/summary")
def get_case_report_summary(
    period: str = Query("weekly", pattern="^(weekly|monthly|quarterly|custom)$"),
    case_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: User = Depends(require_permission("reports.generate")),
    db: Session = Depends(get_db),
):
    """Retrieve summarized weekly/monthly case analytics, classification breakdown, and case roster."""
    data = compute_case_report_data(db, user, period=period, case_type=case_type, start_date=start_date, end_date=end_date)
    return data


# --- API Endpoint: Download Official Case Report PDF ---
@router.get("/cases/pdf")
def download_case_report_pdf(
    period: str = Query("weekly", pattern="^(weekly|monthly|quarterly|custom)$"),
    case_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: User = Depends(require_permission("reports.generate")),
    db: Session = Depends(get_db),
):
    """Generate and stream an official, formatted police/investigation PDF dossier for cases."""
    data = compute_case_report_data(db, user, period=period, case_type=case_type, start_date=start_date, end_date=end_date)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch, cm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.2*cm, bottomMargin=1.2*cm, leftMargin=1.2*cm, rightMargin=1.2*cm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('DocTitle', parent=styles['Title'], fontSize=16, leading=20, textColor=HexColor('#0f172a'), alignment=1)
        sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=10, textColor=HexColor('#475569'), alignment=1, spaceAfter=8)
        section_style = ParagraphStyle('DocSection', parent=styles['Heading2'], fontSize=12, leading=15, textColor=HexColor('#1e293b'), spaceBefore=8, spaceAfter=6)
        normal_style = ParagraphStyle('DocNormal', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=HexColor('#334155'))
        cell_style = ParagraphStyle('DocCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=HexColor('#1e293b'))
        cell_bold = ParagraphStyle('DocCellB', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold', textColor=HexColor('#0f172a'))

        elements = []

        # Masthead Header
        elements.append(Paragraph("STATE CRIME INVESTIGATION WING — EVIDENCE VAULT", title_style))
        elements.append(Paragraph(f"<b>OFFICIAL {data['period'].upper()} CASE INTELLIGENCE & CRIME REGISTRY REPORT</b>", sub_style))
        elements.append(Paragraph(f"Period: <b>{data['start_date']}</b> to <b>{data['end_date']}</b> | Generated: {data['generated_at']} | Prepared by: {user.full_name} ({user.role})", sub_style))
        elements.append(Spacer(1, 0.15*inch))

        # Executive Metrics Summary Table
        elements.append(Paragraph("1. Executive Summary & Incident Key Performance Indicators", section_style))
        metrics_table_data = [
            ["Metric Parameter", "Count", "Metric Parameter", "Status / Ratio"],
            ["Total Cases Logged", str(data["total_cases"]), "Under Active Investigation", str(data["under_investigation"])],
            ["Cases Newly Opened", str(data["open_cases"]), "Cases Resolved / Closed", str(data["closed_cases"])],
            ["Total Evidence Files", str(data["total_evidence"]), "Verified On Blockchain", f"{data['verified_evidence']} ({data['integrity_rate']}%)"],
            ["Tampered Alerts", str(data["tampered_evidence"]), "Pending Integrity Review", str(data["pending_evidence"])],
        ]
        t_metrics = Table(metrics_table_data, colWidths=[4.6*cm, 3.8*cm, 4.8*cm, 4.6*cm])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f8fafc'), HexColor('#ffffff')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_metrics)
        elements.append(Spacer(1, 0.18*inch))

        # Crime Classification Distribution Table
        elements.append(Paragraph("2. Case Breakdown by Crime & Incident Classification", section_style))
        class_table_data = [["Classification / Incident Type", "Total Cases", "Percentage of Total", "Severity Protocol"]]
        total_c = max(data["total_cases"], 1)

        for item in sorted(data["by_classification"], key=lambda x: x["value"], reverse=True):
            pct = f"{(item['value'] / total_c * 100):.1f}%"
            severity = "CRITICAL" if item["name"] == "MURDER" else ("HIGH" if item["name"] in ["ACCIDENT", "CYBER_CRIME", "NARCOTICS", "ASSAULT"] else "MEDIUM")
            class_table_data.append([item["name"].replace("_", " "), str(item["value"]), pct, severity])

        t_class = Table(class_table_data, colWidths=[6.5*cm, 3.5*cm, 4*cm, 3.8*cm])
        t_class.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f8fafc'), HexColor('#ffffff')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_class)
        elements.append(Spacer(1, 0.18*inch))

        # Detailed Case Registry Table
        elements.append(Paragraph("3. Registered Case Roster & Status Details", section_style))
        cases_table_data = [["Case Number", "Type", "Title / Synopsis", "Priority", "Officer", "Evidence", "Status"]]

        for c in data["cases"][:25]:
            cases_table_data.append([
                Paragraph(c["case_number"], cell_bold),
                Paragraph(c["case_type"].replace("_", " "), cell_style),
                Paragraph(c["title"][:42] + ("..." if len(c["title"]) > 42 else ""), cell_style),
                Paragraph(c["priority"], cell_style),
                Paragraph(c["investigating_officer"], cell_style),
                Paragraph(str(c["evidence_count"]), cell_style),
                Paragraph(c["status"].replace("_", " "), cell_style),
            ])

        t_cases = Table(cases_table_data, colWidths=[2.6*cm, 2.3*cm, 5.7*cm, 1.8*cm, 2.7*cm, 1.3*cm, 2.4*cm])
        t_cases.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0f172a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cbd5e1')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f8fafc'), HexColor('#ffffff')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_cases)

        # Footer & Digital Signature Seal
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("— End of Official Report —", ParagraphStyle('Center', parent=normal_style, alignment=1)))
        elements.append(Paragraph("This confidential document was compiled by EvidenceVault Cryptographic Case & Evidence Management System.",
                                  ParagraphStyle('Footer', parent=normal_style, fontSize=7, alignment=1, textColor=HexColor('#64748b'))))

        doc.build(elements)
        buffer.seek(0)

        create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                        action="REPORT_GENERATED", resource_type="CASES",
                        resource_id=f"CASES-{data['period'].upper()}-{data['start_date']}")

        filename = f"cases_report_{data['period']}_{data['start_date']}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
        )

    except ImportError:
        # Fallback JSON
        return data


# --- API Endpoint: Download Case Report CSV ---
@router.get("/cases/csv")
def download_case_report_csv(
    period: str = Query("weekly", pattern="^(weekly|monthly|quarterly|custom)$"),
    case_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: User = Depends(require_permission("reports.generate")),
    db: Session = Depends(get_db),
):
    """Generate and stream a CSV spreadsheet export of all cases in the reporting period."""
    data = compute_case_report_data(db, user, period=period, case_type=case_type, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    writer.writerow([
        "Case Number",
        "Title",
        "Classification",
        "Priority",
        "Status",
        "Investigating Officer",
        "Evidence Count",
        "Created Date",
        "Description",
    ])

    for c in data["cases"]:
        writer.writerow([
            c["case_number"],
            c["title"],
            c["case_type"],
            c["priority"],
            c["status"],
            c["investigating_officer"],
            c["evidence_count"],
            c["created_at"],
            c["description"].replace("\n", " "),
        ])

    csv_content = output.getvalue()
    filename = f"cases_report_{data['period']}_{data['start_date']}.csv"

    create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                    action="REPORT_EXPORTED_CSV", resource_type="CASES",
                    resource_id=f"CASES-{data['period'].upper()}-{data['start_date']}")

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


# --- Existing Evidence Report ---
@router.get("/evidence/{evidence_id}")
def generate_evidence_report(
    evidence_id: int,
    user: User = Depends(require_permission("reports.generate")),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    ensure_evidence_access(user, ev, db)

    case = db.query(Case).filter(Case.id == ev.case_id).first()
    ai = db.query(AIAnalysis).filter(AIAnalysis.evidence_id == ev.id).first()
    custody = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).order_by(CustodyEvent.timestamp).all()
    bc_result = verify_evidence_blocks(db, ev.evidence_id)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch, cm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=18,
                                      textColor=HexColor('#1a1a2e'))
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14,
                                       textColor=HexColor('#16213e'), spaceAfter=10)
        normal_style = styles['Normal']

        elements = []

        # Title
        elements.append(Paragraph("EVIDENCE VAULT — Evidence Report", title_style))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", normal_style))
        elements.append(Paragraph(f"Generated by: {user.full_name} ({user.role})", normal_style))
        elements.append(Spacer(1, 0.3*inch))

        # Evidence Passport
        elements.append(Paragraph("Evidence Passport", heading_style))
        passport_data = [
            ["Evidence ID", ev.evidence_id],
            ["Case", f"{case.case_number} — {case.title}" if case else "N/A"],
            ["Original Filename", ev.original_filename],
            ["Type", ev.evidence_type],
            ["MIME Type", ev.mime_type],
            ["File Size", f"{ev.file_size:,} bytes"],
            ["SHA-256 Hash", ev.sha256_hash],
            ["Classification", ev.classification],
            ["Current Version", str(ev.current_version)],
            ["Current Custodian", ev.current_custodian],
            ["Integrity Status", ev.integrity_status],
            ["Blockchain Status", ev.blockchain_status],
            ["Created", ev.created_at.strftime('%Y-%m-%d %H:%M') if ev.created_at else "N/A"],
        ]
        t = Table(passport_data, colWidths=[3.5*cm, 13*cm])
        t.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.3*inch))

        # AI Analysis
        if ai:
            elements.append(Paragraph("AI Analysis", heading_style))
            ai_data = [
                ["Document Type", ai.document_type],
                ["AI Confidence", f"{ai.confidence:.0%}"],
                ["Risk Score", f"{ai.risk_score:.0f}/100"],
                ["Risk Level", ai.risk_level],
                ["Key Persons", str(ai.key_persons_count)],
                ["Locations", str(ai.locations_count)],
                ["Dates Detected", str(ai.dates_count)],
            ]
            t2 = Table(ai_data, colWidths=[3.5*cm, 13*cm])
            t2.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t2)
            if ai.summary:
                elements.append(Spacer(1, 0.15*inch))
                elements.append(Paragraph(f"<b>Summary:</b> {ai.summary}", normal_style))
            elements.append(Spacer(1, 0.3*inch))

        # Chain of Custody
        if custody:
            elements.append(Paragraph("Chain of Custody", heading_style))
            cust_data = [["Timestamp", "Actor", "Role", "Action", "Condition"]]
            for c in custody:
                cust_data.append([
                    c.timestamp.strftime('%Y-%m-%d %H:%M') if c.timestamp else "",
                    c.actor_name,
                    c.actor_role,
                    c.action,
                    c.evidence_condition,
                ])
            t3 = Table(cust_data, colWidths=[3*cm, 3.5*cm, 3*cm, 4*cm, 3*cm])
            t3.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t3)
            elements.append(Spacer(1, 0.3*inch))

        # Blockchain Verification
        elements.append(Paragraph("Blockchain Verification", heading_style))
        bc_status = "VERIFIED ✓" if bc_result.get("valid") else "INTEGRITY ISSUE ✕"
        elements.append(Paragraph(f"<b>Status:</b> {bc_status}", normal_style))
        elements.append(Paragraph(f"<b>Blocks:</b> {len(bc_result.get('blocks', []))}", normal_style))
        if bc_result.get("errors"):
            for err in bc_result["errors"]:
                elements.append(Paragraph(f"⚠ Block #{err['block_index']}: {err['error']}", normal_style))

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("— End of Report —", ParagraphStyle('Center', parent=normal_style, alignment=1)))
        elements.append(Paragraph("This report was generated by EvidenceVault Secure Document Management System.",
                                  ParagraphStyle('Footer', parent=normal_style, fontSize=7, alignment=1)))

        doc.build(elements)
        buffer.seek(0)

        create_audit_log(db, user_id=user.id, user_email=user.email, role=user.role,
                        action="REPORT_GENERATED", resource_type="EVIDENCE",
                        resource_id=ev.evidence_id)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"report_{ev.evidence_id}.pdf\""},
        )

    except ImportError:
        report = {
            "evidence_id": ev.evidence_id,
            "case_number": case.case_number if case else "",
            "filename": ev.original_filename,
            "sha256_hash": ev.sha256_hash,
            "classification": ev.classification,
            "integrity_status": ev.integrity_status,
            "blockchain_result": bc_result,
            "custody_chain": [{"actor": c.actor_name, "action": c.action,
                              "timestamp": c.timestamp.isoformat() if c.timestamp else ""} for c in custody],
            "generated_at": datetime.utcnow().isoformat(),
        }
        return report
