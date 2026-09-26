"""Seed script — Creates demo users, cases, evidence, blockchain, audit logs"""
import os
import sys
import json
import hashlib
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.database import init_db, SessionLocal, engine, Base
from app.models.user import User
from app.models.case import Case
from app.models.evidence import Evidence, EvidenceVersion, CustodyEvent, EvidenceRelationship
from app.models.blockchain import BlockchainBlock
from app.models.audit import AuditLog
from app.models.ai_analysis import AIAnalysis
from app.security.auth import hash_password, compute_sha256
from app.security.auth import encrypt_file
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
        print("👥 Loading seeded users...")
        users = db.query(User).all()
        print(f"   ✓ Loaded {len(users)} users ({', '.join(u.email for u in users)})")

        # === CASES (ALL 9 CASE TYPES FROM SECTION 15) ===
        print("📁 Creating cases for all 9 Case Types...")
        cases_data = [
            {
                "case_number": "CASE-2026-001",
                "title": "Missing Person Investigation — Rahul Verma",
                "description": "Investigation into the disappearance of Rahul Verma, age 32, last seen on 5th September 2026 near Connaught Place, New Delhi. Multiple witnesses have provided statements.",
                "case_type": "MISSING_PERSON", "status": "OPEN", "priority": "HIGH",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 9, 5, 9, 30),
                "incident_location": "Connaught Place Inner Circle, New Delhi",
                "reporting_authority": "Parliament Street Police Station",
                "assigned_team": "Missing Persons Unit Alpha",
                "persons_involved": "Rahul Verma (Missing Subject), Sunita Verma (Spouse/Complainant)",
                "jurisdiction": "New Delhi Central District",
                "retention_category": "EXTENDED_10YR",
                "confidentiality_level": "RESTRICTED",
            },
            {
                "case_number": "CASE-2026-002",
                "title": "Financial Fraud Investigation — TechCorp Ltd",
                "description": "Investigation into alleged financial fraud involving TechCorp Ltd. Suspected embezzlement of Rs. 2.5 Crore through falsified invoices and shell companies.",
                "case_type": "FINANCIAL_FRAUD", "status": "UNDER_INVESTIGATION", "priority": "HIGH",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 8, 14, 11, 0),
                "incident_location": "Barakhamba Road Financial District, New Delhi",
                "reporting_authority": "Economic Offences Wing (EOW)",
                "assigned_team": "Financial Crime Squad 3",
                "persons_involved": "TechCorp Ltd, Vikram Patel (CFO, Prime Suspect), GlobalPay Solutions",
                "jurisdiction": "Delhi High Court Commercial Division",
                "retention_category": "STANDARD_5YR",
                "confidentiality_level": "CONFIDENTIAL",
            },
            {
                "case_number": "CASE-2026-003",
                "title": "Digital Crime — Ransomware Attack on Municipal Systems",
                "description": "Investigation into ransomware attack on Delhi Municipal Corporation digital infrastructure. Critical systems compromised on 1st September 2026.",
                "case_type": "CYBER_CRIME", "status": "UNDER_INVESTIGATION", "priority": "CRITICAL",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 9, 1, 8, 45),
                "incident_location": "Civic Centre Server Farm, Minto Road, New Delhi",
                "reporting_authority": "Cyber Crime Cell Special Cell",
                "assigned_team": "CERT-In Cyber Forensics Incident Response",
                "persons_involved": "DMC Systems Admin, CryptoLock-X Threat Actor Group",
                "jurisdiction": "Cyber Crime Appellate Tribunal / NCT Cyber Court",
                "retention_category": "STATUTORY_PERMANENT",
                "confidentiality_level": "RESTRICTED",
            },
            {
                "case_number": "CASE-2026-004",
                "title": "Hit-and-Run Fatal Collision — Ring Road Flyover",
                "description": "Investigation into fatal hit-and-run road accident on Ring Road flyover involving a speeding SUV and two-wheeler. Debris analysis, vehicle paint samples, and toll gate CCTV footage catalogued.",
                "case_type": "ACCIDENT", "status": "UNDER_INVESTIGATION", "priority": "HIGH",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 9, 10, 23, 15),
                "incident_location": "Outer Ring Road Flyover, Pillar #84, New Delhi",
                "reporting_authority": "Delhi Traffic Police HQ",
                "assigned_team": "Crash Investigation & Reconstruction Team",
                "persons_involved": "Rajesh Meena (Victim/Deceased), Unknown SUV Driver",
                "jurisdiction": "Saket District Court Traffic Bench",
                "retention_category": "STANDARD_5YR",
                "confidentiality_level": "CONFIDENTIAL",
            },
            {
                "case_number": "CASE-2026-005",
                "title": "Homicide Investigation — Sector 14 Warehouse",
                "description": "Investigation into suspicious death and homicide at Sector 14 warehouse facility. Crime scene perimeter secured; biological forensic samples, weapon ballistics, and access logs gathered.",
                "case_type": "MURDER", "status": "COURT_READY", "priority": "CRITICAL",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 9, 12, 22, 30),
                "incident_location": "Plot 42, Sector 14 Industrial Area, Rohini, Delhi",
                "reporting_authority": "Rohini District Police Station",
                "assigned_team": "Homicide Task Force Central",
                "persons_involved": "Vipin Anand (Deceased Victim), Manoj Tyagi (Arrested Suspect)",
                "jurisdiction": "Sessions Court Rohini / High Court of Delhi",
                "retention_category": "STATUTORY_PERMANENT",
                "confidentiality_level": "RESTRICTED",
            },
            {
                "case_number": "CASE-2026-006",
                "title": "Commercial Break-in & Armed Robbery — Metro Plaza Jewellers",
                "description": "Armed robbery and vault breach reported at Metro Plaza retail store. Physical forced-entry forensics, vault sensor triggers, and CCTV tapes catalogued in vault.",
                "case_type": "THEFT", "status": "OPEN", "priority": "HIGH",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 9, 15, 3, 20),
                "incident_location": "Shop 104, Metro Plaza Complex, Netaji Subhash Place, Delhi",
                "reporting_authority": "Subhash Place Police Station",
                "assigned_team": "Robbery & Dacoity Squad",
                "persons_involved": "Kailash Jewellers (Complainant), 3 Masked Perpetrators",
                "jurisdiction": "Tis Hazari District Court",
                "retention_category": "STANDARD_5YR",
                "confidentiality_level": "CONFIDENTIAL",
            },
            {
                "case_number": "CASE-2026-007",
                "title": "Inter-State Controlled Substance Seizure — Cargo Terminal",
                "description": "Seizure of suspected narcotics consignment concealed within air cargo freight. Chemical identification, lab chromatography testing, and chain-of-custody sealing required under NDPS Act.",
                "case_type": "NARCOTICS", "status": "UNDER_INVESTIGATION", "priority": "CRITICAL",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 9, 18, 14, 0),
                "incident_location": "Air Cargo Freight Terminal 3, IGI Airport, New Delhi",
                "reporting_authority": "Narcotics Control Bureau (NCB) Delhi Zonal Unit",
                "assigned_team": "NDPS Interdiction Taskforce",
                "persons_involved": "Consignment #NCB-9921, Consignee: Apex Logistics",
                "jurisdiction": "Special NDPS Court Patiala House",
                "retention_category": "STATUTORY_PERMANENT",
                "confidentiality_level": "RESTRICTED",
            },
            {
                "case_number": "CASE-2026-008",
                "title": "Aggravated Assault & Grievous Hurt — Green Park",
                "description": "Investigation into grievous physical assault with bludgeoning weapon outside commercial establishment. Medico-legal injury certification, blood-spatter clothing, and surveillance clips registered.",
                "case_type": "ASSAULT", "status": "UNDER_INVESTIGATION", "priority": "HIGH",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 9, 20, 21, 45),
                "incident_location": "Main Market Commercial Strip, Green Park, New Delhi",
                "reporting_authority": "Safdarjung Enclave Police Station",
                "assigned_team": "Violent Crimes Unit South",
                "persons_involved": "Karan Singhal (Injured Complainant), Rohit Bakshi (Accused)",
                "jurisdiction": "Saket District Court Criminal Division",
                "retention_category": "STANDARD_5YR",
                "confidentiality_level": "CONFIDENTIAL",
            },
            {
                "case_number": "CASE-2026-009",
                "title": "Special Statutory Audit & Cross-Agency Inquiry — Port Customs",
                "description": "General investigative dossier concerning regulatory compliance, contraband tracking, and inter-agency intelligence synchronization across civil and maritime jurisdictions.",
                "case_type": "GENERAL", "status": "OPEN", "priority": "MEDIUM",
                "investigating_officer": "Inspector Sharma",
                "incident_date": datetime(2026, 9, 22, 10, 0),
                "incident_location": "Inland Container Depot, Tughlakabad, New Delhi",
                "reporting_authority": "Customs Preventive Commissionerate",
                "assigned_team": "Joint Task Force Enforcement",
                "persons_involved": "Multi-Agency Task Force, Consignor Maritime Global",
                "jurisdiction": "Central Administrative & Judicial Tribunal",
                "retention_category": "STANDARD_5YR",
                "confidentiality_level": "UNCLASSIFIED",
            },
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
                incident_date=c["incident_date"],
                incident_location=c["incident_location"],
                reporting_authority=c["reporting_authority"],
                assigned_team=c["assigned_team"],
                persons_involved=c["persons_involved"],
                jurisdiction=c["jurisdiction"],
                retention_category=c["retention_category"],
                confidentiality_level=c["confidentiality_level"],
                is_court_ready=(c["status"] == "COURT_READY"),
                court_docket_number=f"DOCK-{c['case_number']}" if c["status"] == "COURT_READY" else "",
            )
            db.add(case)
            cases.append(case)
        db.commit()
        for c in cases:
            db.refresh(c)
        print(f"   ✓ Created {len(cases)} cases across all 9 Case Types")

        # === GENESIS BLOCK ===
        print("⛓️  Creating genesis block...")
        create_genesis_block(db)

        # === EVIDENCE ===
        print("📄 Creating evidence records with Stage 2 metadata...")
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)

        evidence_templates = [
            # Case 1: Missing Person
            {"filename": "FIR_Report_Case001.pdf", "case_idx": 0, "mime": "application/pdf",
             "classification": "FIR", "content": "FIRST INFORMATION REPORT\nPolice Station: Connaught Place\nDate: 05-Sep-2026\nComplainant: Mrs. Sunita Verma\nSubject: Missing Person Report\n\nI, Mrs. Sunita Verma, wife of Mr. Rahul Verma, age 32, resident of B-42, Vasant Kunj, New Delhi, hereby report that my husband Mr. Rahul Verma has been missing since 5th September 2026. He was last seen leaving our residence at approximately 09:30 AM. He was wearing a blue shirt and black trousers. His mobile phone is switched off since 11:45 AM.\n\nInvestigating Officer: Inspector Sharma, Badge INV-201",
             "source": "Complainant In-Person Lodgement", "collector": "Inspector Sharma", "condition": "INTACT", "storage": "Digital Vault / Primary FIR Depot"},
            {"filename": "Witness_Statement_Arun.docx", "case_idx": 0, "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "classification": "INVESTIGATION_REPORT", "content": "WITNESS STATEMENT\nWitness: Mr. Arun Kumar\nDate: 06-Sep-2026\nLocation: Police Station Connaught Place\n\nI, Mr. Arun Kumar, shopkeeper at Shop No. 15, Palika Bazaar, state that I saw Mr. Rahul Verma near the parking area at approximately 10:15 AM on 5th September 2026. He appeared to be speaking with an unknown person near a white sedan. The unknown person was approximately 5'10\", medium build.\n\nRecorded by: Inspector Sharma",
             "source": "Palika Bazaar Shopkeeper Deposition", "collector": "Inspector Sharma", "condition": "INTACT", "storage": "Digital Vault / Case File Dossier"},
            {"filename": "CCTV_Screenshot_CP.png", "case_idx": 0, "mime": "image/png",
             "classification": "EVIDENCE", "content": "CCTV footage screenshot showing subject near Connaught Place parking area at 10:14 AM",
             "source": "Delhi Police Surveillance Grid Cam #CP-09", "collector": "Inspector Sharma", "condition": "INTACT", "storage": "Digital Vault / Media Partition"},

            # Case 2: Financial Fraud
            {"filename": "Financial_Audit_TechCorp.pdf", "case_idx": 1, "mime": "application/pdf",
             "classification": "FORENSIC_REPORT", "content": "FORENSIC FINANCIAL AUDIT REPORT\nCase: CASE-2026-002\nSubject: TechCorp Ltd Financial Investigation\nPrepared by: Dr. Priya Forensic\nDate: 08-Sep-2026\n\nExecutive Summary:\nOur forensic analysis of TechCorp Ltd financial records reveals systematic fraud through:\n1. 47 falsified invoices totaling Rs. 1.8 Crore\n2. 3 shell companies used for money laundering\n3. Unauthorized wire transfers to offshore accounts\n\nKey findings indicate that the CFO, Mr. Vikram Patel, orchestrated the scheme starting January 2025.\n\nOrganizations involved: TechCorp Ltd, GlobalPay Solutions, Meridian Exports",
             "source": "Forensic Accounting Examination", "collector": "Dr. Priya Forensic", "condition": "INTACT", "storage": "FSL Digital Analysis Repository"},
            {"filename": "Bank_Statements_Q1_2026.pdf", "case_idx": 1, "mime": "application/pdf",
             "classification": "EVIDENCE", "content": "BANK STATEMENT — CONFIDENTIAL\nAccount Holder: TechCorp Ltd\nBank: State Bank of India\nAccount No: XXXX-XXXX-4521\nPeriod: January 2026 — March 2026\n\nSuspicious transactions flagged:\n15-Jan-2026: Wire transfer Rs. 45,00,000 to GlobalPay Solutions\n28-Feb-2026: Wire transfer Rs. 32,00,000 to Meridian Exports\n15-Mar-2026: Cash withdrawal Rs. 8,00,000",
             "source": "Subpoena Production from State Bank of India", "collector": "Inspector Sharma", "condition": "INTACT", "storage": "Digital Vault / Financial Locker"},

            # Case 3: Cybercrime
            {"filename": "Ransomware_Analysis_Report.pdf", "case_idx": 2, "mime": "application/pdf",
             "classification": "FORENSIC_REPORT", "content": "DIGITAL FORENSIC REPORT\nCase: CASE-2026-003\nIncident: Ransomware Attack\nDate of Incident: 01-Sep-2026\nAnalyst: Dr. Priya Forensic\n\nMalware Analysis:\nThe ransomware variant identified as 'CryptoLock-X' was deployed via spear-phishing email targeting the IT administrator. The malware encrypted 2,847 files across 12 servers.\n\nAttack Vector: Email attachment (malicious macro in Excel file)\nEncryption: AES-256\nRansom Demand: 5 Bitcoin\nC2 Server: 185.234.xx.xx (located in Eastern Europe)\n\nEmail: admin@dmc.gov.in was the initial compromise point",
             "source": "Bitstream Memory Dump & Disk Analysis", "collector": "Dr. Priya Forensic", "condition": "INTACT", "storage": "Cyber Forensic Enclave Disk Image Storage"},
            {"filename": "Server_Logs_DMC.txt", "case_idx": 2, "mime": "text/plain",
             "classification": "EVIDENCE", "content": "SERVER ACCESS LOG — CONFIDENTIAL\nServer: DMC-PROD-01\nDate: 01-Sep-2026\n\n[08:45:22] INFO: User admin@dmc.gov.in logged in from 10.0.1.15\n[08:46:03] INFO: Email attachment opened: Q3_Budget.xlsx\n[08:46:15] WARNING: Macro execution detected\n[08:46:18] CRITICAL: Suspicious process spawned: svchost_update.exe\n[08:46:22] CRITICAL: Mass file encryption started\n[08:47:01] CRITICAL: 500 files encrypted in /data/\n[09:15:00] CRITICAL: Ransom note displayed on all terminals",
             "source": "Syslog Appliance Extraction", "collector": "Inspector Sharma", "condition": "INTACT", "storage": "Digital Vault / Raw Log Vault"},

            # Case 4: Accident
            {"filename": "Crash_Site_Inspection_Report.pdf", "case_idx": 3, "mime": "application/pdf",
             "classification": "INVESTIGATION_REPORT", "content": "ACCIDENT INVESTIGATION & TECHNICAL RECONSTRUCTION REPORT\nCase: CASE-2026-004\nLocation: Outer Ring Road Flyover, Pillar #84\nVehicle 1: Two-wheeler (Reg: DL-04-BK-8921)\nVehicle 2 (Suspect): Dark Grey SUV (Make: Fortuner, partial plate 5821)\n\nAnalysis: Skid mark measurements indicate suspect vehicle speed exceeded 110 km/h in an 60 km/h zone. Impact angle 35 degrees rear-left collision. Metallic paint scraped onto guardrail matches factory code #GR-402.\n\nInvestigating Officer: Inspector Sharma",
             "source": "Physical Crash Site Reconstruction", "collector": "Inspector Sharma", "condition": "INTACT", "storage": "Digital Vault / Accident Reports"},
            {"filename": "Toll_Plaza_Dashcam_Clip.png", "case_idx": 3, "mime": "image/png",
             "classification": "EVIDENCE", "content": "High-definition toll plaza frame grab showing suspect dark grey SUV fleeing with front bumper damage at 23:22 PM",
             "source": "NHAI Toll Barrier ANPR System", "collector": "Inspector Sharma", "condition": "INTACT", "storage": "Digital Vault / High Speed ANPR Cache"},

            # Case 5: Murder / Homicide
            {"filename": "Autopsy_Forensic_PostMortem.pdf", "case_idx": 4, "mime": "application/pdf",
             "classification": "FORENSIC_REPORT", "content": "MEDICO-LEGAL POST-MORTEM EXAMINATION REPORT\nCase: CASE-2026-005\nSubject: Unidentified Male (approx. age 35)\nExamining Pathologist: Dr. K. N. Rao, Forensic Science Laboratory\n\nCause of Death: Hemorrhagic shock secondary to penetrating trauma. Blunt force injury observed on occipital region. Time of death estimated between 22:00 and 01:00 hours.\nBiological samples preserved: Blood card, fingernail scrapings, DNA reference swabs.",
             "source": "Mortuary Autopsy Suite FSL", "collector": "Dr. Priya Forensic", "condition": "INTACT", "storage": "FSL Medico-Legal Records"},
            {"filename": "CrimeScene_Biological_Swab_Analysis.txt", "case_idx": 4, "mime": "text/plain",
             "classification": "FORENSIC_REPORT", "content": "DNA FORENSIC LAB ANALYSIS REPORT\nSample ID: BIO-SWAB-005A\nOrigin: Door handle at Sector 14 warehouse\nAllele Profile: Mixed DNA profile detected. Major donor matches victim; minor STR donor profile catalogued in CODIS pending suspect reference cross-match.",
             "source": "Crime Scene Biological Extraction", "collector": "Dr. Priya Forensic", "condition": "SEALED", "storage": "FSL Bio-Specimen Cold Storage -80C",
             "lab_sample_id": "BIO-SWAB-005A", "lab_test": "STR Multiplex DNA Profiling", "qc_status": "QC_PASSED", "court_exhibit": "EXHIBIT-P-01", "court_action": "ADMITTED"},

            # Case 7: Narcotics
            {"filename": "Narcotics_Chemical_Assay_Report.pdf", "case_idx": 6, "mime": "application/pdf",
             "classification": "FORENSIC_REPORT", "content": "FORENSIC CHEMICAL TESTING & SPECTROMETRY REPORT\nCase: CASE-2026-007\nAgency: Narcotics Control Bureau\nSeized Material: 2.4 Kilograms crystalline white substance in tamper-evident heat-sealed bags.\n\nGas Chromatography-Mass Spectrometry (GC-MS) Results:\nCompound Identified: Methamphetamine Hydrochloride (purity 94.2% wt/wt).\nPackaging Seals: Tamper-evident seal NCB-DEL-984 intact upon intake.\n\nAnalyst: Dr. Priya Forensic, Chief Chemical Examiner",
             "source": "Air Cargo Seizure under NDPS Warrant", "collector": "Inspector Sharma", "condition": "SEALED", "storage": "Central Narcotics Malkhana Safe Vault",
             "lab_sample_id": "NDPS-SPEC-902", "lab_test": "GC-MS Purity & Spectrometry Assay", "qc_status": "QC_PASSED", "court_exhibit": "EXHIBIT-N-01", "court_action": "ADMITTED"},

            # Case 8: Assault
            {"filename": "Medico_Legal_Injury_Certificate.pdf", "case_idx": 7, "mime": "application/pdf",
             "classification": "FORENSIC_REPORT", "content": "MEDICO-LEGAL INJURY REPORT (MLC)\nCase: CASE-2026-008\nPatient/Victim: Karan Singhal, Age 28\nExamining Medical Officer: Dr. A. K. Sen, AIIMS Trauma Centre\n\nInjury Details:\n1. 4cm laceration over left parietal bone caused by heavy blunt weapon.\n2. Contusion and swelling over right zygomatic arch.\nNature of Injuries: Grievous hurt within meaning of Section 116 BNS.\n\nSeized Physical Artifacts: Blood-stained cotton shirt forwarded for serology testing.",
             "source": "AIIMS Trauma Centre Emergency Deposition", "collector": "Inspector Sharma", "condition": "INTACT", "storage": "Digital Vault / MLC Archive",
             "lab_sample_id": "BIO-SER-008", "lab_test": "Blood Grouping & Serology", "qc_status": "QC_PASSED", "court_exhibit": "EXHIBIT-A-01", "court_action": "ADMITTED"},
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
                description=f"Seized evidentiary asset for {cases[et['case_idx']].case_number}",
                uploaded_by=users[1].id,
                source=et.get("source", "Incident Scene Collection"),
                collector=et.get("collector", users[1].full_name),
                collection_datetime=datetime.utcnow() - timedelta(days=7 - i),
                collection_location=et.get("storage", "Incident Scene"),
                condition_at_intake=et.get("condition", "INTACT"),
                storage_location=et.get("storage", "Digital Vault / Secure Repository"),
                lab_sample_id=et.get("lab_sample_id", ""),
                lab_test_requested=et.get("lab_test", ""),
                lab_test_performed=et.get("lab_test", ""),
                lab_qc_status=et.get("qc_status", "QC_PASSED" if et.get("lab_sample_id") else "QC_PENDING"),
                lab_seal_intact=True,
                lab_analyst=users[2].full_name if et.get("lab_sample_id") else "",
                court_exhibit_number=et.get("court_exhibit", ""),
                court_receipt_number=f"REC-CRT-{i + 1:04d}" if et.get("court_exhibit") else "",
                court_presentation_date=datetime.utcnow() - timedelta(days=1) if et.get("court_exhibit") else None,
                court_action=et.get("court_action", "ADMITTED" if et.get("court_exhibit") else "PENDING"),
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
                reason="Initial upload and hashing",
                actor_id=users[1].id,
                actor_name=users[1].full_name,
                created_at=ev.created_at,
            )
            db.add(version)
        db.commit()

        # === CUSTODY EVENTS (WITH CRYPTOGRAPHIC HASH CHAINING - SECTION 25) ===
        print("🔗 Creating cryptographic chain of custody events...")
        custody_templates = [
            (0, 1, "EVIDENCE_REGISTERED", "Initial evidence intake and registration in vault", "GENESIS_CUSTODY_HASH"),
            (0, 1, "ANALYSIS_STARTED", "Automated AI metadata and entity classification", None),
            (0, 2, "EVIDENCE_TRANSFERRED", "Transferred to Forensic Specialist for analysis", None),
            (0, 2, "ANALYSIS_COMPLETED", "Forensic analysis completed and verified", None),
            (0, 3, "EVIDENCE_TRANSFERRED", "Transferred to Legal Prosecutor for review", None),
            (1, 1, "EVIDENCE_REGISTERED", "Witness statement recorded and sealed", "GENESIS_CUSTODY_HASH"),
            (3, 1, "EVIDENCE_REGISTERED", "Financial audit report uploaded", "GENESIS_CUSTODY_HASH"),
            (3, 2, "EVIDENCE_TRANSFERRED", "Transferred to Forensic Science Lab", None),
            (3, 2, "ANALYSIS_COMPLETED", "Forensic financial analysis completed", None),
            (5, 1, "EVIDENCE_REGISTERED", "Ransomware report uploaded", "GENESIS_CUSTODY_HASH"),
            (5, 2, "EVIDENCE_TRANSFERRED", "Transferred to Cyber Lab", None),
            (9, 2, "LABORATORY_ANALYSIS_COMPLETED", "STR Multiplex DNA Profiling completed with QC Pass", "GENESIS_CUSTODY_HASH"),
            (10, 2, "LABORATORY_ANALYSIS_COMPLETED", "GC-MS Purity & Spectrometry Assay completed with QC Pass", "GENESIS_CUSTODY_HASH"),
            (11, 2, "LABORATORY_ANALYSIS_COMPLETED", "Medico-legal injury certificate serology verified", "GENESIS_CUSTODY_HASH"),
        ]

        # Track previous hashes per evidence
        evidence_chain_hashes = {}

        for idx, (ev_idx, user_idx, action, notes, initial_prev) in enumerate(custody_templates):
            if ev_idx < len(evidences):
                ev_obj = evidences[ev_idx]
                prev_h = evidence_chain_hashes.get(ev_obj.id, initial_prev or "GENESIS_CUSTODY_HASH")
                curr_h = compute_sha256(f"{prev_h}:{ev_obj.evidence_id}:{action}:{users[user_idx].full_name}:{idx}".encode())
                evidence_chain_hashes[ev_obj.id] = curr_h
                sig = f"SIG-{users[user_idx].role}-{curr_h[:16].upper()}"

                ce = CustodyEvent(
                    event_id=f"COC-{ev_obj.evidence_id[-6:]}-{idx+1:02d}",
                    evidence_id=ev_obj.id,
                    actor_id=users[user_idx].id,
                    actor_name=users[user_idx].full_name,
                    actor_role=users[user_idx].role,
                    previous_custodian="Field Intake" if "REGISTERED" in action else users[1].full_name,
                    new_custodian=users[user_idx].full_name,
                    action=action,
                    reason="Chain of custody event per standard operating procedure",
                    location="Forensic Science Laboratory" if user_idx == 2 else "Investigation Command",
                    evidence_condition="INTACT",
                    integrity_state="VERIFIED",
                    authorization="Magistrate Court Directive / Standing Order",
                    digital_signature=sig,
                    notes=notes,
                    sha256_hash=ev_obj.sha256_hash,
                    previous_event_hash=prev_h,
                    current_event_hash=curr_h,
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
