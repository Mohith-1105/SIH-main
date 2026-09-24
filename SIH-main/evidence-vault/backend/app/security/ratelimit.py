"""In-memory brute-force protection for authentication endpoints.

Sliding-window failed-attempt counter per account+IP with temporary lockout.
# ponytail: single-process in-memory store; move to Redis or a DB table when the
# app runs multiple workers/instances (state would otherwise be per-process).
"""
from __future__ import annotations

import threading
import time

from app.config import settings


class LoginGuard:
    def __init__(
        self,
        max_attempts: int | None = None,
        window_seconds: int | None = None,
        lockout_seconds: int | None = None,
    ):
        self.max_attempts = max_attempts or settings.RATE_LIMIT_MAX_ATTEMPTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        self.lockout_seconds = lockout_seconds or settings.LOCKOUT_SECONDS
        self._lock = threading.Lock()
        self._records: dict[str, tuple[list[float], float]] = {}

    def _prune(self, ts: float) -> None:
        stale = [k for k, (times, _until) in self._records.items()
                 if not times and (not _until or _until <= ts)]
        for k in stale:
            del self._records[k]

    def blocked(self, key: str) -> bool:
        """True if attempts for this key are currently locked out."""
        with self._lock:
            ts = time.time()
            self._prune(ts)
            rec = self._records.get(key)
            if not rec:
                return False
            times, locked_until = rec
            if locked_until:
                if locked_until > ts:
                    return True
                self._records.pop(key, None)
            return False

    def fail(self, key: str) -> bool:
        """Record one failed attempt; returns True if the key just reached lockout."""
        with self._lock:
            ts = time.time()
            self._prune(ts)
            times, locked_until = self._records.get(key, ([], 0.0))
            if locked_until > ts:
                return True
            times = [t for t in times if ts - t <= self.window_seconds]
            times.append(ts)
            if len(times) >= self.max_attempts:
                self._records[key] = ([], ts + self.lockout_seconds)
                return True
            self._records[key] = (times, 0.0)
            return False

    def clear(self, key: str) -> None:
        with self._lock:
            self._records.pop(key, None)


guard = LoginGuard()