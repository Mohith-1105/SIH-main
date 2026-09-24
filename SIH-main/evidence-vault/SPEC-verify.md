# Spec: `verify` — Tighten Unauthenticated Public QR Verification

Module in Capability Map: `verify`. Depends on: `access` (rank scoping), `identity` (guard store). Final module in the build order.

## Objective

`app/routes/public.py` (no-auth, mounted at `/api/public`) today returns the **full case dossier** to anyone holding a verification URL/QR: case title, description, investigating officer, every evidence filename, SHA-256 hashes, custody trail with handler names/roles/locations/notes, uploader, block/int tx details. Scanned or screenshotted QRs leak all of it with no authentication. Make the public surface **authenticity-only**: it proves *that a document exists on the ledger and is untampered* (plus gives a hash to re-verify a held copy offline) — and deliberately withholds case narrative, personnel, and custody details. Simultaneously remove ID enumeration and prune the dead `app/services/` package.

Decisions locked at spec approval:
- **Authenticity-only** public responses (below).
- **Opaque IDs only** — bare DB integer identifiers are rejected (404); only `EV-…` / `CASE-…` public identifiers resolve.

## Public Surface Model (the tightened contract)

The QR URL is the credential — the bearer already has the document. So the surface proves integrity, not content.

### `GET /api/public/verify/evidence/{identifier}` (opaque `EV-…` only)

```
valid               true
is_tamper_proof     integrity_status == "VERIFIED" AND block.data_hash == sha256_hash
verification_url    (unchanged)
qr_code             (unchanged, PNG base64)
verified_at         (unchanged)
evidence              → evidence_id, classification, integrity_status,
                        blockchain_status, current_version, sha256_hash,
                        created_at
blockchain            → block_index, block_hash, previous_hash, timestamp,
                        hash_match, status
```

Removed from evidence response: `original_filename`, `evidence_type`, `mime_type`, `file_size`, `current_custodian`, `uploaded_by`, raw integer `id`, `uploaded_at`.
Removed entirely: the `case` object (no case number/title/description/officer/type/status/priority/dates) and the `custody_trail` array, and the `consensus`/`tx_id` fabricated strings.

### `GET /api/public/verify/case/{identifier}` (opaque `CASE-…` only)

```
valid
all_evidence_intact      every evidence item VERIFIED
verification_url / qr_code / verified_at
evidence_count
evidence_list            → per item: evidence_id, integrity_status,
                           blockchain_status, verify_link
blockchain_seal          → status, evidence_secured_count, timestamp
```

Removed: the `case` object, and per-item `original_filename`, `evidence_type`, `classification`, `sha256_hash`, `current_custodian`, integer `id`, `created_at`.

### Unchanged

- `GET /api/public/network-info` stays (LAN QR-scanning helper for mobile/laptop; not sensitive).
- Identifier resolution by the purely *opaque* string. The `isdigit()` integer branch is **deleted**; a bare integer string simply fails to match → 404 "Evidence not found" / "Case not found" (no existence oracle).
- QR encode + LAN base-URL helpers, block verification logic.

## Tech Stack

Unchanged: Python 3, FastAPI, SQLAlchemy, SQLite. No new dependencies, no new tables, no signatures/tokens. Frontend: React 19 + TS, types trimmed to match.

## Commands

```
cd SIH-main/evidence-vault/backend
python seed.py                      # existing seeded data (EV-/CASE- ids) — no reseed needed
uvicorn app.main:app --reload       # API on :8000
python test_qr_verification.py      # update → must assert tightened schema + 404 on integers
python test_hardening.py            # identity suite must stay green
python test_phase2.py               # phase-2 suite must stay green
python test_access.py               # access suite must stay green
```

Frontend:
```
cd SIH-main/evidence-vault/frontend
npm run build   # tsc -b && vite build
npm run lint
```

## Project Structure

```
backend/app/routes/public.py       → tighten both verify handlers; delete isdigit() branch
backend/app/services/               → DELETE whole directory (dead code, nothing imports it)
backend/test_qr_verification.py    → update public-verify tests to tightened schema; drop
                                     /evidence/1 integer test; add 404-on-integer assertions;
                                     add absence-of-sensitive-field assertions
frontend/src/types/index.ts        → PublicEvidenceVerification / PublicCaseVerification:
                                     remove leaked fields (filenames, case object, custody_trail,
                                     officer, hashes-in-case-list…)
frontend/src/pages/PublicVerifyPage.tsx → trim to authenticity certificate (drop case-details,
                                     custody timeline, filename/size/format cards, hash-copy on
                                     case list); keep seals, block proof, QR, verify links
```

## Testing Strategy

Same script-style suites, `python test_*.py`, run after `seed.py`. The working tree must be ALL GREEN at every step of the module (test_hardening + test_phase2 + test_access + test_qr_verification).

`test_qr_verification.py` updates:
1. `test_public_evidence_verification_by_id` → becomes opaque-ID test (resolve the seeded `EV-…` id first), not `/evidence/1`.
2. Assert the tightened evidence block contains ONLY the allowed keys; assert absence of `case`, `custody_trail`, `original_filename`, `uploaded_by`, `current_custodian` in the response.
3. Assert integer identifiers are rejected: `/verify/evidence/1` → 404 and `/verify/case/2` → 404.
4. Keep `test_network_info`, `test_public_case_verification` (updated to opaque `CASE-…`, still present in seeded data), `test_passport_route_scannable_qr`.

## Code Style

Match the file as-is. Handler keeps `identifier: str`, `request: Request`, `host` query param, `db` dependency. Only the response-building and the lookup change:

```python
ev = db.query(Evidence).filter(Evidence.evidence_id == identifier).first()
if not ev:
    raise HTTPException(status_code=404, detail="Evidence not found")
```

Same for the case handler: `Case.case_number == identifier`, no integer-first branch.

## Boundaries

- Always: keep `generate_qr_base64`, `get_base_client_url`, validity/hash-match logic intact; keep both endpoints public and auth-free; keep verified_at/verification_url/qr_code; keep network-info.
- Ask first: re-adding integer-ID lookup; re-adding filenames/custody/case details to public responses; adding rate limiting to public routes (explicitly deferred — ID de-enumeration + URL-as-credential cover the brute-force vector); changing the `sha256_hash` in the public evidence view.
- Never: publish case metadata, custody events, officer/actor names, or original filenames through `/api/public`; call the dead `evidence_service` functions (they don't exist after this module).

## Success Criteria

- [x] `/verify/evidence/{EV-…}` returns only the authenticity fields above; no `case`, no `custody_trail`, no `original_filename`/`uploaded_by`/`current_custodian`/`tx_id`/integer `id`.
- [x] `/verify/case/{CASE-…}` returns per-item `evidence_id` + integrity/blockchain status + link only; no `case` block, no filenames/hashes.
- [x] Integer identifiers on either endpoint → 404.
- [x] `/api/public/network-info` unchanged.
- [x] `app/services/` deleted and nothing imports it (`python -c "import app.main"` clean).
- [x] Frontend types + PublicVerifyPage compile against the trimmed contract; build + lint clean; page renders the certificate without referencing removed fields.
- [x] Full regression: test_qr_verification + test_hardening + test_phase2 + test_access all green.

## Open Questions

None — locked at approval (authenticity-only surface; opaque IDs only).