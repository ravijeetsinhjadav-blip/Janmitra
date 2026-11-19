"""Tests for in-memory rate limiting module."""

import time
import pytest
from fastapi import HTTPException
from app.core.rate_limiter import InMemoryRateLimiter


def test_rate_limiter_allows_requests_under_threshold():
    limiter = InMemoryRateLimiter()
    # 3 attempts allowed in 60s
    for _ in range(3):
        limiter.check_rate_limit(action="test_action", identifier="user@example.com", max_attempts=3, window_seconds=60)
        limiter.record_attempt(action="test_action", identifier="user@example.com")


def test_rate_limiter_blocks_when_threshold_exceeded():
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        limiter.check_rate_limit(action="test_action", identifier="user@example.com", max_attempts=3, window_seconds=60)
        limiter.record_attempt(action="test_action", identifier="user@example.com")

    # 4th attempt should raise HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        limiter.check_rate_limit(action="test_action", identifier="user@example.com", max_attempts=3, window_seconds=60)

    assert exc_info.value.status_code == 429
    assert "Too many attempts" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers


def test_rate_limiter_clear_attempts_resets_counter():
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        limiter.record_attempt(action="test_action", identifier="user@example.com")

    assert limiter.is_rate_limited(action="test_action", identifier="user@example.com", max_attempts=3, window_seconds=60) is True

    # Clear attempts (e.g. on successful login)
    limiter.clear_attempts(action="test_action", identifier="user@example.com")

    assert limiter.is_rate_limited(action="test_action", identifier="user@example.com", max_attempts=3, window_seconds=60) is False
    assert limiter.get_remaining_attempts(action="test_action", identifier="user@example.com", max_attempts=3, window_seconds=60) == 3


def test_rate_limiter_expiry_window():
    limiter = InMemoryRateLimiter()
    # Window of 1 second
    limiter.record_attempt(action="short_window", identifier="user@example.com")
    assert limiter.get_remaining_attempts(action="short_window", identifier="user@example.com", max_attempts=1, window_seconds=1) == 0

    # Wait for window to expire
    time.sleep(1.1)

    # Should now be allowed
    assert limiter.is_rate_limited(action="short_window", identifier="user@example.com", max_attempts=1, window_seconds=1) is False
    assert limiter.get_remaining_attempts(action="short_window", identifier="user@example.com", max_attempts=1, window_seconds=1) == 1


def test_rate_limiter_cleanup_expired_buckets():
    limiter = InMemoryRateLimiter()
    limiter.record_attempt(action="cleanup_test", identifier="expired_user@example.com")
    # Manually backdate timestamp
    key = ("cleanup_test", "expired_user@example.com")
    limiter._attempts[key] = [time.time() - 4000]

    # Cleanup entries older than 3600 seconds
    removed = limiter.cleanup_expired(max_age_seconds=3600)
    assert removed == 1
    assert key not in limiter._attempts

