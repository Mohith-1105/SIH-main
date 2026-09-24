# Implementation Plan: `identity` — Authentication Hardening

Spec: `SPEC-identity.md`. Capability map: `CAPABILITY-MAP.md`. Scope: `identity` module only.

## Overview

Harden EvidenceVault login: per-user TOTP secrets (killing the `123456` backdoor and the derived-from-SECRET_KEY seed), gate the demo TOTP leak behind `DEMO_MODE`, add brute-force rate limiting + account lockout, lock CORS to configured origins, and untrack the committed `.env` with fail-fast secret defaults. JWT/stateless session unchanged (non-goal). DB stays SQLite.

## Architecture Decisions

1. **Per-user TOTP secret stored in `users.totp_secret`.** `verify_totp(secret, code)` replaces `verify_user_mfa(email, code)`; callers pass the stored secret. New `generate_totp_secret()` uses `secrets` (cryptographically random base32). This removes both the shared-seed and the bypass.
2. **Rate limiting + lockout in an in-memory store** (`app/security/ratelimit.py`), no new dependency. `login` and `verify-mfa` check a per-IP+per-account sliding window; after N failed attempts the account is locked until cooldown. `# ponytail:` note — single-process in-memory; move to Redis/DB when multi-instance.
3. **`demo_totp_code` and frontend auto-fill gated on `settings.DEMO_MODE`** (default False in `config.py`; `.env`/`.env.example` may set True for the judge demo). Seed users keep `demo123` so the hackathon demo still works.
4. **CORS origins from settings** (`CORS_ORIGINS`, comma-separated env; default `http://localhost:5173,http://127.0.0.1:5173`). No wildcard with credentials.
5. **Secrets fail-fast:** in non-demo mode, startup aborts if `SECRET_KEY` or `ENCRYPTION_KEY` equals the dev defaults or is empty. `.env` untracked from git via root `.gitignore` + `git rm --cached`. Fresh local keys; demo storage reseeded so the 12 files re-encrypt under the new key.

## Task List

### Task 1: Per-user TOTP secret storage + verification

**Description:** Add `totp_secret` to `users` (model + migration), replace derived-secret generation with random per-user secrets, and change verification to take the stored secret. Remove the `"123456"` bypass from `mfa.py`. Backfill existing DB rows with generated secrets.

**Acceptance criteria:**
- [x] `users.totp_secret` column exists (model + `migrate_sqlite`); existing rows backfilled
- [x] `mfa.py` has no `"123456"` path and no `get_user_totp_secret(email)`; `verify_totp(secret, code)` and `generate_totp_secret()` exist
- [x] `routes/auth.py` verifies with `user.totp_secret`; `users.py` and `seed.py` generate a secret per new user

**Verification:**
- [x] `python test_phase2.py` passes (login without bypass)
- [x] Manual: `python test_hardening.py::test_no_backdoor`-style check (see Task 6)

**Dependencies:** None

**Files likely touched:** `app/models/user.py`, `app/database.py`, `app/security/mfa.py`, `app/routes/auth.py`, `app/routes/users.py`, `seed.py`

**Estimated scope:** Medium (5-6 files)

### Task 2: Gate the demo TOTP leak + frontend cheese

**Description:** Return `demo_totp_code` only when `DEMO_MODE` is enabled (now default False); remove the "Use 123456" button and unconditional code auto-fill from `LoginPage.tsx`, showing the code only in demo mode.

**Acceptance criteria:**
- [x] With `DEMO_MODE=false`, `/api/auth/login` response contains no `demo_totp_code`
- [x] With `DEMO_MODE=true`, demo flow still returns it
- [x] `LoginPage.tsx`: no `123456` button, no hardcoded demo-code prefills

**Verification:**
- [x] `npm run build` (frontend) passes
- [x] `python test_phase2.py` still green (demo mode)

**Dependencies:** Task 1

