"""Retry decorators and circuit breaker for API resilience."""

from __future__ import annotations

import random
import functools
import threading
import time as time_module
from enum import Enum
from dataclasses import dataclass, field
from typing import TypeVar, Callable, Optional, Type, Tuple, Any

import tenacity
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    RetryCallState,
)

import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


def exponential_backoff_with_jitter(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay with optional jitter."""
    delay = min(base_delay * (2 ** attempt), max_delay)
    if jitter:
        jitter_range = delay * 0.25
        delay = delay + random.uniform(-jitter_range, jitter_range)
    return max(0.0, delay)


def retry_on_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that retries a function on specified exceptions with exponential backoff."""

    def _before_sleep(retry_state: RetryCallState) -> None:
        exc = retry_state.outcome.exception()
        attempt = retry_state.attempt_number
        logger.warning(
            f"{retry_state.fn.__name__} failed (attempt {attempt}/{max_attempts}): "
            f"{exc} - Retrying..."
        )
        if on_retry:
            on_retry(exc, attempt)

    def _after_final_failure(retry_state: RetryCallState) -> None:
        exc = retry_state.outcome.exception()
        logger.error(
            f"{retry_state.fn.__name__} failed after {max_attempts} attempts: {exc}",
            exc_info=True,
        )

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(
            initial=base_delay,
            max=max_delay,
            jitter=base_delay * 0.25,
        ),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
        before_sleep=_before_sleep,
        after=_after_final_failure,
    )


def retry_on_network_error(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator specialized for network errors (timeout, connection, 5xx)."""
    import requests

    def _should_retry(retry_state: RetryCallState) -> bool:
        exc = retry_state.outcome.exception()
        if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
            return True
        if isinstance(exc, requests.HTTPError):
            if exc.response is None:
                return True
            return 500 <= exc.response.status_code < 600
        return False

    def _before_sleep(retry_state: RetryCallState) -> None:
        exc = retry_state.outcome.exception()
        attempt = retry_state.attempt_number
        logger.warning(
            f"{retry_state.fn.__name__} network error (attempt {attempt}/{max_attempts}): "
            f"{exc} - Retrying..."
        )

    def _after_final_failure(retry_state: RetryCallState) -> None:
        exc = retry_state.outcome.exception()
        logger.error(
            f"{retry_state.fn.__name__} failed after {max_attempts} attempts: {exc}",
            exc_info=True,
        )

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(
            initial=base_delay,
            max=max_delay,
            jitter=base_delay * 0.25,
        ),
        retry=_should_retry,
        reraise=True,
        before_sleep=_before_sleep,
        after=_after_final_failure,
    )


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Circuit breaker '{name}' is OPEN - service unavailable")


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    reset_timeout: float = 60.0
    success_threshold: int = 2


class CircuitBreaker:
    """Thread-safe circuit breaker with singleton per name."""

    _instances: dict = {}
    _lock = threading.Lock()

    def __new__(cls, name: str, config: Optional[CircuitBreakerConfig] = None):
        with cls._lock:
            if name not in cls._instances:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instances[name] = instance
            return cls._instances[name]

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        if getattr(self, "_initialized", False):
            return
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._state_lock = threading.Lock()
        self._initialized = True

    def allow_request(self) -> bool:
        """Check if a request is allowed through."""
        with self._state_lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if self.last_failure_time and (
                    time_module.time() - self.last_failure_time >= self.config.reset_timeout
                ):
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' -> HALF_OPEN (probe)")
                    return True
                return False
            if self.state == CircuitState.HALF_OPEN:
                return True
            return False

    def record_success(self) -> None:
        """Record a successful request."""
        with self._state_lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' -> CLOSED (recovered)")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self, error: Exception) -> None:
        """Record a failed request."""
        with self._state_lock:
            self.failure_count += 1
            self.last_failure_time = time_module.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' -> OPEN (probe failed: {error})"
                )
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker '{self.name}' -> OPEN "
                        f"(failures: {self.failure_count})"
                    )

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """Wrap a function with circuit breaker protection."""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.allow_request():
                raise CircuitOpenError(self.name)
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure(e)
                raise
        return wrapper

    def reset(self) -> None:
        """Reset to closed state."""
        with self._state_lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None


def get_citation_circuit_breaker() -> CircuitBreaker:
    """Get or create the citation APIs circuit breaker."""
    config = CircuitBreakerConfig(
        failure_threshold=10,
        reset_timeout=30.0,
        success_threshold=3,
    )
    return CircuitBreaker("citation_apis", config)
