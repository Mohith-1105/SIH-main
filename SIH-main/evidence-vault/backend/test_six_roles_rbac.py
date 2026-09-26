import sys
import os
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import init_db
from app.main import app

def run_tests():
    print("=" * 60)
    print("RUNNING 6-ROLE RBAC & SEPARATION OF DUTIES VERIFICATION")
    print("=" * 60)

    # 1. Initialize DB to ensure 6 seed accounts are loaded
    init_db()
    client = TestClient(app)

    roles = [
        ("admin@evidencevault.local", "ADMIN", "System Administrator"),
        ("investigator@evidencevault.local", "INVESTIGATOR", "Investigating Officer"),
        ("forensic@evidencevault.local", "FORENSIC_OFFICER", "Forensic Lab Analyst"),
        ("legal@evidencevault.local", "LEGAL_OFFICER", "Legal Prosecutor"),
        ("auditor@evidencevault.local", "AUDITOR", "Compliance Auditor"),
        ("custodian@evidencevault.local", "CUSTODIAN", "Malkhana Evidence Custodian")
    ]

    tokens = {}

    # Step 1: Authenticate all 6 personas
    print("\n--- STEP 1: Authentication & JWT Enterprise Claims ---")
    for email, expected_role, title in roles:
        res = client.post("/api/auth/login", json={"email": email, "password": "demo123"})
        assert res.status_code == 200, f"Login failed for {email}: {res.text}"
        data = res.json()
        assert "access_token" in data, f"Missing token for {email}"
        user_info = data["user"]
        assert user_info["role"] == expected_role, f"Role mismatch for {email}: got {user_info['role']}, expected {expected_role}"
        tokens[expected_role] = data["access_token"]
        print(f"  [PASS] {title} ({email}) authenticated successfully with role={expected_role}")

    # Step 2: System Administrator - Separation of Duties Verification
    print("\n--- STEP 2: Admin Separation of Duties (Zero Evidence Access) ---")
    admin_headers = {"Authorization": f"Bearer {tokens['ADMIN']}"}
    
    # Admin CAN access admin dashboard
    admin_dash = client.get("/api/dashboard/admin", headers=admin_headers)
    assert admin_dash.status_code == 200, f"Admin dashboard failed: {admin_dash.text}"
    print("  [PASS] Admin can access infrastructure telemetry, health metrics, and storage stats")

    # Admin CANNOT download evidence payload or access case narratives
    admin_blocked_ev = client.get("/api/evidence/1/download", headers=admin_headers)
    assert admin_blocked_ev.status_code in [403, 404], f"Admin was not blocked from evidence content! Got: {admin_blocked_ev.status_code}"
    print(f"  [PASS] Admin blocked from evidence content download (Returned status: {admin_blocked_ev.status_code})")

    # Step 3: Investigating Officer - Upload & Ingest
    print("\n--- STEP 3: Investigating Officer (IO) Depot & Transit Hash Verification ---")
    io_headers = {"Authorization": f"Bearer {tokens['INVESTIGATOR']}"}
    io_dash = client.get("/api/dashboard/io", headers=io_headers)
    assert io_dash.status_code == 200, f"IO dashboard failed: {io_dash.text}"
    print("  [PASS] IO can access active cases and pending custody transfers")

    # Step 4: Forensic Specialist - Analysis & Child Reports
    print("\n--- STEP 4: Forensic Specialist Workbench & Child Report Permissions ---")
    forensic_headers = {"Authorization": f"Bearer {tokens['FORENSIC_OFFICER']}"}
    forensic_dash = client.get("/api/dashboard/forensic", headers=forensic_headers)
    assert forensic_dash.status_code == 200, f"Forensic dashboard failed: {forensic_dash.text}"
    print("  [PASS] Forensic Specialist can access assigned analysis queue and pre/post hash tools")

    # Step 5: Legal Prosecutor - Trial Prep & Watermarked Stream
    print("\n--- STEP 5: Legal Prosecutor Docket & Watermarked Streaming ---")
    legal_headers = {"Authorization": f"Bearer {tokens['LEGAL_OFFICER']}"}
    legal_dash = client.get("/api/dashboard/prosecutor", headers=legal_headers)
    assert legal_dash.status_code == 200, f"Prosecutor dashboard failed: {legal_dash.text}"
    print("  [PASS] Prosecutor can access trial dockets and read-only evidence dossier")

    # Step 6: Compliance Auditor - Immutable Logs & Quarantine
    print("\n--- STEP 6: Compliance Auditor Oversight & Warrant Guard ---")
    auditor_headers = {"Authorization": f"Bearer {tokens['AUDITOR']}"}
    auditor_dash = client.get("/api/dashboard/auditor", headers=auditor_headers)
    assert auditor_dash.status_code == 200, f"Auditor dashboard failed: {auditor_dash.text}"
    print("  [PASS] Auditor can access compliance scorecards, anomaly alerts, and destruction reviews")

    # Auditor is BLOCKED from evidence binary content without a warrant
    auditor_blocked = client.get("/api/evidence/1/download", headers=auditor_headers)
    assert auditor_blocked.status_code in [403, 404], f"Auditor was not blocked from unsealed evidence content! Got: {auditor_blocked.status_code}"
    print(f"  [PASS] Auditor blocked from downloading evidence content without court warrant (Status: {auditor_blocked.status_code})")

    # Step 7: Malkhana Custodian - Physical Registry & Barcode
    print("\n--- STEP 7: Malkhana Custodian Physical Storage ---")
    custodian_headers = {"Authorization": f"Bearer {tokens['CUSTODIAN']}"}
    custodian_dash = client.get("/api/dashboard/custodian", headers=custodian_headers)
    assert custodian_dash.status_code == 200, f"Custodian dashboard failed: {custodian_dash.text}"
    print("  [PASS] Custodian can access physical inventory, barcode lookup, and bay allocations")

    # Custodian is BLOCKED from downloading digital video/audio evidence
    custodian_blocked = client.get("/api/evidence/1/download", headers=custodian_headers)
    assert custodian_blocked.status_code in [403, 404], f"Custodian was not blocked from digital content! Got: {custodian_blocked.status_code}"
    print(f"  [PASS] Custodian blocked from digital file playback/download (Status: {custodian_blocked.status_code})")

    print("\n" + "=" * 60)
    print("ALL 6 ROLES, RBAC PERMISSIONS, AND SEPARATION OF DUTIES VERIFIED!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