**Files likely touched:** `app/routes/auth.py`, `app/config.py`, `frontend/src/pages/LoginPage.tsx`, `.env`/.env.example `DEMO_MODE`

**Estimated scope:** Small (2-4 files)

### Checkpoint: after Tasks 1-2
- [x] `test_phase2.py` and `test_qr_verification.py` pass with demo mode on
- [x] Frontend builds with `npm run build`
- [x] Manual: login as `investigator@evidencevault.local` / `demo123` completes MFA in demo mode
- [x] Human review before proceeding

### Task 3: Brute-force rate limiting + account lockout

**Description:** Add `app/security/ratelimit.py` (in-memory sliding window + lockout) and enforce it on `/api/auth/login` and `/api/auth/verify-mfa` (per IP + per account). Configurable via settings (`RATE_LIMIT_MAX_ATTEMPTS`, `RATE_LIMIT_WINDOW_SECONDS`, `LOCKOUT_SECONDS`).

**Acceptance criteria:**
- [x] N (default 5) failed password attempts on an account within window → further attempts rejected (429) until cooldown
- [x] Lockout/limit works for both login and MFA verification
- [x] Audit log records BLOCKED/THROTTLED events (failures already logged)

**Verification:**
- [x] `python test_hardening.py` (Task 6) includes lockout case, passes

**Dependencies:** Task 1

**Files likely touched:** `app/security/ratelimit.py` (new), `app/routes/auth.py`, `app/config.py`

**Estimated scope:** Medium (3 files)

### Task 4: CORS lockdown + secret handling + git hygiene

**Description:** CORS from `settings.CORS_ORIGINS`; fail-fast in non-demo when secrets are the dev defaults/empty; add repo `.gitignore` covering `.env` and `*.db`; `git rm --cached backend/.env`; regenerate `.env` with fresh keys and update `.env.example`; reseed the DB/storage so demo evidence re-encrypts under the new `ENCRYPTION_KEY`.

**Acceptance criteria:**
- [x] `app/main.py` uses `settings.CORS_ORIGINS`; a request with a disallowed `Origin` gets no `Access-Control-Allow-Origin`
- [x] Non-demo startup raises if `SECRET_KEY`/`ENCRYPTION_KEY` are dev defaults or empty; demo mode still boots
- [x] `git ls-files` no longer lists `backend/.env`; `.env` listed in a committed `.gitignore`
- [x] Fresh keys generated; demo uploads/downloads work after reseed (files decrypt under new key)

**Verification:**
- [x] `python test_hardening.py` (CORS + fail-fast cases), `python test_phase2.py`
- [x] `fastapi.main:app` boots in demo mode; `/docs` loads

**Dependencies:** None (parallel-safe with Task 3)

**Files likely touched:** `app/main.py`, `app/config.py`, `app/database.py` (no), `seed.py`, `.gitignore` (new, repo root), `backend/.env`, `backend/.env.example`

**Estimated scope:** Medium (4-6 files)

### Checkpoint: after Tasks 3-4
- [x] New `test_hardening.py` green; `test_phase2.py` green
- [x] CORS disallowed-origin manually verified via curl
- [x] `.env` untracked; no secrets in `git status`/diff
- [x] Human review before proceeding

### Task 5: `test_hardening.py` suite + full regression

**Description:** Script-style suite (matches repo convention) asserting every identity success criterion: no backdoor, no demo code when demo off, per-user secret independence, lockout, CORS, fail-fast.

**Acceptance criteria:**
- [x] Suite covers: `123456` rejected; no `demo_totp_code` when `DEMO_MODE=false`; seeded `totp_secret`s unique; lockout after 5 fails; CORS rejected origin; config fail-fast
- [x] All existing test scripts (`test_phase2.py`, `test_qr_verification.py`) still pass

**Verification:**
- [x] `python test_hardening.py && python test_phase2.py && python test_qr_verification.py`

