"""Phase 2 Automated Test Suite for EvidenceVault Backend.

Tests:
1. Evidence upload & SHA-256 accuracy
2. Invalid file rejection (disallowed ext, empty file)
3. Fernet encryption storage & decryption verification
4. Evidence Passport generation
5. Integrity verification (VERIFIED & TAMPERED states)
6. Evidence version creation & listing
7. Custody transfer & timeline
8. Audit log creation & RBAC authorization checks (403 Forbidden)
"""
import os
import sys
import hashlib
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal, init_db
from app.models.user import User
from app.models.case import Case
from app.models.evidence import Evidence, EvidenceVersion, CustodyEvent
from app.models.audit import AuditLog
from app.security.auth import hash_password, create_access_token, decrypt_file
from app.config import settings

client = TestClient(app)


def setup_database():
    init_db()
    db = SessionLocal()

    try:
        # Create test users if not exist
        admin = db.query(User).filter(User.email == "admin_test@vault.local").first()
        if not admin:
            admin = User(
                email="admin_test@vault.local",
                full_name="Test Admin",
                hashed_password=hash_password("test1234"),
                role="ADMIN",
            )
            db.add(admin)

        investigator = db.query(User).filter(User.email == "investigator_test@vault.local").first()
        if not investigator:
            investigator = User(
                email="investigator_test@vault.local",
                full_name="Test Investigator",
                hashed_password=hash_password("test1234"),
                role="INVESTIGATOR",
            )
            db.add(investigator)

        auditor = db.query(User).filter(User.email == "auditor_test@vault.local").first()
        if not auditor:
            auditor = User(
                email="auditor_test@vault.local",
                full_name="Test Auditor",
                hashed_password=hash_password("test1234"),
                role="AUDITOR",
            )
            db.add(auditor)

        forensic = db.query(User).filter(User.email == "forensic_test@vault.local").first()
        if not forensic:
            forensic = User(
                email="forensic_test@vault.local",
                full_name="Test Forensic Officer",
                hashed_password=hash_password("test1234"),
                role="FORENSIC_OFFICER",
            )
            db.add(forensic)

        db.flush()

        # Create test case
        c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
        if not c:
            c = Case(
                case_number="CASE-TEST-PH2",
                title="Phase 2 Verification Case",
                description="Test case for Phase 2 validation",
                created_by=investigator.id,
            )
            db.add(c)

        c.created_by = investigator.id
        c.assigned_user_id = investigator.id

        db.commit()
    finally:
        db.close()


def get_token_for(email: str, role: str, user_id: int = 1) -> str:
    return create_access_token({"sub": str(user_id), "email": email, "role": role})


def test_evidence_upload_and_sha256():
    print("Running test_evidence_upload_and_sha256...")
    db = SessionLocal()
    c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
    case_id = c.id
    investigator = db.query(User).filter(User.email == "investigator_test@vault.local").first()
    db.close()

    token = get_token_for(investigator.email, "INVESTIGATOR", investigator.id)
    headers = {"Authorization": f"Bearer {token}"}

    file_content = b"%PDF-1.5 EVIDENCE_VAULT_TEST_CONTENT_PHASE_2_" + os.urandom(64)
    expected_hash = hashlib.sha256(file_content).hexdigest()

    response = client.post(
        "/api/evidence/upload",
        headers=headers,
        data={"case_id": str(case_id), "description": "Test Evidence Doc"},
        files={"file": ("test_doc.pdf", file_content, "application/pdf")},
    )

    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()

    assert data["sha256_hash"] == expected_hash, "Calculated SHA-256 hash mismatch!"
    assert data["original_filename"] == "test_doc.pdf"
    assert data["current_version"] == 1
    assert data["integrity_status"] == "VERIFIED"
    print("  PASSED [OK]")


