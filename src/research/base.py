"""Abstract base API client with rate limiting, proxy rotation, and retries."""

from __future__ import annotations

import os
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import requests

from src.research.backpressure import get_backpressure_manager
from src.research.retry import get_citation_circuit_breaker, CircuitOpenError

# Lazy-loaded proxy manager (initialized on first use)
_PROXY_MANAGER = None


def _get_proxy_manager():
    """Get or initialize the ProxyManager singleton."""
    global _PROXY_MANAGER
    if _PROXY_MANAGER is None:
        try:
            from src.proxy.manager import ProxyManager
            _PROXY_MANAGER = ProxyManager(auto_refresh=True, refresh_interval=1800)
        except Exception:
            _PROXY_MANAGER = False  # Sentinel: don't retry if import fails
    return _PROXY_MANAGER if _PROXY_MANAGER is not False else None


# Browser User-Agent pool for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

BROWSER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def _load_proxy_list() -> list[str]:
    """Load proxy list from PROXY_LIST env var or config file.

    Supports: host:port or host:port:user:pass
    Config key: research.proxy_list in ~/.config/open-work/config.toml
    """
    raw = os.environ.get("PROXY_LIST", "")
    if not raw:
        try:
            from src.config import get_research_config
            raw = get_research_config().get("proxy_list", "")
        except Exception:
            pass
    if not raw:
        return []
    proxies = [p.strip() for p in raw.split(",") if p.strip()]
    valid = []
    for p in proxies:
        parts = p.split(":")
        if len(parts) in (2, 4):
            valid.append(p)
        else:
            import logging
            logging.getLogger(__name__).warning(f"Invalid proxy format (expected host:port or host:port:user:pass): {p[:20]}...")
    return valid


def _parse_proxy(proxy_str: str) -> dict:
    """Parse a proxy string into requests proxy dict."""
    parts = proxy_str.split(":")
    if len(parts) == 4:
        host, port, user, pwd = parts
        proxy_url = f"http://{user}:{pwd}@{host}:{port}"
    elif len(parts) == 2:
        host, port = parts
        proxy_url = f"http://{host}:{port}"
    else:
        return {}
    return {"http": proxy_url, "https": proxy_url}


# Loaded once at import time (static fallback list)
PROXY_LIST: list[str] = _load_proxy_list()


class BaseAPIClient(ABC):
    """Abstract base for academic API clients.

    Provides: rate limiting, retries with exponential backoff, proxy rotation,
    User-Agent rotation, and backpressure integration.
    """

    _client_ip: Optional[str] = None

    @classmethod
    def set_client_ip(cls, ip: Optional[str]) -> None:
        cls._client_ip = ip

    @classmethod
    def get_client_ip(cls) -> Optional[str]:
        return cls._client_ip

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        rate_limit_per_second: float = 10.0,
        timeout: int = 10,
        max_retries: int = 3,
        api_type: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_type = api_type
        self.rate_limit_per_second = rate_limit_per_second
        self.min_interval = 1.0 / rate_limit_per_second
        self.last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)

    def _rate_limit_wait(self) -> None:
        """Token-bucket rate limiting plus global backpressure delay."""
        now = time.time()
        elapsed = now - self.last_request_time
        wait_time = self.min_interval - elapsed
        try:
            bp_delay = get_backpressure_manager().get_recommended_delay()
            wait_time = max(wait_time, bp_delay)
        except Exception:
            bp_delay = 0.0
        if wait_time > 0:
            time.sleep(wait_time)
        self.last_request_time = time.time()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make an HTTP request with rate limiting, retries, proxy rotation, and backoff.

        Returns:
            JSON response dict, or None on failure/not found.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        bp = get_backpressure_manager()

        # Check circuit breaker before attempting requests
        breaker = get_citation_circuit_breaker()
        if not breaker.allow_request():
            import logging
            logging.getLogger(__name__).warning(
                f"Circuit breaker OPEN for {self.api_type}; skipping request"
            )
            return None

        for attempt in range(self.max_retries):
            self._rate_limit_wait()

            headers = {"User-Agent": random.choice(USER_AGENTS)}

            # Client IP forwarding for distributed rate limits
            client_ip = self.get_client_ip()
            if client_ip and client_ip != "unknown":
                headers["X-Forwarded-For"] = client_ip

            # API key
            if self.api_key:
                headers["x-api-key"] = self.api_key

            if extra_headers:
                headers.update(extra_headers)

            # Proxy selection — prefer ProxyManager (health-aware), fallback to static list
            proxies = None
            proxy_str = None
            pm = _get_proxy_manager()
            if pm:
                proxy_str = pm.get_proxy()
                if proxy_str:
                    proxies = _parse_proxy(proxy_str)
            elif PROXY_LIST:
                proxy_str = random.choice(PROXY_LIST)
                proxies = _parse_proxy(proxy_str)

            request_start = time.monotonic()
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                    timeout=self.timeout,
                    proxies=proxies,
                )
                elapsed_ms = (time.monotonic() - request_start) * 1000

                # Report to proxy manager
                if pm and proxy_str:
                    pm.report_usage(proxy_str, success=response.status_code == 200, latency_ms=elapsed_ms)

                if response.status_code == 200:
                    breaker.record_success()
                    return response.json()

                if response.status_code == 404:
                    return None

                if response.status_code == 429:
                    bp.signal_429(self.api_type or "unknown")
                    if pm and proxy_str:
                        pm.report_usage(proxy_str, success=False)
                    if PROXY_LIST:
                        wait_time = 0.5
                    else:
                        wait_time = min(3 * (2 ** attempt), 10.0)
                    import logging
                    logging.getLogger(__name__).warning(
                        f"429 from {self.api_type}: waiting {wait_time:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                    continue

                if response.status_code >= 500:
                    if PROXY_LIST:
                        wait_time = 0.5
                    else:
                        wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue

                # Other client errors — don't retry
                import logging
                logging.getLogger(__name__).debug(
                    f"HTTP {response.status_code} from {self.api_type}: {url}"
                )
                breaker.record_failure(Exception(f"HTTP {response.status_code}"))
                return None

            except requests.Timeout:
                if PROXY_LIST:
                    time.sleep(0.5)
                else:
                    time.sleep(2 ** attempt)
                continue

            except requests.ConnectionError:
                if PROXY_LIST:
                    time.sleep(0.5)
                else:
                    time.sleep(2 ** attempt)
                continue

            except requests.RequestException:
                return None

            except Exception:
                return None

        import logging
        logging.getLogger(__name__).debug(
            f"All {self.max_retries} retries exhausted for {self.api_type}: {url}"
        )
        breaker.record_failure(Exception(f"All retries exhausted for {self.api_type}"))
        return None

    @abstractmethod
    def search_paper(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for a single paper. Returns normalized metadata dict or None."""
        ...

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> BaseAPIClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