**Dependencies:** Tasks 1-4

**Files likely touched:** `test_hardening.py` (new)

**Estimated scope:** Medium (1 file + fixtures)

### Checkpoint: Complete
- [x] All SPEC-identity Success Criteria met
- [x] Backend + frontend run, demo login + MFA works
- [x] Ready for `access` module spec

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `ENCRYPTION_KEY` rotation makes committed demo files undecryptable | Med | Reseed storage via `seed.py` during Task 4; verify download flow |
| Gating `demo_totp_code` breaks existing tests that read it | Med | Tests run with demo mode on (`.env`), keep behavior demo-gated |
| In-memory lockout lost on restart | Low | Acceptable for MVP; `ponytail:` comment points at DB/Redis upgrade path |
| Rank field added later (`access` module) collides with JWT/role payloads | Low | `identity` only touches `totp_secret`; rank lands in `access` |

## Open Questions

None remaining (Q1 reseed + Q2 .env-write behavior approved).

---

# Implementation Plan: `access` — Rank-Level Hierarchical Access

Spec: `SPEC-access.md`. Capability map: `CAPABILITY-MAP.md`. Scope: `access` module only.

## Overview

Add rank-level data scoping: `users.rank_level` (1–6) decides which cases/evidence a user may see; the existing 5 `role` permission sets still decide what they may do. Rewrite the currently-dead `visible_case_ids` / `ensure_case_access` / `ensure_evidence_access` in `app/security/auth.py` into the single enforcement point, then wire them into every case/evidence read route, evidence upload, dashboard aggregates, and global search. Evidence visibility = visibility of its `case_id`. Ranks 1–2 see only their own cases, 3–4 their own + same-`department`, 5+ and `ADMIN` all.

## Architecture Decisions

1. **One numeric `users.rank_level` column** (default 3), backfilled by role defaults (`ADMIN=6, AUDITOR=6, FORENSIC_OFFICER=5, LEGAL_OFFICER=5, INVESTIGATOR=3`) via a `ROLE_DEFAULT_RANK` map in `auth.py`. No hierarchy table, no per-case ACL, no unit table — a user's `department` string is the unit proxy (strict equality).
2. **`visible_case_ids(user, db)` returns `list[int]` or `None`** (None = unrestricted). Ranks 1–2: `assigned_user_id==me OR created_by==me`. Ranks 3–4: that PLUS cases assigned/created by any user in my `department`. Rank 5+ or `ADMIN`: `None`. Callers apply `Case.id.in_(ids)` / `Evidence.case_id.in_(ids)` to list queries and `ensure_*_access` to detail routes. 403 (not 404) on foreign resources once authenticated.
3. **Evidence scoping collapses to case scoping.** The old role-based exemptions for `FORENSIC_OFFICER`/`LEGAL_OFFICER`/`AUDITOR` in `ensure_evidence_access` are deleted — rank subsumes them (they are rank 5+).
4. **Non-admin cannot raise rank.** `users.write` is ADMIN-only today, closing elevation by RBAC; no second check (noted in `users.py`, not added).
5. **Seed gains a 6th demo user** — a rank-2 constable in a different department — so the hierarchy (hide/show) is demonstrable from the login screen. Tests create additional rank/department users via direct DB writes for the scoping matrix.

## Task List

### Task A: `rank_level` plumbing (model → migration → schemas → routes → seed)

**Description:** Add `rank_level` to `User` (default 3) and to the `migrate_sqlite()` `users` additions with role-based backfill (lazy-import `ROLE_DEFAULT_RANK` to avoid import cycles, like `database.py:70` does for `generate_totp_secret`). Add `rank_level` to `UserOut` and `UserCreate` (validation `ge=1, le=6`; default from role or 3). Pass it in `routes/users.py` create and `seed.py` (5 users by role default + the new constable rank 2). Define `ROLE_DEFAULT_RANK` and `user_rank()` in `auth.py`.

