"""Thread-safe in-memory sliding window rate limiter for JanMitra Assist.

NOTE ON MULTI-WORKER DEPLOYMENTS & PRODUCTION LIMITATIONS:
This rate limiter maintains state within the memory of a single Python process.
- Local Development / MCA Evaluation: Highly reliable, thread-safe (via threading.Lock),
  zero external dependency, instant setup.
- Production Multi-Worker Environments: In multi-worker deployments (e.g. Uvicorn with
  --workers 4 or distributed containers behind a load balancer), rate limit counters
  are not shared between worker processes. For high-scale production deployments,
  this component should be swapped with a distributed Redis-backed rate limiter
  (e.g., Redis sliding window with sorted sets or slowapi backed by redis://).
"""

import threading
import time
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger


class InMemoryRateLimiter:
    """Thread-safe in-memory sliding window rate limiter for sensitive endpoints.
    
    Protects authentication (login) and password reset routes against brute-force attacks
    without requiring external infrastructure (Redis) for local development/demonstration.
    """

    def __init__(self):
        self._lock = threading.RLock()
        # Key: (action, identifier) -> List of timestamp floats
        self._attempts: Dict[Tuple[str, str], List[float]] = {}
        self._last_cleanup = time.time()

    def check_rate_limit(
        self,
        action: str,
        identifier: str,
        max_attempts: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> None:
        """Check if action is rate-limited. Raises HTTP 429 if limit exceeded."""
        effective_max = max_attempts if max_attempts is not None else settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
        effective_window = window_seconds if window_seconds is not None else settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS

        now = time.time()
        key = (action, identifier.strip().lower())

        with self._lock:
            self._periodic_cleanup(now)
            timestamps = self._attempts.get(key, [])
            cutoff = now - effective_window
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= effective_max:
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(oldest_in_window + effective_window - now) + 1)
                logger.warning(
                    f"Rate limit exceeded for action='{action}', identifier='{identifier[:4]}***'. "
                    f"Retry after {retry_after}s"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts. Please try again after {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

    def record_attempt(
        self,
        action: str,
        identifier: str,
    ) -> None:
        """Record an attempt (e.g. failed login or password reset request)."""
        now = time.time()
        key = (action, identifier.strip().lower())

        with self._lock:
            if key not in self._attempts:
                self._attempts[key] = []
            self._attempts[key].append(now)

    def clear_attempts(
        self,
        action: str,
        identifier: str,
    ) -> None:
        """Clear attempts upon successful authentication."""
        key = (action, identifier.strip().lower())
        with self._lock:
            self._attempts.pop(key, None)

    def is_rate_limited(
        self,
        action: str,
        identifier: str,
        max_attempts: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> bool:
        """Check rate-limit status without raising HTTPException."""
        effective_max = max_attempts if max_attempts is not None else settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
        effective_window = window_seconds if window_seconds is not None else settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS

        now = time.time()
        key = (action, identifier.strip().lower())
        with self._lock:
            timestamps = self._attempts.get(key, [])
            cutoff = now - effective_window
            valid_timestamps = [t for t in timestamps if t > cutoff]
            return len(valid_timestamps) >= effective_max

    def get_remaining_attempts(
        self,
        action: str,
        identifier: str,
        max_attempts: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> int:
        """Return the number of remaining allowed attempts in current window."""
        effective_max = max_attempts if max_attempts is not None else settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
        effective_window = window_seconds if window_seconds is not None else settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS

        now = time.time()
        key = (action, identifier.strip().lower())
        with self._lock:
            timestamps = self._attempts.get(key, [])
            cutoff = now - effective_window
            valid_count = len([t for t in timestamps if t > cutoff])
            return max(0, effective_max - valid_count)

    def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """Explicitly prune entries older than max_age_seconds. Returns number of removed keys."""
        now = time.time()
        cutoff = now - max_age_seconds
        removed_count = 0
        with self._lock:
            keys_to_remove = []
            for key, timestamps in self._attempts.items():
                valid = [t for t in timestamps if t > cutoff]
                if valid:
                    self._attempts[key] = valid
                else:
                    keys_to_remove.append(key)
            for k in keys_to_remove:
                self._attempts.pop(k, None)
                removed_count += 1
            self._last_cleanup = now
        return removed_count

    def reset_all(self) -> None:
        """Reset all rate limiter state (used in testing)."""
        with self._lock:
            self._attempts.clear()
            self._last_cleanup = time.time()

    def _periodic_cleanup(self, now: float) -> None:
        """Internal periodic cleanup: prunes entries older than 1 hour every 5 minutes."""
        if now - self._last_cleanup < 300:
            return
        self.cleanup_expired(3600)


# Global singleton instance
rate_limiter = InMemoryRateLimiter()
