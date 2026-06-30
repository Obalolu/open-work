"""Persistent JSON cache for citation research results."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE_FILE = ".citation_cache.json"
DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 1 week


def _get_default_cache_path() -> Path:
    """Return a stable cache path under the project data directory."""
    try:
        from src.config import get_project_root
        return get_project_root() / DEFAULT_CACHE_FILE
    except Exception:
        return Path(DEFAULT_CACHE_FILE)


class CitationCache:
    """Persistent JSON cache mapping topics to citation results."""

    def __init__(
        self,
        cache_file: str | Path | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.cache_file = Path(cache_file) if cache_file else _get_default_cache_path()
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, Any] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()
            self._loaded = True

    def _load(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            self._cache = {}
            return

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Normalize format: ensure dict
            if isinstance(data, dict):
                self._cache = data
            else:
                self._cache = {}
            logger.debug(f"Loaded {len(self._cache)} cached topics from {self.cache_file}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load citation cache: {e}")
            self._cache = {}

    def _save(self) -> None:
        """Save cache to disk with advisory locking."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            lock_path = self.cache_file.with_suffix(self.cache_file.suffix + ".lock")
            with open(lock_path, "w") as lock_file:
                try:
                    if hasattr(os, "flock"):
                        import fcntl
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    with open(self.cache_file, "w", encoding="utf-8") as f:
                        json.dump(self._cache, f, indent=2, ensure_ascii=False)
                finally:
                    if hasattr(os, "flock"):
                        import fcntl
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            logger.debug(f"Saved {len(self._cache)} cached topics to {self.cache_file}")
        except OSError as e:
            logger.warning(f"Failed to save citation cache: {e}")

    def has(self, topic: str) -> bool:
        """Check if a topic is cached and not expired."""
        self._ensure_loaded()
        entry = self._cache.get(topic)
        if not isinstance(entry, dict) or "results" not in entry:
            return topic in self._cache  # legacy raw list
        cached_at = entry.get("cached_at", 0)
        if time.time() - cached_at > self.ttl_seconds:
            return False
        return True

    def get(self, topic: str) -> Optional[list[dict]]:
        """Get cached results for a topic.

        Returns:
            List of result dicts, or None if not cached or expired.
        """
        self._ensure_loaded()
        entry = self._cache.get(topic)
        if entry is None:
            return None

        # New format: {"results": [...], "cached_at": timestamp}
        if isinstance(entry, dict):
            results = entry.get("results", [])
            cached_at = entry.get("cached_at", 0)
            if time.time() - cached_at > self.ttl_seconds:
                return None
            return results if isinstance(results, list) else None

        # Legacy formats
        if isinstance(entry, list):
            return entry
        if isinstance(entry, dict):
            return [entry]
        return None

    def set(self, topic: str, results: list[dict]) -> None:
        """Cache results for a topic.

        Empty results are not cached so transient failures can be retried.
        """
        if not results:
            logger.debug(f"Not caching empty results for '{topic[:50]}...'")
            return
        self._ensure_loaded()
        self._cache[topic] = {
            "results": results,
            "cached_at": time.time(),
        }
        self._save()

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache = {}
        self._save()

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._cache)

    def __contains__(self, topic: str) -> bool:
        return self.has(topic)
