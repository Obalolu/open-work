"""Semantic Scholar API client for academic paper search."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.research.base import BaseAPIClient
from src.research.validators import validate_author_name


class SemanticScholarClient(BaseAPIClient):
    """Semantic Scholar API client — 200M+ papers, relevance-ranked discovery.

    Env vars:
        SEMANTIC_SCHOLAR_API_KEY: Optional API key for higher rate limits.
        Without key: ~1 req/3s (shared pool, throttled during heavy use).
        With key: 1 req/s (starter), can be raised on request.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_per_second: float = 0.5,
        timeout: int = 15,
        max_retries: int = 5,
    ) -> None:
        key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

        # With API key, can go faster
        if key:
            rate_limit_per_second = min(rate_limit_per_second, 10.0)
        else:
            rate_limit_per_second = 0.5  # Free tier: ~1 req/2s safe

        super().__init__(
            base_url="https://api.semanticscholar.org",
            api_key=key or None,
            rate_limit_per_second=rate_limit_per_second,
            timeout=timeout,
            max_retries=max_retries,
            api_type="semantic_scholar",
        )

    def search_paper(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for a single paper. Returns first result."""
        results = self.search_papers(query, limit=1)
        return results[0] if results else None

    def search_papers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for multiple papers.

        Args:
            query: Search query string.
            limit: Max results (capped at 100 by API).

        Returns:
            List of normalized metadata dicts, sorted by citation count.
        """
        params: Dict[str, Any] = {
            "query": query,
            "limit": min(limit, 100),
            "fields": "title,authors,year,venue,externalIds,url,citationCount,publicationTypes,abstract",
        }

        data = self._make_request("GET", "/graph/v1/paper/search", params=params)
        if not data or "data" not in data:
            return []

        results = []
        for paper in data["data"]:
            metadata = self._extract_metadata(paper)
            if metadata:
                results.append(metadata)

        results.sort(key=lambda r: r.get("citation_count", 0), reverse=True)
        return results

    def get_paper_details(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific paper by ID."""
        data = self._make_request(
            "GET",
            f"/graph/v1/paper/{paper_id}",
            params={
                "fields": "title,authors,year,venue,externalIds,url,citationCount,publicationTypes,abstract",
            },
        )
        if not data:
            return None
        return self._extract_metadata(data)

    def _extract_metadata(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract normalized metadata from a Semantic Scholar paper object."""
        title = paper.get("title", "")
        if not title:
            return None

        # Authors — take last name from full name
        authors = []
        for author in paper.get("authors", []):
            name = author.get("name", "")
            if name:
                last_name = name.split()[-1]
                if last_name:
                    is_valid, _ = validate_author_name(last_name)
                    if is_valid:
                        authors.append(last_name)

        year = paper.get("year")
        if not year or year == 0:
            return None

        # DOI from externalIds
        external_ids = paper.get("externalIds") or {}
        doi = external_ids.get("DOI", "")

        # URL — prefer DOI URL, then arXiv URL, then S2 URL
        url = paper.get("url", "")
        if doi:
            url = f"https://doi.org/{doi}"
        elif external_ids.get("ArXiv"):
            url = f"https://arxiv.org/abs/{external_ids['ArXiv']}"

        # Venue / journal
        venue = paper.get("venue", "") or ""

        # Source type from publicationTypes
        pub_types = [t.lower() for t in (paper.get("publicationTypes") or [])]
        source_type = self._map_source_type(pub_types, venue)

        # Citation count
        citation_count = paper.get("citationCount", 0) or 0

        # Abstract
        abstract = paper.get("abstract", "") or None

        # Confidence
        confidence = self._calculate_confidence(doi, url, venue, authors, citation_count)

        return {
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi,
            "url": url,
            "journal": venue,
            "publisher": "",
            "volume": "",
            "issue": "",
            "pages": "",
            "source_type": source_type,
            "confidence": confidence,
            "abstract": abstract,
            "citation_count": citation_count,
        }

    def _map_source_type(self, pub_types: list[str], venue: str) -> str:
        """Map Semantic Scholar publication types to standard source type."""
        if "journalarticle" in pub_types or "journal" in pub_types:
            return "journal"
        if any(t in pub_types for t in ["conference", "proceedingsarticle"]):
            return "conference"
        if "book" in pub_types:
            return "book"
        if any(t in pub_types for t in ["review", "editorial"]):
            return "journal"

        # Guess from venue name
        venue_lower = venue.lower()
        if any(w in venue_lower for w in ["conference", "proceedings", "workshop", "symposium"]):
            return "conference"

        return "journal"

    def _calculate_confidence(
        self,
        doi: str,
        url: str,
        venue: str,
        authors: list,
        citation_count: int,
    ) -> float:
        """Calculate confidence score."""
        score = 0.4
        if doi:
            score += 0.3
        elif url:
            score += 0.1
        if venue:
            score += 0.1
        if authors:
            score += 0.05
        if citation_count > 100:
            score += 0.1
        elif citation_count > 10:
            score += 0.05
        return min(1.0, score)


# --- Backward-compatible async functions for existing code ---

async def search_papers(
    query: str,
    max_results: int = 15,
    year_range: str | None = None,
    fields_of_study: list[str] | None = None,
) -> list[Dict[str, Any]]:
    """Search Semantic Scholar for papers (backward-compatible async wrapper).

    Returns list of normalized metadata dicts.
    """
    client = SemanticScholarClient()
    try:
        return client.search_papers(query, limit=max_results)
    finally:
        client.close()


async def get_paper_details(paper_id: str) -> Dict[str, Any] | None:
    """Get detailed information about a specific paper by ID."""
    client = SemanticScholarClient()
    try:
        return client.get_paper_details(paper_id)
    finally:
        client.close()
