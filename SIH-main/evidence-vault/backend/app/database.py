"""Database setup for EvidenceVault"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Enable WAL mode and foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_columns(table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def migrate_sqlite():
    """Add new columns for RBAC/CoC without dropping existing SQLite data."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    additions = {
        "evidence": [
            ("stored_filename", "VARCHAR(500) DEFAULT ''"),
            ("file_type", "VARCHAR(50) DEFAULT 'DOCUMENT'"),
            ("status", "VARCHAR(50) DEFAULT 'REGISTERED'"),
            ("uploaded_at", "DATETIME"),
            ("physical_location", "VARCHAR(255) DEFAULT 'Malkhana Bay A-Shelf 3'"),
            ("barcode_id", "VARCHAR(100) DEFAULT ''"),
            ("physical_status", "VARCHAR(50) DEFAULT 'CHECKED_IN'"),
            ("is_frozen", "BOOLEAN DEFAULT 0"),
            ("quarantine_reason", "TEXT DEFAULT ''"),
            ("is_unsealed_by_warrant", "BOOLEAN DEFAULT 0"),
            ("warrant_number", "VARCHAR(100) DEFAULT ''"),
            ("deletion_requested", "BOOLEAN DEFAULT 0"),
            ("deletion_request_reason", "TEXT DEFAULT ''"),
            ("deletion_status", "VARCHAR(50) DEFAULT 'NONE'"),
            ("deletion_request_by", "INTEGER"),
            ("forensic_status", "VARCHAR(50) DEFAULT 'NOT_REQUIRED'"),
            ("custody_state", "VARCHAR(50) DEFAULT 'SECURE_VAULT'"),
            ("physical_release_approved", "BOOLEAN DEFAULT 0"),
            ("physical_release_to", "VARCHAR(255) DEFAULT ''"),
            ("parent_evidence_id", "INTEGER"),
            ("is_child_report", "BOOLEAN DEFAULT 0"),
            ("source", "VARCHAR(500) DEFAULT ''"),
            ("collector", "VARCHAR(255) DEFAULT ''"),
            ("collection_datetime", "DATETIME"),
            ("collection_location", "VARCHAR(500) DEFAULT ''"),
            ("condition_at_intake", "VARCHAR(100) DEFAULT 'INTACT'"),
            ("storage_location", "VARCHAR(255) DEFAULT 'Digital Vault / Secure Repository'"),
            ("lab_sample_id", "VARCHAR(100) DEFAULT ''"),
            ("lab_test_requested", "VARCHAR(255) DEFAULT ''"),
            ("lab_test_performed", "VARCHAR(255) DEFAULT ''"),
            ("lab_qc_status", "VARCHAR(50) DEFAULT 'QC_PENDING'"),
            ("lab_seal_intact", "BOOLEAN DEFAULT 1"),
            ("lab_findings", "TEXT DEFAULT ''"),
            ("lab_analyst", "VARCHAR(255) DEFAULT ''"),
            ("court_exhibit_number", "VARCHAR(100) DEFAULT ''"),
            ("court_receipt_number", "VARCHAR(100) DEFAULT ''"),
            ("court_presentation_date", "DATETIME"),
            ("court_action", "VARCHAR(50) DEFAULT 'PENDING'"),
            ("court_disposition_notes", "TEXT DEFAULT ''"),
            ("court_order_ref", "VARCHAR(100) DEFAULT ''"),
            ("destruction_certificate_id", "VARCHAR(100) DEFAULT ''"),
            ("destruction_timestamp", "DATETIME"),
            ("destruction_authority", "VARCHAR(255) DEFAULT ''"),
            ("destruction_method", "VARCHAR(255) DEFAULT ''"),
            ("is_destroyed", "BOOLEAN DEFAULT 0"),
        ],
        "evidence_versions": [
            ("filename", "VARCHAR(500) DEFAULT ''"),
            ("change_reason", "TEXT DEFAULT ''"),
            ("uploaded_by", "VARCHAR(255) DEFAULT ''"),
        ],
        "cases": [
            ("is_frozen", "BOOLEAN DEFAULT 0"),
            ("quarantine_reason", "TEXT DEFAULT ''"),
            ("is_court_ready", "BOOLEAN DEFAULT 0"),
            ("court_docket_number", "VARCHAR(100) DEFAULT ''"),
            ("incident_date", "DATETIME"),
            ("incident_location", "VARCHAR(500) DEFAULT ''"),
            ("reporting_authority", "VARCHAR(255) DEFAULT ''"),
            ("assigned_team", "VARCHAR(255) DEFAULT 'Special Investigation Unit'"),
            ("persons_involved", "TEXT DEFAULT ''"),
            ("jurisdiction", "VARCHAR(255) DEFAULT 'Delhi NCT Central'"),
            ("retention_category", "VARCHAR(100) DEFAULT 'STANDARD_5YR'"),
            ("confidentiality_level", "VARCHAR(100) DEFAULT 'CONFIDENTIAL'"),
            ("legal_hold", "BOOLEAN DEFAULT 0"),
            ("closure_checklist_json", "TEXT DEFAULT '{}'"),
            ("closed_at", "DATETIME"),
            ("closed_by", "INTEGER"),
            ("archived_at", "DATETIME"),
        ],
        "custody_events": [
            ("event_id", "VARCHAR(50) DEFAULT ''"),
            ("previous_custodian", "VARCHAR(255) DEFAULT ''"),
            ("new_custodian", "VARCHAR(255) DEFAULT ''"),
            ("reason", "VARCHAR(255) DEFAULT 'Custody Transfer'"),
            ("integrity_state", "VARCHAR(50) DEFAULT 'VERIFIED'"),
            ("authorization", "VARCHAR(255) DEFAULT 'Standard Investigation Procedure'"),
            ("digital_signature", "VARCHAR(255) DEFAULT ''"),
            ("previous_event_hash", "VARCHAR(64) DEFAULT ''"),
            ("current_event_hash", "VARCHAR(64) DEFAULT ''"),
        ],
        "users": [
            ("mfa_enabled", "BOOLEAN DEFAULT 1"),
        ],
    }
    with engine.begin() as conn:
        for table, cols in additions.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            if not existing:
                continue
            for name, ddl in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        # Backfill stored_filename from encrypted_path
        try:
            conn.execute(text(
                "UPDATE evidence SET stored_filename = encrypted_path "
                "WHERE stored_filename IS NULL OR stored_filename = ''"
            ))
            conn.execute(text(
                "UPDATE evidence SET file_type = evidence_type "
                "WHERE file_type IS NULL OR file_type = '' OR file_type = 'DOCUMENT'"
            ))
            conn.execute(text(
                "UPDATE evidence SET uploaded_at = created_at WHERE uploaded_at IS NULL"
            ))
            conn.execute(text(
                "UPDATE evidence SET barcode_id = 'BAR-' || substr(evidence_id, 4) "
                "WHERE barcode_id IS NULL OR barcode_id = ''"
            ))
            conn.execute(text(
                "UPDATE evidence_versions SET filename = "
                "(SELECT original_filename FROM evidence WHERE evidence.id = evidence_versions.evidence_id) "
                "WHERE filename IS NULL OR filename = ''"
            ))
            conn.execute(text(
                "UPDATE evidence_versions SET change_reason = reason "
                "WHERE change_reason IS NULL OR change_reason = ''"
            ))
            conn.execute(text(
                "UPDATE evidence_versions SET uploaded_by = actor_name "
                "WHERE uploaded_by IS NULL OR uploaded_by = ''"
            ))
        except Exception:
            pass


