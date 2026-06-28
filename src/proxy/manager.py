"""Proxy manager — orchestrates fetching, validation, rotation, and config updates."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import toml

from src.proxy.fetcher import fetch_all
from src.proxy.validator import ProxyResult, validate_proxies

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(os.environ.get("OPENWORK_CONFIG_DIR", Path.home() / ".config" / "open-work"))
PROXY_CACHE = CONFIG_DIR / "proxy_cache.json"


@dataclass
class ProxyPool:
    """Manages a pool of working proxies with rotation and health tracking."""
    proxies: list[str] = field(default_factory=list)
    latencies: dict[str, float] = field(default_factory=dict)
    failures: dict[str, int] = field(default_factory=dict)
    last_refresh: float = 0.0
    max_failures: int = 3

    def get_random(self) -> Optional[str]:
        """Get a random healthy proxy."""
        healthy = self._healthy_proxies()
        if not healthy:
            return None
        # Weight by inverse latency (faster = more likely to be picked)
        weights = [1.0 / max(self.latencies.get(p, 1000), 1) for p in healthy]
        return random.choices(healthy, weights=weights, k=1)[0]

    def get_fastest(self) -> Optional[str]:
        """Get the fastest healthy proxy."""
        healthy = self._healthy_proxies()
        if not healthy:
            return None
        return min(healthy, key=lambda p: self.latencies.get(p, 9999))

    def report_failure(self, proxy: str) -> None:
        """Report a proxy failure."""
        self.failures[proxy] = self.failures.get(proxy, 0) + 1

    def report_success(self, proxy: str, latency_ms: float = 0) -> None:
        """Report a successful use."""
        self.failures[proxy] = 0
        if latency_ms > 0:
            # Exponential moving average
            old = self.latencies.get(proxy, latency_ms)
            self.latencies[proxy] = old * 0.7 + latency_ms * 0.3

    def _healthy_proxies(self) -> list[str]:
        """Return proxies that haven't exceeded failure threshold."""
        return [
            p for p in self.proxies
            if self.failures.get(p, 0) < self.max_failures
        ]

    @property
    def stats(self) -> dict:
        healthy = len(self._healthy_proxies())
        return {
            "total": len(self.proxies),
            "healthy": healthy,
            "failed": len(self.proxies) - healthy,
            "avg_latency": (
                sum(self.latencies.values()) / len(self.latencies)
                if self.latencies else 0
            ),
            "last_refresh": self.last_refresh,
        }


class ProxyManager:
    """Manages proxy lifecycle: fetch, validate, rotate, persist."""

    def __init__(self, auto_refresh: bool = True, refresh_interval: int = 3600):
        self.pool = ProxyPool()
        self.auto_refresh = auto_refresh
        self.refresh_interval = refresh_interval  # seconds
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached proxy data from disk."""
        if PROXY_CACHE.exists():
            try:
                data = json.loads(PROXY_CACHE.read_text())
                self.pool.proxies = data.get("proxies", [])
                self.pool.latencies = data.get("latencies", {})
                self.pool.failures = data.get("failures", {})
                self.pool.last_refresh = data.get("last_refresh", 0)
                logger.info(f"Loaded {len(self.pool.proxies)} cached proxies")
            except Exception as e:
                logger.warning(f"Failed to load proxy cache: {e}")

    def _save_cache(self) -> None:
        """Persist proxy data to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "proxies": self.pool.proxies,
            "latencies": self.pool.latencies,
            "failures": self.pool.failures,
            "last_refresh": self.pool.last_refresh,
        }
        PROXY_CACHE.write_text(json.dumps(data, indent=2))

    def _update_config_toml(self) -> None:
        """Write working proxies to config.toml."""
        config_path = CONFIG_DIR / "config.toml"
        if not config_path.exists():
            return

        try:
            cfg = toml.load(config_path)
        except Exception:
            cfg = {}

        if "research" not in cfg:
            cfg["research"] = {}

        cfg["research"]["proxy_list"] = ",".join(self.pool.proxies)

        with open(config_path, "w") as f:
            toml.dump(cfg, f)

        logger.info(f"Updated config.toml with {len(self.pool.proxies)} proxies")

    def refresh(self, force: bool = False) -> int:
        """Fetch, validate, and update proxy pool. Returns count of working proxies."""
        # Check if refresh needed
        if (
            not force
            and self.pool.proxies
            and (time.time() - self.pool.last_refresh) < self.refresh_interval
        ):
            logger.info(
                f"Proxy pool still fresh ({len(self.pool.proxies)} proxies, "
                f"refreshed {int(time.time() - self.pool.last_refresh)}s ago)"
            )
            return len(self.pool.proxies)

        logger.info("Refreshing proxy pool from all sources...")
        start = time.monotonic()

        # Fetch from all sources (returns tier1 + all)
        tier1_proxies, all_proxies = fetch_all(max_workers=12)
        logger.info(f"Fetched {len(tier1_proxies)} tier-1, {len(all_proxies)} total proxies")

        # Validate tier-1 first (high quality), then fill from the rest
        working = validate_proxies(
            tier1_proxies,
            max_workers=40,
            timeout=6,
            target_working=40,
            max_test=600,
        )

        # If not enough from tier-1, test more from all sources
        if len(working) < 30:
            already_tested = set(r.proxy for r in working)
            remaining = [p for p in all_proxies if p not in already_tested]
            more = validate_proxies(
                remaining,
                max_workers=40,
                timeout=6,
                target_working=50 - len(working),
                max_test=400,
            )
            working.extend(more)

        # Update pool
        self.pool.proxies = [r.proxy for r in working]
        self.pool.latencies = {r.proxy: r.latency_ms for r in working}
        self.pool.failures = {r.proxy: 0 for r in working}
        self.pool.last_refresh = time.time()

        elapsed = time.monotonic() - start
        logger.info(
            f"Proxy refresh complete: {len(self.pool.proxies)} working "
            f"proxies in {elapsed:.1f}s"
        )

        # Persist
        self._save_cache()
        self._update_config_toml()

        return len(self.pool.proxies)

    def get_proxy(self) -> Optional[str]:
        """Get a proxy. Auto-refreshes if stale."""
        if self.auto_refresh:
            if time.time() - self.pool.last_refresh > self.refresh_interval:
                self.refresh()
        return self.pool.get_random()

    def get_proxies_dict(self) -> Optional[dict]:
        """Get a requests-compatible proxy dict."""
        proxy = self.get_proxy()
        if not proxy:
            return None
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

    def report_usage(self, proxy: str, success: bool, latency_ms: float = 0) -> None:
        """Report proxy usage result."""
        if success:
            self.pool.report_success(proxy, latency_ms)
        else:
            self.pool.report_failure(proxy)

    def get_stats(self) -> dict:
        """Get pool statistics."""
        return self.pool.stats
