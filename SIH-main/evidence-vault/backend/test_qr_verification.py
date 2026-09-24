"""Automated test suite for QR Code & Public Verification System (Mobile & Laptop).
Follows SPEC-verify.md: authenticity-only public surface, opaque IDs only.
"""
import base64
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_network_info():
    res = client.get("/api/public/network-info")
    assert res.status_code == 200, f"Network info failed: {res.text}"
    data = res.json()
    assert "lan_ip" in data, "lan_ip missing from network-info"
    assert "frontend_port" in data and data["frontend_port"] == 5173
    assert "mobile_base_url" in data
    assert "localhost_base_url" in data
    print(f"  [OK] Network info: LAN IP={data['lan_ip']}, Mobile Base={data['mobile_base_url']}")

def test_public_evidence_verification_by_opaque_id():
    ev1 = client.get("/api/public/verify/evidence/EV-2026-000001").json()["evidence"]
    assert ev1["evidence_id"], "expected a resolvable opaque evidence id"
    code = ev1["evidence_id"]
    res = client.get(f"/api/public/verify/evidence/{code}")
    assert res.status_code == 200, f"Failed verify evidence by ID: {res.text}"
    data = res.json()
    assert data["valid"] is True
    assert data["evidence"]["evidence_id"] == code
    assert data["evidence"]["integrity_status"] in ("VERIFIED", "PENDING", "TAMPERED")
    assert "sha256_hash" in data["evidence"]
    assert "blockchain" in data and "block_index" in data["blockchain"]
    assert "verification_url" in data and "/verify/evidence/" in data["verification_url"]
    assert "qr_code" in data and len(data["qr_code"]) > 100
    qr_bytes = base64.b64decode(data["qr_code"])
    assert qr_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "QR code is not a valid PNG image"

    # Authenticity-only surface: leaked fields must be absent.
    assert "case" not in data, "case metadata must not be public"
    assert "custody_trail" not in data, "custody trail must not be public"
    assert "original_filename" not in data["evidence"], "filename must not be public"
    assert "uploaded_by" not in data["evidence"], "uploader name must not be public"
    assert "current_custodian" not in data["evidence"], "custodian must not be public"
    assert "tx_id" not in data["blockchain"], "fabricated tx id must not be public"
    print(f"  [OK] Evidence '{code}' verified (authenticity-only): URL={data['verification_url']}")

def test_public_evidence_verification_by_code():
    res = client.get("/api/public/verify/evidence/EV-2026-000001")
    code = res.json()["evidence"]["evidence_id"]
    res = client.get(f"/api/public/verify/evidence/{code}?host=192.168.43.160:5173")
    assert res.status_code == 200
    data = res.json()
    assert data["evidence"]["evidence_id"] == code
    assert "192.168.43.160:5173/verify/evidence/" in data["verification_url"]
    print(f"  [OK] Evidence by string code '{code}' with custom mobile host verified: {data['verification_url']}")

def test_integer_identifiers_rejected():
    for path in ["/api/public/verify/evidence/1", "/api/public/verify/case/2"]:
        res = client.get(path)
        assert res.status_code == 404, f"integer identifier {path} must be rejected (enumeration), got {res.status_code}"
    print("  [OK] Bare integer identifiers rejected with 404 (no enumeration oracle)")

def test_public_case_verification():
    res = client.get("/api/public/verify/case/CASE-2026-001")
    assert res.status_code == 200, f"Case verification failed: {res.text}"
    data = res.json()
    assert data["valid"] is True
    assert "all_evidence_intact" in data
    assert "/verify/case/CASE-2026-001" in data["verification_url"]
    assert data["evidence_count"] > 0
    assert len(data["evidence_list"]) == data["evidence_count"]
    assert "qr_code" in data and len(data["qr_code"]) > 100

    assert "case" not in data, "case metadata must not be public"
    for item in data["evidence_list"]:
        assert "evidence_id" in item and "integrity_status" in item
        assert "verify_link" in item and "/verify/evidence/" in item["verify_link"]
        assert "original_filename" not in item, "filenames must not be public in case list"
        assert "sha256_hash" not in item, "hashes must not be public in case list"
    print(f"  [OK] Case 'CASE-2026-001' verified: {data['evidence_count']} evidence assets, authenticity-only")

def test_passport_route_scannable_qr():
    login_res = client.post("/api/auth/login", json={"email": "admin@evidencevault.local", "password": "demo123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    if login_data.get("mfa_required"):
        mfa_res = client.post("/api/auth/verify-mfa", json={
            "temp_token": login_data["temp_token"],
            "mfa_code": login_data["demo_totp_code"]
        })
        assert mfa_res.status_code == 200, f"MFA failed: {mfa_res.text}"
        token = mfa_res.json()["access_token"]
    else:
        token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ev = client.get("/api/evidence?limit=1", headers=headers).json()[0]
    ev_id = ev["id"]

    res = client.get(f"/api/evidence/{ev_id}/passport?host=192.168.43.160:5173", headers=headers)
    assert res.status_code == 200, f"Passport fetch failed: {res.text}"
    data = res.json()
    assert "verification_url" in data and data["verification_url"] is not None
    assert "/verify/evidence/" in data["verification_url"]
    assert "qr_code" in data and len(data["qr_code"]) > 100
    print(f"  [OK] Passport route returns scannable URL: {data['verification_url']}")

if __name__ == "__main__":
    print("==================================================")
    print("Running Universal QR Verification Test Suite")
    print("==================================================")
    test_network_info()
    test_public_evidence_verification_by_opaque_id()
    test_public_evidence_verification_by_code()
    test_integer_identifiers_rejected()
    test_public_case_verification()
    test_passport_route_scannable_qr()
    print("==================================================")
    print("[SUCCESS] ALL QR & PUBLIC VERIFICATION TESTS PASSED!")
    print("==================================================")