**Acceptance criteria:**
- [x] `users.rank_level` column exists; backfilled by role; constable seed user present with rank 2
- [x] `UserOut`/`UserCreate` carry validated `rank_level`
- [x] `create_user` persists `rank_level`

**Verification:**
- [x] `python seed.py`; DB check via test in `test_access.py`

**Dependencies:** None (foundation for the rest)

**Files likely touched:** `app/models/user.py`, `app/database.py`, `app/schemas/__init__.py`, `app/routes/users.py`, `seed.py`, `app/security/auth.py` (map only)

**Estimated scope:** Small-medium (6 files)

### Task B: `test_access.py` scoping matrix (TDD — RED)

**Description:** New script-style suite. Creates users by writing rows directly (known `totp_secret`), logs in via the demo path, and asserts the full rank matrix against cases/evidence created for the fixtures.

**Acceptance criteria:**
- [x] Rank 1–2: only own cases in list; foreign case get → 403
- [x] Rank 3–4: own + same-`department` cases; other-department get → 403
- [x] Rank 5+ / ADMIN: unrestricted
- [x] Evidence endpoints (get/download/passport/verify/transfer/versions/custody/graph) 403 on out-of-scope evidence; upload to hidden case → 403
- [x] Dashboard counts + case-status distribution and `/search` scoped
- [x] Schema: `rank_level` round-trips; out-of-range rejected

**Verification:**
- [x] Suite FAILS against current code (RED) before implementation

**Dependencies:** Task A (users can hold rank)

**Files likely touched:** `test_access.py` (new)

**Estimated scope:** Medium (1 file)

### Task C: Rewrite scoping core in `auth.py`

**Description:** Replace `visible_case_ids` / `ensure_case_access` / `ensure_evidence_access` (function bodies at `auth.py:152-184`) with the rank rules; delete role-specific branches. Add `case_scope_expr(user, db, column)` helper for list-query filtering.

**Acceptance criteria:**
- [x] `visible_case_ids` returns `None` for ADMIN/rank 5+; `list[int]` otherwise per rules
- [x] `ensure_evidence_access` routes through the evidence's case
- [x] No `FORENSIC_OFFICER`/`LEGAL_OFFICER`/`AUDITOR` special-cases remain

**Verification:**
- [x] `test_access.py` scoping assertions pass for permitted/denied access

**Dependencies:** Task A

**Files likely touched:** `app/security/auth.py`

**Estimated scope:** Small (1 file)

### Task D: Wire case routes

**Description:** In `cases.py`: `list_cases` filters `Case.id.in_(ids)` when scoped; `get_case`, `update_case`, `get_case_flow`, `advance_case_stage`, `list_case_evidence` call `ensure_case_access` (after the 404 check).

**Acceptance criteria:**
- [x] List reflects scope; detail routes 403 on foreign cases
- [x] `list_case_evidence` on a hidden case → 403

**Verification:**
- [x] `test_access.py` case block green

**Dependencies:** Task C

**Files likely touched:** `app/routes/cases.py`

**Estimated scope:** Small (1 file)

### Task E: Wire evidence routes

**Description:** In `evidence.py`: `list_evidence` filters `Evidence.case_id.in_(ids)` when scoped; `upload_evidence` calls `ensure_case_access` on the target case; `get_evidence`, `download_evidence`, `get_passport`, `verify_evidence`, `transfer_custody`, `create_version`, `get_versions`, `get_custody`, `get_evidence_graph` call `ensure_evidence_access` (after 404).

**Acceptance criteria:**
- [x] All read/download/transfer/version/custody/graph routes enforce evidence scope
- [x] Upload to a case outside scope → 403

**Verification:**
- [x] `test_access.py` evidence block green

**Dependencies:** Task C

**Files likely touched:** `app/routes/evidence.py`

**Estimated scope:** Medium (1 file)

