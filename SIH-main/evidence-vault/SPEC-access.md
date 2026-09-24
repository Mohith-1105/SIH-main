# Spec: `access` — Rank-Level Hierarchical Access

Module in Capability Map: `access`. Depends on: `identity` (per-user auth, current-user dependency, config). Feeds `verify`.

## Objective

EvidenceVault currently shows every case and every piece of evidence to any authenticated user holding a `cases.read` / `evidence.read` permission — `visible_case_ids`/`ensure_evidence_access` in `app/security/auth.py:152-184` are dead code and never wired into routes. Make access **hierarchical by police rank**: what a user can *see* is decided by `rank_level` (1–6), what a user can *do* stays decided by the existing 5 `role` permission sets. Every case/evidence read path scopes to what the rank permits — list, get, download, passport, upload, transfer, versions, custody, graph, dashboard, search.

Non-goals: no new role system (5 roles stay), no new hierarchy table (single numeric column), no per-case ACLs, no org/unit table (a user's `department` field is the unit proxy — a case has no unit field, so a case "belongs" to the department of its assigned/creating officer).

## Rank & Visibility Model

Ranks are numeric and monotonic — a rank N user never sees more than a rank N+1 user.

```
1  Constable
2  Head Constable / ASI
3  Sub-Inspector (own + same-department cases)
4  Inspector / DSP (own + same-department cases)
5  Forensic/Legal heads (all cases)
6  IGP / Commissioner / Admin (all cases)
```

| rank_level | Case visibility |
|---|---|
| 1–2 | Own cases only: `assigned_user_id == me` **or** `created_by == me` |
| 3–4 | Own cases **or** any case assigned to / created by a user in my `department` |
| 5–6 **or** role `ADMIN` | All cases (`None` sentinel = unrestricted) |

Rules:

- `ADMIN` always sees all, regardless of rank value.
- Role still gates *actions* via the existing `ROLE_PERMISSIONS` in `auth.py` — unchanged. Rank only gates *data scope*. A rank-6 forensic head who lacks `cases.write` still cannot write cases.
- Evidence visibility = visibility of its `case_id`. No separate evidence dimension; custody is not a read gate (forensic heads must be able to read any case to verify, and they are rank 5+).
- Backfill defaults by role: `ADMIN=6, AUDITOR=6, FORENSIC_OFFICER=5, LEGAL_OFFICER=5, INVESTIGATOR=3`. New-user default: role default via `ROLE_DEFAULT_RANK` map.
- If a user has an empty `department` and rank 3–4, unit scope is impossible → they fall back to own-cases-only (secure default).

## Tech Stack

Unchanged: Python 3, FastAPI, SQLAlchemy, SQLite. No new dependencies. One new `users` column + a `ROLE_DEFAULT_RANK` map; the existing (currently dead) `visible_case_ids` / `ensure_case_access` / `ensure_evidence_access` signatures in `app/security/auth.py` are **rewritten, not removed** — they become the single enforcement point.

## Commands

```
cd SIH-main/evidence-vault/backend
python seed.py                      # reseed DB → users get rank_level
uvicorn app.main:app --reload       # API on :8000
python test_hardening.py            # identity suite must stay green
python test_phase2.py               # existing suite must stay green
python test_access.py               # new access-module suite (TDD)
```

Frontend:
```
cd SIH-main/evidence-vault/frontend
npm run build   # tsc -b && vite build
npm run lint
```

## Project Structure

```
backend/app/security/auth.py   → RANK/visibility model: ROLE_DEFAULT_RANK, visible_case_ids(),
                                 ensure_case_access(), ensure_evidence_access(), case_scope_expr()
                                 (rewrite of the dead code at auth.py:152-184)
backend/app/models/user.py     → add rank_level (Integer, default 3)
backend/app/database.py        → users.rank_level migration + role-based backfill (like the
                                 existing totp_secret migration/backfill at database.py:56-79)
backend/app/schemas/__init__.py → UserOut.rank_level, UserCreate.rank_level (ge=1, le=6)
backend/app/routes/users.py    → pass rank_level on create
backend/seed.py                → rank_level per user
backend/app/routes/cases.py    → ensure_case_access on get/update/flow/advance/list_case_evidence;
                                 list_cases filters Case.id.in_(visible ids)
backend/app/routes/evidence.py → ensure_evidence_access on get/download/passport/verify/transfer/
                                 versions/custody/graph; upload checks case access; list_evidence
                                 filters Evidence.case_id.in_(visible ids)
backend/app/routes/dashboard.py → scope aggregate counts + distributions + alerts + search to
                                  visible cases/evidence
backend/test_access.py          → new script-style suite (matches test_hardening.py style)
frontend/src/types/index.ts     → User.rank_level
frontend/src/pages/UsersPage.tsx → show rank badge (label map, display only)
```

## Code Style

One shared scope resolver in `auth.py`; routes consume it with a two-line pattern. Example (matches existing route/docstring conventions):

```python
ids = visible_case_ids(user, db)          # None ⇒ unrestricted
if ids is not None:
    q = q.filter(Case.id.in_(ids))
```

Detail block (`auth.py`):

```python
# --- Rank hierarchy (data scope) ---
RANK_MIN, RANK_MAX = 1, 6
RANK_OWN_ONLY_MAX = 2    # ranks 1-2: own cases only
RANK_UNIT_MAX = 4        # ranks 3-4: own + same-department
ROLE_DEFAULT_RANK = {
    "ADMIN": 6, "AUDITOR": 6, "FORENSIC_OFFICER": 5,
    "LEGAL_OFFICER": 5, "INVESTIGATOR": 3,
}

def user_rank(u) -> int: return getattr(u, "rank_level", None) or 3

def visible_case_ids(user: User, db: Session):
    """Case IDs visible to this user, or None (all). Rank-driven, role-agnostic."""
    from app.models.case import Case
    from app.models.user import User as _U
    if user.role == "ADMIN" or user_rank(user) >= 5:
        return None
    scope = (Case.assigned_user_id == user.id) | (Case.created_by == user.id)
    if user_rank(user) >= 3 and user.department:
        mates = db.query(_U.id).filter(_U.department == user.department).all()
        ids = [m[0] for m in mates]
        scope = scope | Case.assigned_user_id.in_(ids) | Case.created_by.in_(ids)
    return [r[0] for r in db.query(Case.id).filter(scope).all()]
```

`ensure_case_access(user, case, db)` and `ensure_evidence_access(user, evidence, db)` both reduce to: compute `visible_case_ids`; `None` → allow; `evidence.case_id not in ids` (or `case.id not in ids`) → `HTTPException(403, "Not authorized to access this <case|evidence>")`. Old role-based special-cases for `FORENSIC_OFFICER`/`LEGAL_OFFICER`/`AUDITOR` are deleted — rank subsumes them. Keep the existing 404-before-403 ordering in routes.

## Testing Strategy

New script-style suite `test_access.py` (FastAPI `TestClient`, same style as `test_hardening.py`). Test-only users are created through `/api/users`; `demo123` is not used (seeded TOTP unknowable) — tests log in via the demo path with `DEMO_MODE` on, or create users with a known `totp_secret` by writing rows directly. Coverage:

- **Rank 1–2:** a constable sees only cases where they are assignee or creator (create 3 cases differing on those axes). List/get of a foreign case → 403.
- **Rank 3–4:** investigator sees own + cases by a same-`department` officer; does *not* see another department's case (403 on get).
- **Rank 5+ / ADMIN:** unrestricted list; get on any case 200.
- **Evidence:** list/get/download/passport/verify/transfer/versions/custody/graph on a case outside the user's scope → 403; inside → 200. Upload to a hidden case → 403.
- **Dashboard/search:** scoped counts and case-status distribution at rank 1–2 reflect only visible cases; unscoped admin counts stay the same as before.
- **Schema:** `UserOut`/`UserCreate` carry `rank_level`; `create_user` with `rank_level=2` returns a user whose list/get reflects rank 2; out-of-range (0, 7) rejected by validation.
- **Regression:** `test_hardening.py` and `test_phase2.py` stay green.

## Boundaries

- **Always:** enforce at the trust boundary — every route that takes a `case_id`/`evidence_id` path param checks access before returning data; list endpoints filter the query, never fetch-all-then-filter-in-python at scale (small SQLite so `in_` is fine). Foreign case → 403, never 404 (don't leak existence) once authenticated. `ADMIN` bypass unconditional.
- **Ask first:** introducing signal roles fine-grained per-case read; changing rank thresholds; adding a real unit/org table.
- **Never:** let a non-admin create a rank-higher user (users.write is ADMIN-only today — the elevation hole is already closed by RBAC; note this in `users.py`, do not add a second check); return another user's case/evidence to a user outside scope; regress the `identity` results.

## Success Criteria

- [x] `users.rank_level` exists; seed + backfill assign role defaults; `UserOut`/`UserCreate` expose it with 1–6 validation.
- [x] The dead `visible_case_ids`/`ensure_case_access`/`ensure_evidence_access` in `auth.py` are rewired and used by every case/evidence read route and upload.
- [x] Rank 1–2 sees only own cases; rank 3–4 sees own + same-department; rank 5+ and ADMIN see all — verified by `test_access.py`.
- [x] Dashboard aggregates and global search respect visibility.
- [x] `python test_access.py`, `python test_hardening.py`, `python test_phase2.py` pass; frontend builds and lints.

## Open Questions

1. Seed a 6th demo user (e.g. rank-2 constable in a different department) so a hackathon judge can *see* the hierarchy hide/allow access from the login screen, or keep the seed at 5 users and rely on tests to prove scoping? (Recommend: add the constable — cheap, demo-visible.)
2. Department is a free-text string (`"Criminal Investigation"` vs `"Criminal investigation"` differ). Strict equality is the lazy, correct-for-now choice; case-insensitive matching is one small change if the seed ever contradicts itself. Keep strict equality?