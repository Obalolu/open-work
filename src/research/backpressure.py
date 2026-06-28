"""Backpressure manager for rate limit coordination."""

from __future__ import annotations

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PRESSURE_CONFIG = {
    "recovery_window_seconds": 60,
    "429_count_critical": 25,
    "min_delay_seconds": 0.1,
    "max_delay_seconds": 5.0,
    "pause_threshold": 0.8,
    "resume_threshold": 0.5,
}


class APIType:
    """API type identifiers for backpressure tracking."""
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    CROSSREF = "crossref"
    ARXIV = "arxiv"


class BackpressureManager:
    """Tracks 429 errors across APIs and recommends delays.

    Uses local dict storage with time-decay for pressure calculation.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._api_types: list[str] = [
            APIType.SEMANTIC_SCHOLAR,
            APIType.OPENALEX,
            APIType.CROSSREF,
            APIType.ARXIV,
        ]

    def _get(self, key: str, default: Any = 0) -> Any:
        return self._store.get(key, default)

    def _put(self, key: str, value: Any) -> None:
        self._store[key] = value

    def signal_429(self, api_type: str) -> None:
        """Signal that a 429 was received from an API."""
        count = self._get(f"api:{api_type}:429_count", 0)
        self._put(f"api:{api_type}:429_count", count + 1)
        self._put(f"api:{api_type}:last_429", time.time())
        self._recalculate_pressure()

    def _recalculate_pressure(self) -> None:
        """Recalculate global pressure based on per-API 429 counts with time decay."""
        now = time.time()
        window = PRESSURE_CONFIG["recovery_window_seconds"]
        critical = PRESSURE_CONFIG["429_count_critical"]

        pressures = []
        for api_type in self._api_types:
            count = self._get(f"api:{api_type}:429_count", 0)
            last_429 = self._get(f"api:{api_type}:last_429", 0)

            if last_429 == 0:
                effective_count = 0
            else:
                time_since = now - last_429
                decay = max(0, 1 - (time_since / window))
                effective_count = count * decay

            api_pressure = min(1.0, effective_count / critical)
            pressures.append(api_pressure)

        global_pressure = sum(pressures) / max(len(pressures), 1)
        self._put("global:pressure", global_pressure)

        min_d = PRESSURE_CONFIG["min_delay_seconds"]
        max_d = PRESSURE_CONFIG["max_delay_seconds"]
        delay = min_d + (global_pressure * (max_d - min_d))
        self._put("global:recommended_delay", delay)

    def get_global_pressure(self) -> float:
        """Get current global pressure (0.0 to 1.0)."""
        self._recalculate_pressure()
        return self._get("global:pressure", 0.0)

    def get_recommended_delay(self) -> float:
        """Get recommended delay in seconds (0.1 to 5.0)."""
        self._recalculate_pressure()
        return self._get("global:recommended_delay", 0.1)

    def should_pause_spawning(self) -> bool:
        """Check if spawning should be paused due to high pressure."""
        return self.get_global_pressure() > PRESSURE_CONFIG["pause_threshold"]

    def get_adaptive_batch_size(self) -> int:
        """Get batch size based on current pressure."""
        pressure = self.get_global_pressure()
        if pressure > 0.8:
            return 5
        elif pressure > 0.6:
            return 10
        elif pressure > 0.3:
            return 15
        return 25

    def get_stats(self) -> dict:
        """Get current backpressure stats."""
        self._recalculate_pressure()
        stats = {
            "global_pressure": self._get("global:pressure", 0.0),
            "recommended_delay": self._get("global:recommended_delay", 0.1),
            "batch_size": self.get_adaptive_batch_size(),
            "should_pause": self.should_pause_spawning(),
            "apis": {},
        }
        for api_type in self._api_types:
            stats["apis"][api_type] = {
                "429_count": self._get(f"api:{api_type}:429_count", 0),
                "last_429": self._get(f"api:{api_type}:last_429", 0),
            }
        return stats

    def reset(self) -> None:
        """Reset all tracking state."""
        self._store.clear()


# Module-level singleton
_manager: Optional[BackpressureManager] = None


def get_backpressure_manager() -> BackpressureManager:
    """Get the global backpressure manager singleton."""
    global _manager
    if _manager is None:
        _manager = BackpressureManager()
    return _manager
