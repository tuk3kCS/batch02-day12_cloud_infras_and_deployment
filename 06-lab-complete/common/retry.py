"""Exponential backoff retry decorator for A2A agent calls (Challenge 3).

Usage:
    from common.retry import with_retry

    @with_retry(max_attempts=4, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def my_call():
        ...

Or wrap a coroutine call inline:
    result = await with_retry()(my_coro_func)()

Circuit breaker pattern:
    The breaker opens after `breaker_threshold` consecutive failures and stays
    open for `breaker_timeout` seconds. Calls during open state raise
    CircuitOpenError immediately without hitting the downstream service.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)


class CircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is open."""


class CircuitBreaker:
    def __init__(self, threshold: int = 5, timeout: float = 30.0) -> None:
        self.threshold = threshold
        self.timeout = timeout
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.timeout:
            # Half-open: allow one probe through
            self._opened_at = None
            self._failures = 0
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = time.monotonic()
            logger.warning(
                "Circuit breaker opened after %d consecutive failures", self._failures
            )


# Per-endpoint circuit breakers
_breakers: dict[str, CircuitBreaker] = {}


def _get_breaker(key: str) -> CircuitBreaker:
    if key not in _breakers:
        _breakers[key] = CircuitBreaker()
    return _breakers[key]


def with_retry(
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    breaker_key: str | None = None,
) -> Callable:
    """Decorator factory: wraps an async function with exponential backoff retry.

    Args:
        max_attempts: Total number of attempts (including the first).
        base_delay:   Initial wait in seconds before the first retry.
        max_delay:    Upper cap on wait time between retries.
        backoff:      Multiplier applied to delay on each retry.
        exceptions:   Tuple of exception types that trigger a retry.
        breaker_key:  If set, use a named circuit breaker for this endpoint.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = _get_breaker(breaker_key) if breaker_key else None

            if breaker and breaker.is_open:
                raise CircuitOpenError(
                    f"Circuit breaker open for '{breaker_key}' — skipping call"
                )

            delay = base_delay
            last_exc: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)
                    if breaker:
                        breaker.record_success()
                    return result
                except exceptions as exc:
                    last_exc = exc
                    if breaker:
                        breaker.record_failure()
                    if attempt == max_attempts:
                        break
                    jitter = delay * 0.1  # 10% jitter to avoid thundering herd
                    wait = min(delay + jitter, max_delay)
                    logger.warning(
                        "Attempt %d/%d failed (%s); retrying in %.1fs",
                        attempt, max_attempts, exc, wait,
                    )
                    await asyncio.sleep(wait)
                    delay = min(delay * backoff, max_delay)

            raise last_exc  # type: ignore[misc]

        return wrapper
    return decorator