def init_db():
    """Create all tables, apply safe migrations, and provision default roles."""
    from app.models import user, case, evidence, blockchain, audit  # noqa
    Base.metadata.create_all(bind=engine)
    migrate_sqlite()

    # Ensure all 6 enterprise demo users exist
    from app.security.auth import hash_password
    default_users = [
        ("admin@evidencevault.local", "System Admin (K. Singhania)", "ADMIN", "IT & Platform Security", "ADM-001"),
        ("investigator@evidencevault.local", "Inspector Sharma (IO)", "INVESTIGATOR", "Criminal Investigation Division", "INV-201"),
        ("forensic@evidencevault.local", "Dr. Priya Forensic (Lab Analyst)", "FORENSIC_OFFICER", "Forensic Science Laboratory", "FSL-305"),
        ("legal@evidencevault.local", "Adv. Rajan Legal (Prosecutor)", "LEGAL_OFFICER", "State Prosecution Directorate", "LEG-102"),
        ("auditor@evidencevault.local", "Audit Officer Mehra (Oversight)", "AUDITOR", "Internal Compliance & Standards", "AUD-401"),
        ("custodian@evidencevault.local", "HC Ram (Malkhana Custodian)", "CUSTODIAN", "Malkhana Property Room", "MAL-501"),
    ]
    with engine.begin() as conn:
        for email, name, role, dept, badge in default_users:
            exists = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email}).fetchone()
            if not exists:
                conn.execute(text(
                    "INSERT INTO users (email, full_name, hashed_password, role, department, badge_number, is_active, created_at) "
                    "VALUES (:email, :name, :pw, :role, :dept, :badge, 1, datetime('now'))"
                ), {"email": email, "name": name, "pw": hash_password("demo123"), "role": role, "dept": dept, "badge": badge})
            else:
                conn.execute(text(
                    "UPDATE users SET role = :role, full_name = :name, department = :dept, badge_number = :badge WHERE email = :email"
                ), {"role": role, "name": name, "dept": dept, "badge": badge, "email": email})

        # Ensure sample privilege requests exist for Admin approval workflow
        try:
            req_exists = conn.execute(text("SELECT id FROM privilege_requests LIMIT 1")).fetchone()
            if not req_exists:
                conn.execute(text(
                    "INSERT INTO privilege_requests (requested_by_email, target_user_email, target_full_name, requested_role, justification, status, created_at) "
                    "VALUES ('investigator@evidencevault.local', 'sub-auditor.sharma@evidencevault.local', 'Sub-Inspector Sharma (Trainee)', 'AUDITOR', 'Requires secondary Auditor oversight role for ISO 27037 quarterly certification.', 'PENDING', datetime('now'))"
                ))
                conn.execute(text(
                    "INSERT INTO privilege_requests (requested_by_email, target_user_email, target_full_name, requested_role, justification, status, created_at) "
                    "VALUES ('forensic@evidencevault.local', 'lab.assistant.verma@evidencevault.local', 'Dev Verma (Lab Tech)', 'FORENSIC_OFFICER', 'Assigned to digital ballistics extraction unit. Needs child report upload rights.', 'PENDING', datetime('now'))"
                ))
        except Exception:
            pass


