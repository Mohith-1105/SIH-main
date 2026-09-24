"""Access module test suite — rank-level hierarchical scoping.

Run: python test_access.py
Expected: python seed.py must have been run first (seeded accounts + rank_level).

Covers: rank 1-2 own-cases-only, rank 3-4 own + same-department, rank 5+ / ADMIN
unrestricted; evidence endpoint scoping; dashboard + search scoping; rank schema.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlalchemy
from fastapi.testclient import TestClient

from app.database import engine, init_db, SessionLocal
from app.main import app
from app.models.user import User
from app.security.auth import hash_password
from app.security.mfa import generate_totp_secret

client = TestClient(app)

RUN_TOKEN = f"acctok{os.getpid()}{os.urandom(4).hex()}"
LOW_TOKEN = f"lowonly{os.getpid()}{os.urandom(4).hex()}"

FIX = {}


def _upsert_user(email, role, rank_level, department):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u is None:
            u = User(email=email, full_name=email.split("@")[0],
                     hashed_password=hash_password("demo123"), role=role,
                     rank_level=rank_level, department=department,
                     badge_number="", totp_secret=generate_totp_secret())
            db.add(u)
        else:
            u.role = role
            u.rank_level = rank_level
            u.department = department
            u.totp_secret = u.totp_secret or generate_totp_secret()
        db.commit()
        db.refresh(u)
        return u
    finally:
        db.close()


def _login_token(user):
    r = client.post("/api/auth/login", json={"email": user.email, "password": "demo123"})
    assert r.status_code == 200, f"login failed for {user.email}: {r.text}"
    body = r.json()
    assert body.get("demo_totp_code"), "tests need DEMO_MODE=true"
    r2 = client.post("/api/auth/verify-mfa", json={
        "temp_token": body["temp_token"], "mfa_code": body["demo_totp_code"],
    })
    assert r2.status_code == 200, f"mfa failed for {user.email}: {r2.text}"
    return r2.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _fixture():
    """Build users + cases + evidence once; return handers for all assertions."""
    if FIX.get("ready"):
        return FIX

    low = _upsert_user("access-low@vault.local", "INVESTIGATOR", 2, "Alpha Unit")
    mid = _upsert_user("access-mid-a@vault.local", "INVESTIGATOR", 3, "Beta Unit")
    mid2 = _upsert_user("access-mid-b@vault.local", "INVESTIGATOR", 3, "Beta Unit")
    gamma_user = _upsert_user("access-mid-c@vault.local", "INVESTIGATOR", 3, "Gamma Unit")
    high = _upsert_user("access-high@vault.local", "FORENSIC_OFFICER", 5, "Forensic Lab")
    admin = _upsert_user("access-admin@vault.local", "ADMIN", 6, "Administration")

    t_low, t_mid, t_mid2, t_gamma, t_high, t_admin = (
        _login_token(u) for u in (low, mid, mid2, gamma_user, high, admin)
    )

    def create_case(token, title, description="access-fixture"):
        r = client.post("/api/cases", json={
            "title": title, "description": description, "case_type": "GENERAL",
            "priority": "LOW",
        }, headers=_auth(token))
        assert r.status_code == 200, f"case create failed: {r.text}"
        return r.json()

    c_low = create_case(t_low, f"LowRank {LOW_TOKEN}", LOW_TOKEN)
    c_beta = create_case(t_mid, f"BetaCase {RUN_TOKEN}")
    c_gamma = create_case(t_gamma, f"GammaCase {RUN_TOKEN}")

    # Evidence inside c_low (uploaded by low, who owns the case)
    r = client.post("/api/evidence/upload",
                    files={"file": (f"{RUN_TOKEN}.txt", b"access evidence bytes", "text/plain")},
                    data={"case_id": str(c_low["id"]), "description": LOW_TOKEN},
                    headers=_auth(t_low))
    assert r.status_code == 200, f"evidence upload failed: {r.text}"
    ev = r.json()

    FIX.update(
        ready=True,
        low_id=low.id, mid_id=mid.id, mid2_id=mid2.id,
        gamma_id=gamma_user.id, high_id=high.id, admin_id=admin.id,
        t_low=t_low, t_mid=t_mid, t_mid2=t_mid2, t_gamma=t_gamma, t_high=t_high, t_admin=t_admin,
        c_low=c_low, c_beta=c_beta, c_gamma=c_gamma, ev=ev,
    )
    return FIX


# --- Rank schema ---
def test_users_table_has_rank_level_column():
    init_db()
    with engine.connect() as conn:
        rows = conn.execute(sqlalchemy.text("PRAGMA table_info(users)")).fetchall()
    assert "rank_level" in {row[1] for row in rows}, "users.rank_level column missing"


def test_seeded_users_get_role_default_ranks():
    db = SessionLocal()
    try:
        for email, role, rank in [
            ("admin@evidencevault.local", "ADMIN", 6),
            ("investigator@evidencevault.local", "INVESTIGATOR", 3),
            ("forensic@evidencevault.local", "FORENSIC_OFFICER", 5),
            ("legal@evidencevault.local", "LEGAL_OFFICER", 5),
            ("auditor@evidencevault.local", "AUDITOR", 6),
            ("constable@evidencevault.local", "INVESTIGATOR", 2),
        ]:
            u = db.query(User).filter(User.email == email).first()
            if u is None:
                continue
            assert u.rank_level == rank, f"{email}: expected rank {rank}, got {u.rank_level}"
    finally:
        db.close()


def test_login_returns_rank_level():
    f = _fixture()
    r = client.get("/api/auth/me", headers=_auth(f["t_low"]))
    assert r.status_code == 200
    assert r.json()["rank_level"] == 2


def test_usercreate_rejects_out_of_range_rank():
    f = _fixture()
    r = client.post("/api/users", json={
        "email": f"badrank-{RUN_TOKEN}@vault.local", "full_name": "Bad",
        "password": "demo123", "role": "INVESTIGATOR", "rank_level": 0,
    }, headers=_auth(f["t_admin"]))
    assert r.status_code == 422, f"rank 0 should be rejected, got {r.status_code}"
    r = client.post("/api/users", json={
        "email": f"badrank2-{RUN_TOKEN}@vault.local", "full_name": "Bad",
        "password": "demo123", "role": "INVESTIGATOR", "rank_level": 7,
    }, headers=_auth(f["t_admin"]))
    assert r.status_code == 422, f"rank 7 should be rejected, got {r.status_code}"


# --- Case scoping ---
def test_low_rank_sees_only_own_cases():
    f = _fixture()
    r = client.get("/api/cases", headers=_auth(f["t_low"]))
    ids = [c["id"] for c in r.json()]
    assert f["c_low"]["id"] in ids
    assert f["c_beta"]["id"] not in ids
    assert f["c_gamma"]["id"] not in ids


def test_low_rank_denied_foreign_case():
    f = _fixture()
    r = client.get(f'/api/cases/{f["c_beta"]["id"]}', headers=_auth(f["t_low"]))
    assert r.status_code == 403
    r = client.get(f'/api/cases/{f["c_gamma"]["id"]}', headers=_auth(f["t_low"]))
    assert r.status_code == 403


def test_mid_rank_sees_own_and_same_department():
    f = _fixture()
    r = client.get("/api/cases", headers=_auth(f["t_mid"]))
    ids = [c["id"] for c in r.json()]
    assert f["c_beta"]["id"] in ids          # own
    assert f["c_low"]["id"] not in ids       # other department
    assert f["c_gamma"]["id"] not in ids     # other department
    r2 = client.get(f'/api/cases/{f["c_beta"]["id"]}', headers=_auth(f["t_mid2"]))
    assert r2.status_code == 200, "same-department officer should see the case"


def test_mid_rank_denied_other_department():
    f = _fixture()
    r = client.get(f'/api/cases/{f["c_gamma"]["id"]}', headers=_auth(f["t_mid"]))
    assert r.status_code == 403


def test_high_rank_and_admin_see_all():
    f = _fixture()
    for token in (f["t_high"], f["t_admin"]):
        r = client.get("/api/cases", headers=_auth(token))
        ids = [c["id"] for c in r.json()]
        for cid in (f["c_low"]["id"], f["c_beta"]["id"], f["c_gamma"]["id"]):
            assert cid in ids, "rank 5+ / ADMIN must see all cases"
        r2 = client.get(f'/api/cases/{f["c_low"]["id"]}', headers=_auth(token))
        assert r2.status_code == 200


def test_list_case_evidence_scoped():
    f = _fixture()
    r = client.get(f'/api/cases/{f["c_low"]["id"]}/evidence', headers=_auth(f["t_low"]))
    assert r.status_code == 200
    r = client.get(f'/api/cases/{f["c_low"]["id"]}/evidence', headers=_auth(f["t_mid"]))
    assert r.status_code == 403


# --- Evidence scoping ---
def test_evidence_list_scoped():
    f = _fixture()
    r = client.get("/api/evidence", headers=_auth(f["t_low"]))
    ids = [e["id"] for e in r.json()]
    assert f["ev"]["id"] in ids
    r = client.get("/api/evidence", headers=_auth(f["t_mid"]))
    ids = [e["id"] for e in r.json()]
    assert f["ev"]["id"] not in ids, "evidence in another department's case must be hidden"


def test_evidence_read_endpoints_denied_out_of_scope():
    f = _fixture()
    ev = f["ev"]["id"]
    paths = [f"/api/evidence/{ev}", f"/api/evidence/{ev}/download",
             f"/api/evidence/{ev}/passport", f"/api/evidence/{ev}/versions",
             f"/api/evidence/{ev}/custody", f"/api/evidence/{ev}/graph"]
    for path in paths:
        r = client.get(path, headers=_auth(f["t_mid"]))
        assert r.status_code == 403, f"{path} should be 403 for out-of-scope evidence, got {r.status_code}"
    r = client.post(f"/api/evidence/{ev}/verify", headers=_auth(f["t_mid"]))
    assert r.status_code == 403
    r = client.post(f"/api/evidence/{ev}/transfer",
                    json={"target_user_id": f["mid2_id"], "notes": "x"},
                    headers=_auth(f["t_mid"]))
    assert r.status_code == 403
    r = client.post(f"/api/evidence/{ev}/versions",
                    files={"file": ("x.txt", b"x", "text/plain")},
                    data={"change_reason": "x"}, headers=_auth(f["t_mid"]))
    assert r.status_code == 403


def test_evidence_read_endpoints_allowed_in_scope():
    f = _fixture()
    ev = f["ev"]["id"]
    for token in (f["t_low"], f["t_high"]):
        assert client.get(f"/api/evidence/{ev}", headers=_auth(token)).status_code == 200
        assert client.get(f"/api/evidence/{ev}/download", headers=_auth(token)).status_code == 200


def test_upload_to_hidden_case_denied():
    f = _fixture()
    r = client.post("/api/evidence/upload",
                    files={"file": ("x.txt", b"should be blocked", "text/plain")},
                    data={"case_id": str(f["c_beta"]["id"]), "description": "x"},
                    headers=_auth(f["t_low"]))
    assert r.status_code == 403, "upload to a case outside scope must be forbidden"


# --- Dashboard + search scoping ---
def test_dashboard_counts_scoped():
    f = _fixture()
    r = client.get("/api/dashboard", headers=_auth(f["t_low"]))
    body = r.json()
    case_list = client.get("/api/cases", headers=_auth(f["t_low"])).json()
    ev_list = client.get("/api/evidence", headers=_auth(f["t_low"])).json()
    assert body["total_cases"] == len(case_list)
    assert body["total_evidence"] == len(ev_list)
    r_admin = client.get("/api/dashboard", headers=_auth(f["t_high"])).json()
    assert r_admin["total_cases"] >= body["total_cases"]
    assert r_admin["verified_evidence"] >= body["verified_evidence"]


def test_search_scoped():
    f = _fixture()
    r = client.get("/api/search", params={"q": LOW_TOKEN}, headers=_auth(f["t_low"]))
    assert len(r.json()["cases"]) == 1 and r.json()["cases"][0]["id"] == f["c_low"]["id"]
    assert len(r.json()["evidence"]) == 1 and r.json()["evidence"][0]["id"] == f["ev"]["id"]
    r = client.get("/api/search", params={"q": LOW_TOKEN}, headers=_auth(f["t_mid"]))
    assert r.json()["cases"] == [], "another department's case must not appear in search"
    assert r.json()["evidence"] == [], "another department's evidence must not appear in search"


def main():
    print("==========================================")
    print("Running EvidenceVault Access Scoping Tests")
    print("==========================================")
    init_db()
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        name = t.__name__
        print(f"Running {name}...", end=" ")
        try:
            t()
            print("PASSED [OK]")
        except AssertionError as e:
            failed += 1
            print(f"FAILED: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR: {type(e).__name__}: {e}")
    print("==========================================")
    if failed:
        print(f"[FAILURE] {failed} test(s) failed")
        sys.exit(1)
    print("[SUCCESS] ALL ACCESS SCOPING TESTS PASSED")
    print("==========================================")


if __name__ == "__main__":
    main()