"""Seed script — Creates demo users, cases, evidence, blockchain, audit logs"""
import os
import sys
import json
import hashlib
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, SessionLocal, engine, Base
from app.models.user import User
from app.models.case import Case
from app.models.evidence import Evidence, EvidenceVersion, CustodyEvent, EvidenceRelationship
from app.models.blockchain import BlockchainBlock
from app.models.audit import AuditLog
from app.models.ai_analysis import AIAnalysis
from app.security.auth import hash_password, compute_sha256
from app.security.auth import encrypt_file
from app.security.auth import ROLE_DEFAULT_RANK
from app.security.mfa import generate_totp_secret
from app.blockchain.ledger import create_genesis_block, add_block
from app.config import settings


def seed():
    print("EvidenceVault -- Seeding database...")


    # Drop and recreate
    Base.metadata.drop_all(bind=engine)
    init_db()

    db = SessionLocal()

    try:
        # === USERS ===
        print("👥 Creating users...")
        users_data = [
            {"email": "admin@evidencevault.local", "full_name": "Admin User", "role": "ADMIN",
             "department": "Administration", "badge_number": "ADM-001"},
            {"email": "investigator@evidencevault.local", "full_name": "Inspector Sharma", "role": "INVESTIGATOR",
             "department": "Criminal Investigation", "badge_number": "INV-201"},
            {"email": "forensic@evidencevault.local", "full_name": "Dr. Priya Forensic", "role": "FORENSIC_OFFICER",
             "department": "Forensic Science Laboratory", "badge_number": "FSL-305"},
            {"email": "legal@evidencevault.local", "full_name": "Adv. Rajan Legal", "role": "LEGAL_OFFICER",
             "department": "Legal Affairs", "badge_number": "LEG-102"},
            {"email": "auditor@evidencevault.local", "full_name": "Audit Officer Mehra", "role": "AUDITOR",
             "department": "Internal Audit", "badge_number": "AUD-401"},
            {"email": "constable@evidencevault.local", "full_name": "Constable Ravi Kumar", "role": "INVESTIGATOR",
             "department": "Traffic Police", "badge_number": "CTB-001", "rank_level": 2},
        ]
        users = []
        for u in users_data:
            user = User(
                email=u["email"],
                full_name=u["full_name"],
                hashed_password=hash_password("demo123"),
                role=u["role"],
                rank_level=u.get("rank_level") or ROLE_DEFAULT_RANK.get(u["role"], 3),
                department=u["department"],
                badge_number=u["badge_number"],
                totp_secret=generate_totp_secret(),
            )
            db.add(user)
            users.append(user)
        db.commit()
        for u in users:
            db.refresh(u)
        print(f"   ✓ Created {len(users)} users")

        # === CASES ===
        print("📁 Creating cases...")
        cases_data = [
            {"case_number": "CASE-2026-001", "title": "Missing Person Investigation — Rahul Verma",
             "description": "Investigation into the disappearance of Rahul Verma, age 32, last seen on 5th September 2026 near Connaught Place, New Delhi. Multiple witnesses have provided statements.",
             "case_type": "MISSING_PERSON", "status": "OPEN", "priority": "HIGH",
             "investigating_officer": "Inspector Sharma"},
            {"case_number": "CASE-2026-002", "title": "Financial Fraud Investigation — TechCorp Ltd",
             "description": "Investigation into alleged financial fraud involving TechCorp Ltd. Suspected embezzlement of Rs. 2.5 Crore through falsified invoices and shell companies.",
             "case_type": "FINANCIAL_FRAUD", "status": "UNDER_INVESTIGATION", "priority": "HIGH",
             "investigating_officer": "Inspector Sharma"},
            {"case_number": "CASE-2026-003", "title": "Digital Crime — Ransomware Attack on Municipal Systems",
             "description": "Investigation into ransomware attack on Delhi Municipal Corporation digital infrastructure. Critical systems compromised on 1st September 2026.",
             "case_type": "CYBER_CRIME", "status": "OPEN", "priority": "CRITICAL",
             "investigating_officer": "Inspector Sharma"},
            {"case_number": "CASE-2026-004", "title": "Hit-and-Run Fatal Collision — Ring Road Flyover",
             "description": "Investigation into fatal hit-and-run road accident on Ring Road flyover involving a speeding SUV and two-wheeler. Debris analysis, vehicle paint samples, and toll gate CCTV footage catalogued.",
             "case_type": "ACCIDENT", "status": "UNDER_INVESTIGATION", "priority": "HIGH",
             "investigating_officer": "Inspector Sharma"},
            {"case_number": "CASE-2026-005", "title": "Homicide Investigation — Sector 14 Warehouse",
             "description": "Investigation into suspicious death and homicide at Sector 14 warehouse facility. Crime scene perimeter secured; biological forensic samples, weapon ballistics, and access logs gathered.",
             "case_type": "MURDER", "status": "OPEN", "priority": "CRITICAL",
             "investigating_officer": "Inspector Sharma"},
            {"case_number": "CASE-2026-006", "title": "Commercial Break-in & Armed Robbery — Metro Plaza Jewellers",
             "description": "Armed robbery and vault breach reported at Metro Plaza retail store. Physical forced-entry forensics, vault sensor triggers, and CCTV tapes catalogued in vault.",
             "case_type": "THEFT", "status": "OPEN", "priority": "HIGH",
             "investigating_officer": "Inspector Sharma"},
        ]
        cases = []
        for c in cases_data:
            case = Case(
                case_number=c["case_number"],
                title=c["title"],
                description=c["description"],
                case_type=c["case_type"],
                status=c["status"],
                priority=c["priority"],
                investigating_officer=c["investigating_officer"],
                assigned_user_id=users[1].id,
                created_by=users[1].id,
            )
            db.add(case)
            cases.append(case)
        db.commit()
        for c in cases:
            db.refresh(c)
        print(f"   ✓ Created {len(cases)} cases")

        # === GENESIS BLOCK ===
        print("⛓️  Creating genesis block...")
        create_genesis_block(db)

        # === EVIDENCE ===
        print("📄 Creating evidence records...")
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)

        evidence_templates = [
            {"filename": "FIR_Report_Case001.pdf", "case_idx": 0, "mime": "application/pdf",
             "classification": "FIR", "content": "FIRST INFORMATION REPORT\nPolice Station: Connaught Place\nDate: 05-Sep-2026\nComplainant: Mrs. Sunita Verma\nSubject: Missing Person Report\n\nI, Mrs. Sunita Verma, wife of Mr. Rahul Verma, age 32, resident of B-42, Vasant Kunj, New Delhi, hereby report that my husband Mr. Rahul Verma has been missing since 5th September 2026. He was last seen leaving our residence at approximately 09:30 AM. He was wearing a blue shirt and black trousers. His mobile phone is switched off since 11:45 AM.\n\nInvestigating Officer: Inspector Sharma, Badge INV-201"},
            {"filename": "Witness_Statement_Arun.docx", "case_idx": 0, "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "classification": "INVESTIGATION_REPORT", "content": "WITNESS STATEMENT\nWitness: Mr. Arun Kumar\nDate: 06-Sep-2026\nLocation: Police Station Connaught Place\n\nI, Mr. Arun Kumar, shopkeeper at Shop No. 15, Palika Bazaar, state that I saw Mr. Rahul Verma near the parking area at approximately 10:15 AM on 5th September 2026. He appeared to be speaking with an unknown person near a white sedan. The unknown person was approximately 5'10\", medium build.\n\nRecorded by: Inspector Sharma"},
            {"filename": "CCTV_Screenshot_CP.png", "case_idx": 0, "mime": "image/png",
             "classification": "EVIDENCE", "content": "CCTV footage screenshot showing subject near Connaught Place parking area"},
            {"filename": "Financial_Audit_TechCorp.pdf", "case_idx": 1, "mime": "application/pdf",
             "classification": "FORENSIC_REPORT", "content": "FORENSIC FINANCIAL AUDIT REPORT\nCase: CASE-2026-002\nSubject: TechCorp Ltd Financial Investigation\nPrepared by: Dr. Priya Forensic\nDate: 08-Sep-2026\n\nExecutive Summary:\nOur forensic analysis of TechCorp Ltd financial records reveals systematic fraud through:\n1. 47 falsified invoices totaling Rs. 1.8 Crore\n2. 3 shell companies used for money laundering\n3. Unauthorized wire transfers to offshore accounts\n\nKey findings indicate that the CFO, Mr. Vikram Patel, orchestrated the scheme starting January 2025.\n\nOrganizations involved: TechCorp Ltd, GlobalPay Solutions, Meridian Exports"},
            {"filename": "Bank_Statements_Q1_2026.pdf", "case_idx": 1, "mime": "application/pdf",
             "classification": "EVIDENCE", "content": "BANK STATEMENT — CONFIDENTIAL\nAccount Holder: TechCorp Ltd\nBank: State Bank of India\nAccount No: XXXX-XXXX-4521\nPeriod: January 2026 — March 2026\n\nSuspicious transactions flagged:\n15-Jan-2026: Wire transfer Rs. 45,00,000 to GlobalPay Solutions\n28-Feb-2026: Wire transfer Rs. 32,00,000 to Meridian Exports\n15-Mar-2026: Cash withdrawal Rs. 8,00,000"},
            {"filename": "Identity_Vikram_Patel.jpg", "case_idx": 1, "mime": "image/jpeg",
             "classification": "IDENTITY_DOCUMENT", "content": "Identity document scan — Aadhaar Card of Vikram Patel"},
            {"filename": "Ransomware_Analysis_Report.pdf", "case_idx": 2, "mime": "application/pdf",
             "classification": "FORENSIC_REPORT", "content": "DIGITAL FORENSIC REPORT\nCase: CASE-2026-003\nIncident: Ransomware Attack\nDate of Incident: 01-Sep-2026\nAnalyst: Dr. Priya Forensic\n\nMalware Analysis:\nThe ransomware variant identified as 'CryptoLock-X' was deployed via spear-phishing email targeting the IT administrator. The malware encrypted 2,847 files across 12 servers.\n\nAttack Vector: Email attachment (malicious macro in Excel file)\nEncryption: AES-256\nRansom Demand: 5 Bitcoin\nC2 Server: 185.234.xx.xx (located in Eastern Europe)\n\nEmail: admin@dmc.gov.in was the initial compromise point"},
            {"filename": "Server_Logs_DMC.txt", "case_idx": 2, "mime": "text/plain",
             "classification": "EVIDENCE", "content": "SERVER ACCESS LOG — CONFIDENTIAL\nServer: DMC-PROD-01\nDate: 01-Sep-2026\n\n[08:45:22] INFO: User admin@dmc.gov.in logged in from 10.0.1.15\n[08:46:03] INFO: Email attachment opened: Q3_Budget.xlsx\n[08:46:15] WARNING: Macro execution detected\n[08:46:18] CRITICAL: Suspicious process spawned: svchost_update.exe\n[08:46:22] CRITICAL: Mass file encryption started\n[08:47:01] CRITICAL: 500 files encrypted in /data/\n[09:15:00] CRITICAL: Ransom note displayed on all terminals"},
            {"filename": "Crash_Site_Inspection_Report.pdf", "case_idx": 3, "mime": "application/pdf",
             "classification": "INVESTIGATION_REPORT", "content": "ACCIDENT INVESTIGATION & TECHNICAL RECONSTRUCTION REPORT\nCase: CASE-2026-004\nLocation: Outer Ring Road Flyover, Pillar #84\nVehicle 1: Two-wheeler (Reg: DL-04-BK-8921)\nVehicle 2 (Suspect): Dark Grey SUV (Make: Fortuner, partial plate 5821)\n\nAnalysis: Skid mark measurements indicate suspect vehicle speed exceeded 110 km/h in an 60 km/h zone. Impact angle 35 degrees rear-left collision. Metallic paint scraped onto guardrail matches factory code #GR-402.\n\nInvestigating Officer: Inspector Sharma"},
            {"filename": "Toll_Plaza_Dashcam_Clip.png", "case_idx": 3, "mime": "image/png",
             "classification": "EVIDENCE", "content": "High-definition toll plaza frame grab showing suspect dark grey SUV fleeing with front bumper damage"},
            {"filename": "Autopsy_Forensic_PostMortem.pdf", "case_idx": 4, "mime": "application/pdf",
             "classification": "FORENSIC_REPORT", "content": "MEDICO-LEGAL POST-MORTEM EXAMINATION REPORT\nCase: CASE-2026-005\nSubject: Unidentified Male (approx. age 35)\nExamining Pathologist: Dr. K. N. Rao, Forensic Science Laboratory\n\nCause of Death: Hemorrhagic shock secondary to penetrating trauma. Blunt force injury observed on occipital region. Time of death estimated between 22:00 and 01:00 hours.\nBiological samples preserved: Blood card, fingernail scrapings, DNA reference swabs."},
            {"filename": "CrimeScene_Biological_Swab_Analysis.txt", "case_idx": 4, "mime": "text/plain",
             "classification": "FORENSIC_REPORT", "content": "DNA FORENSIC LAB ANALYSIS REPORT\nSample ID: BIO-SWAB-005A\nOrigin: Door handle at Sector 14 warehouse\nAllele Profile: Mixed DNA profile detected. Major donor matches victim; minor STR donor profile catalogued in CODIS pending suspect reference cross-match."},
        ]

        evidences = []
        for i, et in enumerate(evidence_templates):
            content_bytes = et["content"].encode("utf-8")
            file_hash = compute_sha256(content_bytes)

            # Encrypt and store
            encrypted = encrypt_file(content_bytes)
            storage_name = f"demo_{i:04d}_{et['filename']}"
            storage_path = os.path.join(settings.STORAGE_DIR, storage_name)
            with open(storage_path, "wb") as f:
                f.write(encrypted)

            ev_id = f"EV-2026-{(i + 1):06d}"
            evidence = Evidence(
                evidence_id=ev_id,
                case_id=cases[et["case_idx"]].id,
                original_filename=et["filename"],
                evidence_type=et["mime"].split("/")[-1].upper()[:10],
                mime_type=et["mime"],
                file_size=len(content_bytes),
                sha256_hash=file_hash,
                encrypted_path=storage_name,
                current_custodian=users[1].full_name,
                custodian_id=users[1].id,
                classification=et["classification"],
                ai_confidence=0.85,
                integrity_status="VERIFIED",
                blockchain_status="REGISTERED",
                risk_score=10.0 if et["classification"] != "EVIDENCE" else 5.0,
                description=f"Demo evidence for {cases[et['case_idx']].case_number}",
                uploaded_by=users[1].id,
                created_at=datetime.utcnow() - timedelta(days=7 - i, hours=i * 2),
            )
            db.add(evidence)
            evidences.append(evidence)

        db.commit()
        for ev in evidences:
            db.refresh(ev)
        print(f"   ✓ Created {len(evidences)} evidence records")

        # === VERSIONS ===
        print("📋 Creating version records...")
        for ev in evidences:
            version = EvidenceVersion(
                evidence_id=ev.id,
                version_number=1,
                sha256_hash=ev.sha256_hash,
                encrypted_path=ev.encrypted_path,
                file_size=ev.file_size,
                action="UPLOADED",
                reason="Initial upload",
                actor_id=users[1].id,
                actor_name=users[1].full_name,
                created_at=ev.created_at,
            )
            db.add(version)
        db.commit()

        # === CUSTODY EVENTS ===
        print("🔗 Creating chain of custody events...")
        custody_templates = [
            (0, 1, "EVIDENCE_UPLOADED", "Evidence uploaded to system"),
            (0, 1, "ANALYSIS_STARTED", "AI analysis initiated"),
            (0, 2, "CUSTODY_TRANSFERRED", "Transferred to Forensic Officer for analysis"),
            (0, 2, "ANALYSIS_COMPLETED", "Forensic analysis completed"),
            (0, 3, "CUSTODY_TRANSFERRED", "Transferred to Legal Officer for review"),
            (1, 1, "EVIDENCE_UPLOADED", "Witness statement recorded"),
            (1, 1, "ANALYSIS_STARTED", "Document analysis initiated"),
            (3, 1, "EVIDENCE_UPLOADED", "Financial audit report uploaded"),
            (3, 2, "CUSTODY_TRANSFERRED", "Transferred to Forensic Lab"),
            (3, 2, "ANALYSIS_COMPLETED", "Forensic financial analysis completed"),
            (6, 1, "EVIDENCE_UPLOADED", "Ransomware analysis report uploaded"),
            (6, 2, "CUSTODY_TRANSFERRED", "Transferred to Forensic Lab"),
            (6, 2, "ANALYSIS_COMPLETED", "Digital forensic analysis completed"),
            (6, 3, "CUSTODY_TRANSFERRED", "Transferred to Legal for prosecution"),
        ]

        for idx, (ev_idx, user_idx, action, notes) in enumerate(custody_templates):
            if ev_idx < len(evidences):
                ce = CustodyEvent(
                    evidence_id=evidences[ev_idx].id,
                    actor_id=users[user_idx].id,
                    actor_name=users[user_idx].full_name,
                    actor_role=users[user_idx].role,
                    action=action,
                    location="Digital Evidence Lab" if user_idx == 2 else "Investigation Office",
                    evidence_condition="INTACT",
                    notes=notes,
                    sha256_hash=evidences[ev_idx].sha256_hash,
                    timestamp=datetime.utcnow() - timedelta(days=6, hours=-idx),
                )
                db.add(ce)

        # Update custody counts
        for ev in evidences:
            ev.custody_count = len([c for c in custody_templates if c[0] == evidences.index(ev)])
        db.commit()

        # === AI ANALYSES ===
        print("🤖 Creating AI analysis records...")
        from app.ai.pipeline import classify_document, extract_entities, detect_anomalies, generate_summary, calculate_risk_score

        for i, ev in enumerate(evidences):
            template = evidence_templates[i]
            text = template["content"]

            doc_type, confidence = classify_document(text, ev.original_filename)
            entities = extract_entities(text)
            anomalies = detect_anomalies({"file_size": ev.file_size, "current_version": 1})
            risk_score, risk_level = calculate_risk_score(anomalies)
            summary = generate_summary(text, doc_type, entities)

            from collections import Counter
            entity_counts = Counter(e["type"] for e in entities)

            ai = AIAnalysis(
                evidence_id=ev.id,
                document_type=doc_type,
                confidence=confidence,
                extracted_text=text[:5000],
                summary=summary,
                entities_json=json.dumps(entities),
                risk_score=risk_score,
                risk_level=risk_level,
                anomalies_json=json.dumps(anomalies),
                key_persons_count=entity_counts.get("PERSON", 0),
                locations_count=entity_counts.get("LOCATION", 0),
                dates_count=entity_counts.get("DATE", 0),
                case_references_count=entity_counts.get("CASE_NUMBER", 0),
                classification_method="keyword",
            )
            db.add(ai)

            # Update evidence with AI results
            ev.classification = doc_type
            ev.ai_confidence = confidence
            ev.risk_score = risk_score

        db.commit()

        # === BLOCKCHAIN BLOCKS ===
        print("⛓️  Creating blockchain records...")
        for ev in evidences:
            add_block(db, ev.evidence_id, ev.sha256_hash, "EVIDENCE_CREATED",
                      users[1].full_name, users[1].role,
                      {"case": cases[evidence_templates[evidences.index(ev)]["case_idx"]].case_number,
                       "filename": ev.original_filename})

        # Add some additional blockchain events
        add_block(db, evidences[0].evidence_id, evidences[0].sha256_hash,
                  "CUSTODY_TRANSFER", users[1].full_name, "INVESTIGATOR",
                  {"to": users[2].full_name})
        add_block(db, evidences[0].evidence_id, evidences[0].sha256_hash,
                  "EVIDENCE_VERIFIED", users[2].full_name, "FORENSIC_OFFICER", {"result": "VERIFIED"})
        add_block(db, evidences[3].evidence_id, evidences[3].sha256_hash,
                  "CUSTODY_TRANSFER", users[1].full_name, "INVESTIGATOR",
                  {"to": users[2].full_name})

        # === EVIDENCE RELATIONSHIPS ===
        print("🔗 Creating evidence relationships...")
        for i, ev in enumerate(evidences):
            rel = EvidenceRelationship(
                source_evidence_id=ev.id,
                target_case_id=cases[evidence_templates[i]["case_idx"]].id,
                relationship_type="BELONGS_TO",
                label="Belongs to",
                node_type="CASE",
                node_label=cases[evidence_templates[i]["case_idx"]].case_number,
            )
            db.add(rel)

        # Some cross-evidence relationships
        if len(evidences) >= 3:
            db.add(EvidenceRelationship(
                source_evidence_id=evidences[0].id,
                target_evidence_id=evidences[1].id,
                relationship_type="REFERENCES",
                label="Referenced in witness statement",
                node_type="EVIDENCE",
                node_label=evidences[1].evidence_id,
            ))
            db.add(EvidenceRelationship(
                source_evidence_id=evidences[0].id,
                target_evidence_id=evidences[2].id,
                relationship_type="RELATED_TO",
                label="CCTV corroborates FIR",
                node_type="EVIDENCE",
                node_label=evidences[2].evidence_id,
            ))
        if len(evidences) >= 6:
            db.add(EvidenceRelationship(
                source_evidence_id=evidences[3].id,
                target_evidence_id=evidences[4].id,
                relationship_type="REFERENCES",
                label="Audit references bank statements",
                node_type="EVIDENCE",
                node_label=evidences[4].evidence_id,
            ))

        db.commit()

        # === AUDIT LOGS (Operational events only; LOGIN events are captured live) ===
        print("📝 Creating audit logs...")
        audit_actions = [
            ("CASE_CREATED", users[1], "CASE", "CASE-2026-001", "Missing Person case created"),
            ("CASE_CREATED", users[1], "CASE", "CASE-2026-002", "Financial Fraud case created"),
            ("CASE_CREATED", users[1], "CASE", "CASE-2026-003", "Cyber Crime case created"),
            ("EVIDENCE_UPLOADED", users[1], "EVIDENCE", "EV-2026-000001", "FIR uploaded"),
            ("EVIDENCE_UPLOADED", users[1], "EVIDENCE", "EV-2026-000002", "Witness statement uploaded"),
            ("EVIDENCE_UPLOADED", users[1], "EVIDENCE", "EV-2026-000003", "CCTV screenshot uploaded"),
            ("AI_ANALYSIS", users[1], "EVIDENCE", "EV-2026-000001", "AI analysis completed"),
            ("CUSTODY_TRANSFERRED", users[1], "EVIDENCE", "EV-2026-000001", "Transferred to Forensic"),
            ("EVIDENCE_VERIFIED", users[2], "EVIDENCE", "EV-2026-000001", "Evidence integrity verified"),
            ("BLOCKCHAIN_VERIFIED", users[4], "BLOCKCHAIN", "", "Full chain verification"),
            ("EVIDENCE_UPLOADED", users[1], "EVIDENCE", "EV-2026-000004", "Financial audit uploaded"),
            ("EVIDENCE_UPLOADED", users[1], "EVIDENCE", "EV-2026-000007", "Ransomware report uploaded"),
            ("REPORT_GENERATED", users[3], "EVIDENCE", "EV-2026-000001", "Evidence report generated"),
        ]

        for i, (action, user, res_type, res_id, details) in enumerate(audit_actions):
            log = AuditLog(
                user_id=user.id,
                user_email=user.email,
                role=user.role,
                action=action,
                resource_type=res_type,
                resource_id=res_id,
                ip_address="127.0.0.1",
                status="SUCCESS",
                details=details,
                timestamp=datetime.utcnow() - timedelta(days=7, hours=-i * 3),
            )
            db.add(log)
        db.commit()

        print()
        print("=" * 60)
        print("✅ SEED COMPLETE!")
        print("=" * 60)
        print()
        print("Demo Login Credentials:")
        print("-" * 40)
        print("  Admin:        admin@evidencevault.local / demo123")
        print("  Investigator: investigator@evidencevault.local / demo123")
        print("  Forensic:     forensic@evidencevault.local / demo123")
        print("  Legal:        legal@evidencevault.local / demo123")
        print("  Auditor:      auditor@evidencevault.local / demo123")
        print("  Constable:    constable@evidencevault.local / demo123 (rank 2 — scoped view)")
        print()
        print(f"  Users: {len(users)}")
        print(f"  Cases: {len(cases)}")
        print(f"  Evidence: {len(evidences)}")
        print(f"  Blockchain blocks: {db.query(BlockchainBlock).count()}")
        print(f"  Audit logs: {db.query(AuditLog).count()}")
        print()
        print("Run the server:")
        print("  uvicorn app.main:app --reload")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    seed()
