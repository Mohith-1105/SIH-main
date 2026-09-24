# Capability Map: EvidenceVault Hardening

Approved gate: Phase 0, 2026-09-23.

| Module id | Responsibility | Depends on |
|---|---|---|
| `identity` | Auth hardening: per-user TOTP secrets, remove MFA backdoor `123456` + leaked demo code, brute-force lockout + rate limiting, CORS lockdown, rotate committed secrets, fail-fast default keys | — |
| `access` | Rank-level hierarchy (1–6) + enforce row-level scoping (assigned → unit → all); admin top role; per-rank permissions | `identity` |
| `verify` | Tighten unauthenticated public QR verify, fix stale tests, prune dead `evidence_service` | `access` |

Build order: `identity` → `access` → `verify`.

Interface at the boundary: `identity` issues the JWT and exposes the currently authenticated user incl. `rank_level`; `access` consumes it for scoping.

Non-goals (decided at Phase 0): existing 5 department roles stay as-is;
DB remains SQLite; encryption stays single-key Fernet (no per-evidence keys).