def test_invalid_file_rejection():
    print("Running test_invalid_file_rejection...")
    db = SessionLocal()
    c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
    case_id = c.id
    investigator = db.query(User).filter(User.email == "investigator_test@vault.local").first()
    db.close()

    token = get_token_for(investigator.email, "INVESTIGATOR", investigator.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Unallowed extension .exe
    r_exe = client.post(
        "/api/evidence/upload",
        headers=headers,
        data={"case_id": str(case_id)},
        files={"file": ("malware.exe", b"MZ_TEST_CONTENT", "application/x-msdownload")},
    )
    assert r_exe.status_code == 400, "Should reject disallowed extension!"
    assert "not allowed" in r_exe.json()["detail"].lower()

    # Empty file
    r_empty = client.post(
        "/api/evidence/upload",
        headers=headers,
        data={"case_id": str(case_id)},
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert r_empty.status_code == 400, "Should reject empty file!"
    print("  PASSED [OK]")


def test_encryption_and_decryption():
    print("Running test_encryption_and_decryption...")
    db = SessionLocal()
    c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
    case_id = c.id
    investigator = db.query(User).filter(User.email == "investigator_test@vault.local").first()
    db.close()

    token = get_token_for(investigator.email, "INVESTIGATOR", investigator.id)
    headers = {"Authorization": f"Bearer {token}"}

    secret_bytes = b"SECRET_CONFIDENTIAL_FORENSIC_EVIDENCE_DATA_12345"
    r = client.post(
        "/api/evidence/upload",
        headers=headers,
        data={"case_id": str(case_id)},
        files={"file": ("confidential.txt", secret_bytes, "text/plain")},
    )
    assert r.status_code == 200
    ev = r.json()

    # Inspect file on disk
    storage_path = os.path.join(settings.STORAGE_DIR, ev["stored_filename"])
    assert os.path.exists(storage_path), "Encrypted file missing from storage directory!"

    with open(storage_path, "rb") as f:
        stored_bytes = f.read()

    # Verify disk content is encrypted (NOT raw plain text)
    assert secret_bytes not in stored_bytes, "File on disk is plain text! Fernet encryption failed!"

    # Verify decrypting restores original bytes
    decrypted_bytes = decrypt_file(stored_bytes)
    assert decrypted_bytes == secret_bytes, "Decrypted bytes do not match original file content!"
    print("  PASSED [OK]")


def test_evidence_passport():
    print("Running test_evidence_passport...")
    db = SessionLocal()
    c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
    case_id = c.id
    investigator = db.query(User).filter(User.email == "investigator_test@vault.local").first()
    db.close()

    token = get_token_for(investigator.email, "INVESTIGATOR", investigator.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/evidence/upload",
        headers=headers,
        data={"case_id": str(case_id)},
        files={"file": ("passport_test.png", b"\x89PNG\r\n\x1a\nTEST", "image/png")},
    )
    ev_id = r.json()["id"]

    passport_res = client.get(f"/api/evidence/{ev_id}/passport", headers=headers)
    assert passport_res.status_code == 200
    p = passport_res.json()

    assert p["evidence_id"].startswith("EV-")
    assert p["original_filename"] == "passport_test.png"
    assert p["sha256_hash"] == r.json()["sha256_hash"]
    assert p["qr_code"] != ""
    print("  PASSED [OK]")


def test_integrity_verification_verified_and_tampered():
    print("Running test_integrity_verification_verified_and_tampered...")
    db = SessionLocal()
    c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
    case_id = c.id
    investigator = db.query(User).filter(User.email == "investigator_test@vault.local").first()
    db.close()

    token = get_token_for(investigator.email, "INVESTIGATOR", investigator.id)
    headers = {"Authorization": f"Bearer {token}"}

    content = b"INTEGRITY_VERIFICATION_TEST_DATA"
    r = client.post(
        "/api/evidence/upload",
        headers=headers,
        data={"case_id": str(case_id)},
        files={"file": ("verify.txt", content, "text/plain")},
    )
    ev_id = r.json()["id"]

    # 1. Test VERIFIED state
    v_res = client.post(f"/api/evidence/{ev_id}/verify", headers=headers)
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["status"] == "VERIFIED"
    assert v_data["hash_match"] is True

    # 2. Simulate Tampering by modifying hash in DB
    db = SessionLocal()
    ev_obj = db.query(Evidence).filter(Evidence.id == ev_id).first()
    ev_obj.sha256_hash = "TAMPERED_" + ev_obj.sha256_hash[9:]
    db.commit()
    db.close()

    # 3. Test TAMPERED state
    t_res = client.post(f"/api/evidence/{ev_id}/verify", headers=headers)
    assert t_res.status_code == 200
    t_data = t_res.json()
    assert t_data["status"] == "TAMPERED"
    assert t_data["hash_match"] is False
    assert "TAMPERING DETECTED" in t_data["details"]
    print("  PASSED [OK]")


def test_evidence_versioning():
    print("Running test_evidence_versioning...")
    db = SessionLocal()
    c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
    case_id = c.id
    investigator = db.query(User).filter(User.email == "investigator_test@vault.local").first()
    db.close()

    token = get_token_for(investigator.email, "INVESTIGATOR", investigator.id)
    headers = {"Authorization": f"Bearer {token}"}

    v1_bytes = b"%PDF-1.5 VERSION_1_ORIGINAL_CONTENT"
    r = client.post(
        "/api/evidence/upload",
        headers=headers,
        data={"case_id": str(case_id)},
        files={"file": ("report_v1.pdf", v1_bytes, "application/pdf")},
    )
    ev_id = r.json()["id"]

    # Create Version 2
    v2_bytes = b"%PDF-1.5 VERSION_2_UPDATED_CONTENT"
    v2_res = client.post(
        f"/api/evidence/{ev_id}/versions",
        headers=headers,
        data={"change_reason": "Added forensic analysis findings"},
        files={"file": ("report_v2.pdf", v2_bytes, "application/pdf")},
    )

    assert v2_res.status_code == 200
    v2_data = v2_res.json()
    assert v2_data["version_number"] == 2
    assert v2_data["change_reason"] == "Added forensic analysis findings"

    # Get Versions list
    ver_res = client.get(f"/api/evidence/{ev_id}/versions", headers=headers)
    assert ver_res.status_code == 200
    ver_list = ver_res.json()
    assert len(ver_list) == 2
    assert ver_list[0]["version_number"] == 1
    assert ver_list[1]["version_number"] == 2
    print("  PASSED [OK]")


def test_custody_transfer_and_timeline():
    print("Running test_custody_transfer_and_timeline...")
    db = SessionLocal()
    c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
    case_id = c.id
    investigator = db.query(User).filter(User.email == "investigator_test@vault.local").first()
    forensic = db.query(User).filter(User.role == "FORENSIC_OFFICER").first()
    db.close()

    token_inv = get_token_for(investigator.email, "INVESTIGATOR", investigator.id)
    headers_inv = {"Authorization": f"Bearer {token_inv}"}

    r = client.post(
        "/api/evidence/upload",
        headers=headers_inv,
        data={"case_id": str(case_id)},
        files={"file": ("transfer_test.txt", b"CUSTODY_TRANSFER_DATA", "text/plain")},
    )
    ev_id = r.json()["id"]

    # Transfer Custody to Forensic Officer
    t_res = client.post(
        f"/api/evidence/{ev_id}/transfer",
        headers=headers_inv,
        json={
            "target_user_id": forensic.id,
            "location": "Forensic Laboratory Wing B",
            "condition": "SEALED",
            "notes": "Handed over for fingerprint analysis",
        },
    )
    assert t_res.status_code == 200

    # Verify Timeline
    cust_res = client.get(f"/api/evidence/{ev_id}/custody", headers=headers_inv)
    assert cust_res.status_code == 200
    events = cust_res.json()
    assert len(events) >= 2
    actions = [e["action"] for e in events]
    assert "EVIDENCE_CREATED" in actions
    assert "EVIDENCE_TRANSFERRED" in actions or "CUSTODY_TRANSFERRED" in actions
    print("  PASSED [OK]")


def test_audit_logs_and_rbac():
    print("Running test_audit_logs_and_rbac...")
    db = SessionLocal()
    auditor = db.query(User).filter(User.role == "AUDITOR").first()
    c = db.query(Case).filter(Case.case_number == "CASE-TEST-PH2").first()
    case_id = c.id
    db.close()

    # AUDITOR token attempting upload (should be HTTP 403 Forbidden)
    token_auditor = get_token_for(auditor.email, "AUDITOR", auditor.id)
    headers_auditor = {"Authorization": f"Bearer {token_auditor}"}

    r_forbidden = client.post(
        "/api/evidence/upload",
        headers=headers_auditor,
        data={"case_id": str(case_id)},
        files={"file": ("unauthorized.txt", b"UNAUTHORIZED", "text/plain")},
    )
    assert r_forbidden.status_code == 403, "AUDITOR must be denied upload with 403 Forbidden!"

    # Verify audit log was recorded for other operations
    audit_res = client.get("/api/audit-logs", headers=headers_auditor)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0
    print("  PASSED [OK]")


def main():
    print("==========================================")
    print("Starting EvidenceVault Phase 2 Test Suite")
    print("==========================================")
    setup_database()
    test_evidence_upload_and_sha256()
    test_invalid_file_rejection()
    test_encryption_and_decryption()
    test_evidence_passport()
    test_integrity_verification_verified_and_tampered()
    test_evidence_versioning()
    test_custody_transfer_and_timeline()
    test_audit_logs_and_rbac()
    print("==========================================")
    print("[SUCCESS] ALL PHASE 2 TESTS PASSED SUCCESSFULLY!")
    print("==========================================")



if __name__ == "__main__":
    main()