### Task F: Wire dashboard + search + reports

**Description:** In `dashboard.py`: scope `total_cases`, `total_evidence`, `verified`, `pending`, `case_status_distribution`, `evidence_by_category`, `evidence_over_time`, risk counts/distribution, and `high_risk_alerts` to visible case ids; `/search` scopes cases/evidence results. `reports.py` evidence report route calls `ensure_evidence_access`.

**Acceptance criteria:**
- [x] Rank 1–2 dashboard counts reflect only visible cases
- [x] `/search` returns only visible cases/evidence
- [x] Evidence report on hidden evidence → 403

**Verification:**
- [x] `test_access.py` dashboard/search block green

**Dependencies:** Task C

**Files likely touched:** `app/routes/dashboard.py`, `app/routes/reports.py`

**Estimated scope:** Medium (2 files)

### Task G: Frontend rank display + full regression

**Description:** Add `rank_level` to the frontend `User` type; `UsersPage.tsx` shows a rank badge (display-only label map Rank 1–6). Run the full suite + build + lint.

**Acceptance criteria:**
- [x] `User.rank_level` typed; UsersPage renders rank without breaking existing layout
- [x] `npm run build` + `npm run lint` clean
- [x] `test_access.py`, `test_hardening.py`, `test_phase2.py` all green

**Verification:**
- [x] Full command line: `python test_access.py && python test_hardening.py && python test_phase2.py` then frontend build/lint

**Dependencies:** Tasks A–F

**Files likely touched:** `frontend/src/types/index.ts`, `frontend/src/pages/UsersPage.tsx`

**Estimated scope:** Small (2 files)

### Checkpoint: Complete
- [x] All SPEC-access Success Criteria met
- [x] Manual: log in as constable vs. investigator — case list differs; foreign-case get → 403
- [x] Ready for `verify` module spec
---

# Implementation Plan: `verify` — Tighten Unauthenticated Public QR Verification

Spec: `SPEC-verify.md`. Capability map: `CAPABILITY-MAP.md`. Scope: `verify` module only. Depends on `access` (complete).

## Overview

The no-auth `/api/public` handlers in `app/routes/public.py` return the full case dossier (title, description, officer, filenames, full SHA-256 hashes, custody trail with handler names/locations/notes, uploader, block/tx detail) to anyone holding a QR/URL, and resolve bare integer DB IDs (enumeration). Reduce the public surface to **authenticity-only** (evidence identity + integrity/blockchain status + sha256 + block proof), delete the `isdigit()` integer branch, and prune the dead `app/services/` package (nothing imports it). Update `test_qr_verification.py` to the tightened contract and trim the frontend public page + types to match.

## Architecture Decisions

- **URL-as-credential + defense-in-depth:** the QR URL is a bearer credential, so the tighten = de-enumerate (opaque IDs only) + minimize the leak a shared/screenshotted QR exposes. No auth, tokens, or signatures added.
- **Authenticity-only payload:** integrity statuses + block authenticity prove "exists on the ledger, untampered"; `sha256_hash` stays so a holder can re-verify their copy offline. Case narrative, custody trail, personnel names, and filenames are deliberately **not** published.
- **Opaque IDs only:** delete the `identifier.isdigit()` branches; only `EV-…` / `CASE-…` strings resolve; a bare integer fails lookup → 404 (no existence oracle).
- **Keep:** `/api/public/network-info` (LAN QR scanning helper), `generate_qr_base64`, `get_base_client_url`, `hash_match`/integrity logic.
- **Defer:** per-IP rate limiting of public routes (de-enumeration + URL-as-credential cover the vector). Note in code, add when real abuse appears.
- `sha256_hash` on `/verify/evidence` is retained; hashes are removed from the `/verify/case` evidence list (they exist to verify a copy in hand, not to index a case).

## Tasks

### Task A: TDD — rewrite `test_qr_verification.py` to the tightened contract (RED)

