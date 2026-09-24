# Spec: `identity` — Authentication Hardening

Module in Capability Map: `identity`. Depends on: none. Feeds `access` (rank) and `verify`.

## Objective

Make EvidenceVault login genuinely secure and per-user, fixing the confirmed identity flaws in the cloned MVP without re-architecting the app:

1. MFA backdoor: `app/security/mfa.py:57` accepts `"123456"` for any account — remove.
2. Shared, deterministic TOTP secret derived from `SECRET_KEY` + email (`mfa.py:27-31`) — replace with a per-user secret column (`totp_secret`), RFC 6238 semantics unchanged.
3. Live 6-digit TOTP code returned in the login response (`app/routes/auth.py:160 demo_totp_code`, always, even outside demo) — return it only when `DEMO_MODE` is explicitly enabled (default off).
4. No brute-force protection — add rate limiting + per-account lockout on `/api/auth/login` and `/api/auth/verify-mfa`.
5. CORS wide open (`app/main.py` allow_origins `["*"]`, credentials True) — restrict to configured origins.
6. Committed secrets: `backend/.env` is in git (`SECRET_KEY=evidencevault-dev-secret-key-change-in-production-2026`, and the generated `ENCRYPTION_KEY` auto-persists into `.env` via `security/encryption.py`) — untrack it, and fail fast in non-demo mode if `SECRET_KEY`/`ENCRYPTION_KEY` are the dev defaults.
7. Frontend MFA cheese: "Use 123456" button (`LoginPage.tsx:305-310`) — remove; stop pre-showing the TOTP secret path when demo code is disabled.

Non-goals: no session/refresh-token overhaul (JWT stays), no DB change beyond the `totp_secret` column, no per-evidence crypto (that's out of the approved map).

## Tech Stack

Python 3, FastAPI, SQLAlchemy, `python-jose` (JWT HS256), `passlib[bcrypt]`, `cryptography`, `pydantic-settings`. TOTP via stdlib `hmac`/`hashlib` (already present in `mfa.py`). Ratelimiting/lockout with an in-memory store — no new dependencies.

## Commands

```
cd SIH-main/evidence-vault/backend
pip install -r requirements.txt
python seed.py                      # reseed DB + generate per-user TOTP secrets
uvicorn app.main:app --reload       # API on :8000
python test_phase2.py               # existing suite must stay green
python test_hardening.py            # new identity-module suite
```

Frontend:
```
cd SIH-main/evidence-vault/frontend
npm install
npm run build   # tsc -b && vite build
npm run lint
```

## Project Structure

```
backend/app/security/   → mfa.py (per-user secret verification), auth.py (unchanged JWT/RBAC),
                          ratelimit.py (NEW: in-memory limiter + lockout)
backend/app/routes/auth.py   → gate demo_totp_code, wire rate-limit/lockout
backend/app/config.py        → SECRET_KEY/ENCRYPTION_KEY fail-fast, CORS_ORIGINS, DEMO_MODE default False
backend/app/main.py          → use CORS_ORIGINS
backend/app/models/user.py   → add totp_secret, failed_attempts columns
backend/app/database.py      → migration helper used to add the columns
backend/seed.py              → per-user random TOTP secrets; expose QR/provisioning in demo mode only
backend/test_hardening.py    → new script-style suite (matches existing test_phase2.py style)
frontend/src/pages/LoginPage.tsx → drop 123456 button; drop pre-filled code when not demo
```

## Code Style

Match the existing module conventions — plain functions, docstrings, `app.` absolute imports, FastAPI `Depends` for DB/rules. Example (existing style, `mfa.py:34-44`):

```python
def generate_current_totp(secret_base32: str, interval: int = TOTP_INTERVAL) -> str:
    """Generate current 6-digit TOTP code according to RFC 6238."""
    counter = int(time.time() // interval)
    padded = secret_base32 + "=" * ((8 - len(secret_base32) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    ...
```

New `verify_user_mfa` signature: `verify_totp(secret_base32: str, code: str, window: int = 1) -> bool` — the caller passes the stored per-user secret (already in memory/logic in routes). Keep the `-1`-audit-log, `_extract_client_ip`, `_detect_device` conventions as-is.

## Testing Strategy

Script-style suites run with `python test_*.py`, as the repo already does (FastAPI `TestClient`). Coverage expectations for `identity`:

- `123456` no longer verifies MFA on any account.
- `/api/auth/login` response has no `demo_totp_code` when `DEMO_MODE=false` (the test overrides settings/env).
- After N failed logins (configurable, default 5) in window, the account returns 429/423 and further attempts are blocked until cooldown.
- CORS: a request with an origin not in `CORS_ORIGINS` gets no `Access-Control-Allow-Origin` header.
- Seeds: each user's `totp_secret` is unique (per-user, not derived from email/key).
- `test_phase2.py` remains green (both suites use seeded demo credentials; demo path still returns the code only when `DEMO_MODE` is on).

## Boundaries

- **Always:** reject unknown/bad TOTP immediately; hash passwords with bcrypt; log failed attempts to `audit_logs`; fail closed — any config/secret error in non-demo mode aborts startup; keep demo accounts working when `DEMO_MODE` is on (a hackathon judge must still log in).
- **Ask first:** dropping the demo-credential login path entirely; schema changes beyond the two new `users` columns; changing the TOTP window/interval.
- **Never:** commit `.env` or any secret; return real TOTP codes/secrets to clients outside demo mode; log tokens, passwords, or codes.

## Success Criteria

- [x] `mfa.py` has no bypass constant; `verify_totp` takes the user's stored secret.
- [x] `users.totp_secret` column exists and each seeded user has an independent, random secret.
- [x] `demo_totp_code` appears in responses only when `DEMO_MODE=true` (default false).
- [x] Repeated failed password/MFA attempts trigger lockout; rate limiting is applied to login endpoints.
- [x] CORS rejects non-configured origins.
- [x] `backend/.env` untracked from git; `config.py` fails fast on default secrets in non-demo mode.
- [x] `LoginPage.tsx` no longer offers the `123456` bypass or auto-fills the TOTP code when demo code is disabled.
- [x] `python test_phase2.py` and `python test_hardening.py` pass.

## Open Questions

1. Re-encryption on `ENCRYPTION_KEY` rotation: the 12 committed demo files in `storage/evidence/` are Fernet-encrypted with the old key. Plan is to reseed via `seed.py` (re-uploads demo evidence under the new key) — confirm reseeding demo data is acceptable rather than migrating files.
2. `ENCRYPTION_KEY` auto-persist in `encryption.py` writes to `.env` — keep that behavior in demo mode, or switch to memory-only + explicit .env? (dev convenience vs. surprise writes to a now-untracked file)