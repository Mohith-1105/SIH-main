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
    """Add new Phase 2 columns without dropping existing SQLite data."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    additions = {
        "evidence": [
            ("stored_filename", "VARCHAR(500) DEFAULT ''"),
            ("file_type", "VARCHAR(50) DEFAULT 'DOCUMENT'"),
            ("status", "VARCHAR(50) DEFAULT 'REGISTERED'"),
            ("uploaded_at", "DATETIME"),
        ],
        "evidence_versions": [
            ("filename", "VARCHAR(500) DEFAULT ''"),
            ("change_reason", "TEXT DEFAULT ''"),
            ("uploaded_by", "VARCHAR(255) DEFAULT ''"),
        ],
        "users": [
            ("totp_secret", "VARCHAR(100) DEFAULT ''"),
            ("rank_level", "INTEGER DEFAULT 3"),
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
        # Backfill per-user TOTP secrets for rows created before the column existed
        try:
            from app.security.mfa import generate_totp_secret
            rows = conn.execute(
                text("SELECT id FROM users WHERE totp_secret IS NULL OR totp_secret = ''")
            ).fetchall()
            for (uid,) in rows:
                conn.execute(
                    text("UPDATE users SET totp_secret = :s WHERE id = :id"),
                    {"s": generate_totp_secret(), "id": uid},
                )
        except Exception:
            pass
        # Backfill rank_level by role for rows created before the column existed
        try:
            from app.security.auth import ROLE_DEFAULT_RANK
            rows = conn.execute(text(
                "SELECT id, role FROM users WHERE rank_level IS NULL OR rank_level < 1 OR rank_level > 6"
            )).fetchall()
            for uid, role in rows:
                conn.execute(
                    text("UPDATE users SET rank_level = :r WHERE id = :id"),
                    {"r": ROLE_DEFAULT_RANK.get(role, 3), "id": uid},
                )
        except Exception:
            pass
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
    """Create all tables and apply safe SQLite migrations."""
    from app.models import user, case, evidence, blockchain, audit  # noqa
    Base.metadata.create_all(bind=engine)
    migrate_sqlite()
