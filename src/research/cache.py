"""Persistent JSON cache for citation research results."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE_FILE = ".citation_cache.json"


class CitationCache:
    """Persistent JSON cache mapping topics to citation results."""

    def __init__(self, cache_file: str | Path = DEFAULT_CACHE_FILE) -> None:
        self.cache_file = Path(cache_file)
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
        """Save cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self._cache)} cached topics to {self.cache_file}")
        except OSError as e:
            logger.warning(f"Failed to save citation cache: {e}")

    def has(self, topic: str) -> bool:
        """Check if a topic is cached."""
        self._ensure_loaded()
        return topic in self._cache

    def get(self, topic: str) -> Optional[list[dict]]:
        """Get cached results for a topic.

        Returns:
            List of result dicts, or None if not cached.
            Empty list [] means "cached as no results".
        """
        self._ensure_loaded()
        value = self._cache.get(topic)
        if value is None:
            # Could be "not cached" (key missing) or "cached as empty" (value is None)
            if topic in self._cache:
                return []  # Explicitly cached as empty
            return None  # Not in cache at all
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            # Legacy single-result format
            return [value]
        return None

    def set(self, topic: str, results: list[dict]) -> None:
        """Cache results for a topic.

        Args:
            topic: The research query/topic.
            results: List of citation metadata dicts (or empty list for "no results").
        """
        self._ensure_loaded()
        self._cache[topic] = results
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
