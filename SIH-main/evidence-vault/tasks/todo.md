# Todo — `verify` module

Plan: `tasks/plan.md` (verify section) · Spec: `SPEC-verify.md`

## Tasks

- [x] Task A: Rewrite `test_qr_verification.py` to the tightened contract (TDD RED)
  - Acceptance: opaque-ID usage (no `/evidence/1`); absence assertions for `case`/`custody_trail`/`original_filename`/`uploaded_by`/`current_custodian`/`tx_id`; `/verify/evidence/1` + `/verify/case/2` → 404; case list has no filenames/hashes; network-info + passport-QR tests kept
  - Verify: `python test_qr_verification.py` → RED (failed)
  - Files: `test_qr_verification.py`
- [x] Task B: Tighten `app/routes/public.py` to authenticity-only payload
  - Acceptance: evidence response = valid/is_tamper_proof/url/qr/verified_at + evidence{evidence_id, classification, integrity_status, blockchain_status, current_version, sha256_hash, created_at} + blockchain{block_index, block_hash, previous_hash, timestamp, hash_match, status}; case response strips `case` object + per-item filenames/hashes; integer IDs → 404
  - Verify: `python test_qr_verification.py` → GREEN
  - Files: `app/routes/public.py`
- [x] Task C: Delete dead `app/services/` package
  - Acceptance: no import of `app.services`/`evidence_service` anywhere; `python -c "import app.main"` clean
  - Verify: `python seed.py`; all suites
  - Files: `backend/app/services/` (delete)
- [x] Task D: Frontend types + `PublicVerifyPage.tsx` to trimmed contract
  - Acceptance: `PublicEvidenceVerification`/`PublicCaseVerification` drop leaked fields; page renders certificate without case-details/custody/filename cards; build + lint clean
  - Verify: `npm run build && npm run lint`
  - Files: `frontend/src/types/index.ts`, `frontend/src/pages/PublicVerifyPage.tsx`
- [x] Checkpoint: complete — all SPEC-verify success criteria met; full regression green; manual certificate-page check