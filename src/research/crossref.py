"""Crossref API client for DOI verification and bibliographic metadata."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.research.base import BaseAPIClient
from src.research.validators import (
    validate_author_name,
    strip_html_tags,
)


class CrossrefClient(BaseAPIClient):
    """Crossref API client — 150M+ works, 50 req/s free, DOI registry.

    Best for: verifying papers exist, fetching clean metadata by DOI.
    No API key required. Polite pool via mailto param.
    """

    def __init__(
        self,
        rate_limit_per_second: float = 10.0,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        super().__init__(
            base_url="https://api.crossref.org",
            rate_limit_per_second=rate_limit_per_second,
            timeout=timeout,
            max_retries=max_retries,
            api_type="crossref",
        )

    def search_paper(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for a single paper. Returns first result."""
        results = self.search_papers(query, limit=1)
        return results[0] if results else None

    def search_papers(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for multiple papers.

        Args:
            query: Search query string.
            limit: Max results (Crossref uses 'rows').

        Returns:
            List of normalized metadata dicts.
        """
        params = {
            "query": query,
            "rows": limit,
            "sort": "relevance",
            "select": "DOI,title,author,published,container-title,publisher,volume,issue,page,type,abstract",
        }

        data = self._make_request("GET", "/works", params=params)
        if not data or "message" not in data:
            return []

        items = data["message"].get("items", [])
        results = []
        for item in items:
            metadata = self._extract_metadata(item)
            if metadata:
                results.append(metadata)
        return results

    def get_paper_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Get a specific paper by DOI."""
        data = self._make_request(
            "GET",
            f"/works/{doi}",
            params={"select": "DOI,title,author,published,container-title,publisher,volume,issue,page,type,abstract"},
        )
        if not data or "message" not in data:
            return None
        return self._extract_metadata(data["message"])

    def _extract_metadata(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract normalized metadata from a Crossref work object."""
        # Title (Crossref returns as list)
        titles = paper.get("title", [])
        title = titles[0] if titles else ""
        if not title:
            return None

        # Authors
        authors = []
        for author_raw in paper.get("author", []):
            family = author_raw.get("family", "")
            given = author_raw.get("given", "")
            if family:
                is_valid, _ = validate_author_name(family)
                if is_valid:
                    authors.append(family)

        # Year
        year = None
        published = paper.get("published", {})
        date_parts = published.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

        if not year:
            published_online = paper.get("published-online", {})
            date_parts = published_online.get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]

        if not year or year == 0:
            return None

        # DOI
        doi = paper.get("DOI", "")

        # URL
        url = f"https://doi.org/{doi}" if doi else ""

        # Journal
        container = paper.get("container-title", [])
        journal = container[0] if container else ""

        # Publisher
        publisher = paper.get("publisher", "")

        # Volume, issue, pages
        volume = paper.get("volume", "")
        issue = paper.get("issue", "")
        pages = paper.get("page", "")

        # Abstract (strip JATS XML tags)
        abstract = strip_html_tags(paper.get("abstract", ""))

        # Source type
        source_type = self._map_source_type(paper.get("type", ""))

        # Confidence
        confidence = self._calculate_confidence(doi, journal, publisher, authors)

        return {
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi,
            "url": url,
            "journal": journal,
            "publisher": publisher,
            "volume": str(volume) if volume else "",
            "issue": str(issue) if issue else "",
            "pages": str(pages) if pages else "",
            "source_type": source_type,
            "confidence": confidence,
            "abstract": abstract or None,
            "citation_count": 0,
        }

    def _map_source_type(self, cr_type: str) -> str:
        """Map Crossref type to standard source type."""
        mapping = {
            "journal-article": "journal",
            "proceedings-article": "conference",
            "book": "book",
            "book-chapter": "book",
            "report": "report",
            "posted-content": "preprint",
            "dataset": "report",
        }
        return mapping.get(cr_type, "journal")

    def _calculate_confidence(
        self,
        doi: str,
        journal: str,
        publisher: str,
        authors: list,
    ) -> float:
        """Calculate confidence score."""
        score = 0.5
        if doi:
            score += 0.30
        if journal:
            score += 0.10
        if publisher:
            score += 0.05
        if authors:
            score += 0.05
        return min(1.0, score)
