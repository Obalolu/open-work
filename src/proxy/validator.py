"""Validate proxies by testing against real endpoints."""

from __future__ import annotations

import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Single fast endpoint for validation
_TEST_URL = "https://api.openalex.org/works?per_page=1&select=title"

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
]


@dataclass
class ProxyResult:
    """Result of testing a single proxy."""
    proxy: str
    working: bool = False
    latency_ms: float = 0.0
    error: str = ""


def _test_single_proxy(proxy: str, timeout: int = 5) -> ProxyResult:
    """Test a proxy against a fast endpoint."""
    proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    headers = {"User-Agent": random.choice(_USER_AGENTS)}

    try:
        start = time.monotonic()
        r = requests.get(
            _TEST_URL,
            proxies=proxy_dict,
            headers=headers,
            timeout=timeout,
        )
        latency = (time.monotonic() - start) * 1000

        if r.status_code in (200, 429):
            return ProxyResult(proxy=proxy, working=True, latency_ms=round(latency, 1))
    except Exception:
        pass

    return ProxyResult(proxy=proxy, working=False)


def validate_proxies(
    proxies: list[str],
    max_workers: int = 50,
    timeout: int = 5,
    target_working: int = 50,
    max_test: int = 400,
) -> list[ProxyResult]:
    """Validate proxies in parallel. Tests up to max_test, stops at target_working.

    Returns working proxies sorted by latency.
    """
    # If we have more than max_test, prioritize the ones most likely to work
    # (smaller pools from curated sources tend to have higher hit rates)
    if len(proxies) > max_test:
        sample = random.sample(proxies, max_test)
        logger.info(f"Sampled {max_test} proxies from {len(proxies)} total")
    else:
        sample = proxies

    working: list[ProxyResult] = []
    tested = 0

    batch_size = 80
    for i in range(0, len(sample), batch_size):
        if len(working) >= target_working:
            break

        batch = sample[i : i + batch_size]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_test_single_proxy, p, timeout): p for p in batch}
            for future in as_completed(futures):
                result = future.result()
                tested += 1
                if result.working:
                    working.append(result)

        logger.info(f"  Tested {tested}: {len(working)} working")

    working.sort(key=lambda r: r.latency_ms)
    logger.info(f"Validation complete: {len(working)}/{tested} working proxies")
    return working