**Description:** Update the suite before touching `public.py`: opaque-ID usage, absence assertions, 404-on-integer checks.

**Acceptance criteria:**
- [x] Evidence verify tested by seeded opaque `EV-…` id, not `/evidence/1`
- [x] Assert response has NO `case`, `custody_trail`, `original_filename`, `uploaded_by`, `current_custodian`, `tx_id`, integer `id`
- [x] `/verify/evidence/1` and `/verify/case/2` → 404
- [x] Case verify by opaque `CASE-2026-001`; evidence list has no filenames/hashes
- [x] Keep network-info + passport-QR tests

**Verification:**
- [x] Suite FAILS against current code (RED), demonstrating the leak/contract gap

**Dependencies:** None

**Files likely touched:** `test_qr_verification.py`

**Estimated scope:** Small (1 file)

### Task B: Tighten `app/routes/public.py`

**Description:** Rewrite both verify handlers to the authenticity-only contract; delete `isdigit()` integer branches.

**Acceptance criteria:**
- [x] `/verify/evidence` returns only: valid, is_tamper_proof, verification_url, qr_code, verified_at, evidence{evidence_id, classification, integrity_status, blockchain_status, current_version, sha256_hash, created_at}, blockchain{block_index, block_hash, previous_hash, timestamp, hash_match, status}
- [x] `/verify/case` returns only: valid, all_evidence_intact, verification_url, qr_code, verified_at, evidence_count, evidence_list{evidence_id, integrity_status, blockchain_status, verify_link}, blockchain_seal{status, evidence_secured_count, timestamp}
- [x] Integer identifiers → 404; opaque strings resolve
- [x] network-info + QR/base-URL helpers unchanged

**Verification:**
- [x] `python test_qr_verification.py` GREEN

**Dependencies:** Task A (RED contract in place)

**Files likely touched:** `app/routes/public.py`

**Estimated scope:** Small (1 file)

### Task C: Prune dead `app/services/`

**Description:** Delete the entire package (260-line `evidence_service.py` + `__init__.py`); nothing imports `app.services` except the package's own `__init__`.

**Acceptance criteria:**
- [x] Directory removed; no import of `app.services`/`evidence_service` anywhere
- [x] `python -c "import app.main"` clean; all suites still green

**Verification:**
- [x] `python seed.py && python test_qr_verification.py && python test_hardening.py && python test_phase2.py && python test_access.py`

**Dependencies:** None (independent of A/B)

**Files likely touched:** `backend/app/services/` (delete)

**Estimated scope:** Trivial (2 files deleted)

### Task D: Frontend — types + `PublicVerifyPage.tsx` to the trimmed contract

**Description:** Update `PublicEvidenceVerification` / `PublicCaseVerification` types (remove case object, custody_trail, filenames, officer, per-item hash/custodian) and trim the page to an authenticity certificate: keep the official seal, block proof card, QR card, verify links; drop case-details, custody-timeline, filename/size/format cards and case-list hash rows.

**Acceptance criteria:**
- [x] Types compile; no page/type references removed fields
- [x] Page renders certificate without case details / custody / filenames
- [x] `npm run build` + `npm run lint` clean

**Verification:**
- [x] `npm run build && npm run lint`

**Dependencies:** Task B (backend contract)

**Files likely touched:** `frontend/src/types/index.ts`, `frontend/src/pages/PublicVerifyPage.tsx`

**Estimated scope:** Medium (2 files)

### Checkpoint: Complete

- [x] All SPEC-verify Success Criteria met
- [x] Full regression: test_qr_verification + test_hardening + test_phase2 + test_access all green
- [x] `python -c "import app.main"` clean (services pruned)
- [x] `npm run build && npm run lint` clean
- [x] Manual: open `/verify/evidence/{EV…}` from the passport QR in a browser — certificate page with no case/custody/filename details
