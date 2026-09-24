"""Identity module hardening test suite.

Run: python test_hardening.py
Covers per-user TOTP secrets, removal of the 123456 bypass, demo-code gating,
brute-force lockout, CORS, and secret fail-fast behavior.
"""
import os
import sys
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlalchemy
from fastapi.testclient import TestClient

from app.config import settings
from app.database import engine, init_db
from app.main import app
from app.security import mfa

client = TestClient(app)


@contextmanager
def demo_mode(value: bool):
    prev = settings.DEMO_MODE
    settings.DEMO_MODE = value
    try:
        yield
    finally:
        settings.DEMO_MODE = prev


def _fresh_secret():
    return mfa.generate_totp_secret()


def test_totp_secret_is_random_base32_and_unique():
    s1, s2 = _fresh_secret(), _fresh_secret()
    assert isinstance(s1, str) and s1
    assert s1 != s2, "per-user TOTP secrets must not be deterministic"
    assert set(s1) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


def test_verify_totp_accepts_current_code_and_rejects_wrong():
    secret = _fresh_secret()
    code = mfa.generate_current_totp(secret)
    assert mfa.verify_totp(secret, code) is True
    wrong = "0" + code[1:]
    assert mfa.verify_totp(secret, wrong) is False


def test_verify_totp_rejects_backdoor_code():
    secret = _fresh_secret()
    assert mfa.verify_totp(secret, "123456") is False, "123456 bypass must not work"


def test_verify_totp_rejects_malformed():
    secret = _fresh_secret()
    assert mfa.verify_totp(secret, "abc") is False
    assert mfa.verify_totp(secret, "") is False
    assert mfa.verify_totp(secret, "12345") is False


def test_users_table_has_totp_secret_column():
    init_db()
    with engine.connect() as conn:
        rows = conn.execute(sqlalchemy.text("PRAGMA table_info(users)")).fetchall()
    assert "totp_secret" in {row[1] for row in rows}, "users.totp_secret column missing"


def test_no_demo_totp_code_when_demo_mode_off():
    with demo_mode(False):
        res = client.post("/api/auth/login", json={
            "email": "investigator@evidencevault.local", "password": "demo123",
        })
    assert res.status_code == 200
    body = res.json()
    assert body.get("demo_totp_code") is None, "demo TOTP code must not leak when DEMO_MODE=false"


def test_guard_locks_after_max_attempts():
    from app.security.ratelimit import guard

    key = f"guard-test-{os.urandom(4).hex()}@vault.local|127.0.0.1"
    guard.clear(key)
    assert guard.blocked(key) is False
    for i in range(settings.RATE_LIMIT_MAX_ATTEMPTS - 1):
        assert guard.fail(key) is False, f"should not lock before max attempts (i={i})"
    assert guard.blocked(key) is False
    assert guard.fail(key) is True, "threshold attempt must lock the account"
    assert guard.blocked(key) is True, "account must be blocked after lockout"
    guard.clear(key)
    assert guard.blocked(key) is False


def test_login_endpoint_returns_429_after_repeated_failures():
    from app.security.ratelimit import guard

    email = "does-not-exist@vault.local"
    key = f"{email}|testclient"
    guard.clear(key)
    statuses = []
    for _ in range(settings.RATE_LIMIT_MAX_ATTEMPTS + 1):
        res = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
        statuses.append(res.status_code)
    assert statuses[: settings.RATE_LIMIT_MAX_ATTEMPTS - 1] == [401] * (settings.RATE_LIMIT_MAX_ATTEMPTS - 1)
    assert all(s == 429 for s in statuses[settings.RATE_LIMIT_MAX_ATTEMPTS - 1:]), \
        f"expected 429 from the threshold attempt onward, got {statuses}"
    guard.clear(key)


def test_cors_rejects_unlisted_origin():
    res = client.get("/", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in res.headers


def test_cors_allows_configured_origin():
    origin = settings.CORS_ORIGINS.split(",")[0].strip()
    res = client.get("/", headers={"Origin": origin})
    assert res.headers.get("access-control-allow-origin") == origin


def test_config_fails_fast_on_dev_secrets_in_production_mode():
    from app.config import Settings

    try:
        Settings(DEMO_MODE=False, SECRET_KEY="dev-secret-key-change-in-production",
                 ENCRYPTION_KEY="", _env_file=None)
        raise AssertionError("expected RuntimeError for dev SECRET_KEY in production mode")
    except RuntimeError:
        pass


def test_config_allows_dev_secrets_in_demo_mode():
    from app.config import Settings

    Settings(DEMO_MODE=True, SECRET_KEY="dev-secret-key-change-in-production",
             ENCRYPTION_KEY="", _env_file=None)


def main():
    print("==========================================")
    print("Running EvidenceVault Identity Hardening Tests")
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
    print("[SUCCESS] ALL IDENTITY HARDENING TESTS PASSED")
    print("==========================================")


if __name__ == "__main__":
    main()