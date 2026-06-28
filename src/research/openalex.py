"""OpenAlex API client for broad-coverage paper discovery."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.research.base import BaseAPIClient
from src.research.validators import (
    validate_author_name,
    is_preprint_doi,
    strip_html_tags,
)


class OpenAlexClient(BaseAPIClient):
    """OpenAlex API client — 250M+ works, 10 req/s free, credit-based.

    Env vars:
        OPENALEX_API_KEY: Optional API key for higher limits.
        OPENALEX_EMAIL: Email for polite pool (faster responses).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_per_second: float = 10.0,
        timeout: int = 15,
        max_retries: int = 3,
    ) -> None:
        key = api_key or os.environ.get("OPENALEX_API_KEY", "")
        email = os.environ.get("OPENALEX_EMAIL", "open-work@users.noreply.github.com")

        super().__init__(
            base_url="https://api.openalex.org",
            api_key=None,  # We pass key as query param, not header
            rate_limit_per_second=rate_limit_per_second,
            timeout=timeout,
            max_retries=max_retries,
            api_type="openalex",
        )
        self._openalex_key = key or None
        self.email = email

    def search_paper(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for a single paper. Returns first result."""
        results = self.search_papers(query, limit=1)
        return results[0] if results else None

    def search_papers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for multiple papers.

        Args:
            query: Search query string.
            limit: Max results (capped at 200 by API).

        Returns:
            List of normalized metadata dicts.
        """
        params: Dict[str, Any] = {
            "search": query,
            "per_page": min(limit, 200),
            "select": "id,doi,title,authorships,publication_year,primary_location,type,cited_by_count,abstract_inverted_index",
        }
        if self.email:
            params["mailto"] = self.email
        if self._openalex_key:
            params["api_key"] = self._openalex_key

        data = self._make_request("GET", "/works", params=params)
        if not data or "results" not in data:
            return []

        results = []
        for paper in data["results"]:
            metadata = self._extract_metadata(paper)
            if metadata:
                results.append(metadata)
        return results

    def get_paper_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Get a specific paper by DOI."""
        params = {
            "select": "id,doi,title,authorships,publication_year,primary_location,type,cited_by_count,abstract_inverted_index",
        }
        if self._openalex_key:
            params["api_key"] = self._openalex_key
        data = self._make_request(
            "GET",
            f"/works/https://doi.org/{doi}",
            params=params,
        )
        if not data:
            return None
        return self._extract_metadata(data)

    def _extract_metadata(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract normalized metadata from an OpenAlex paper object."""
        title = paper.get("title", "")
        if not title:
            return None

        # Authors
        authors = []
        for authorship in paper.get("authorships", []):
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if not name:
                continue
            last_name = name.split()[-1] if name else ""
            if last_name:
                is_valid, _ = validate_author_name(last_name)
                if is_valid:
                    authors.append(last_name)

        year = paper.get("publication_year")
        if not year or year == 0:
            return None

        # DOI
        doi_raw = paper.get("doi", "") or ""
        doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""

        # URL
        url = doi_raw or paper.get("id", "")

        # Journal/Publisher
        primary_location = paper.get("primary_location") or {}
        source = primary_location.get("source") or {}
        journal = source.get("display_name", "")
        publisher = source.get("host_organization_name", "")

        # Abstract reconstruction from inverted index
        abstract = self._reconstruct_abstract(paper.get("abstract_inverted_index"))

        # Source type
        source_type = self._map_source_type(paper.get("type", ""))

        # Citation count
        citation_count = paper.get("cited_by_count", 0) or 0

        # Confidence
        confidence = self._calculate_confidence(doi, journal, authors, citation_count)

        return {
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi,
            "url": url,
            "journal": journal,
            "publisher": publisher,
            "volume": "",
            "issue": "",
            "pages": "",
            "source_type": source_type,
            "confidence": confidence,
            "abstract": abstract,
            "citation_count": citation_count,
        }

    def _reconstruct_abstract(self, inverted_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
        """Reconstruct abstract text from OpenAlex's inverted index format."""
        if not inverted_index:
            return None

        # Build position -> word mapping
        max_pos = 0
        for positions in inverted_index.values():
            if positions:
                max_pos = max(max_pos, max(positions))

        words = [""] * (max_pos + 1)
        for word, positions in inverted_index.items():
            for pos in positions:
                if pos <= max_pos:
                    words[pos] = word

        return " ".join(w for w in words if w)

    def _map_source_type(self, oa_type: str) -> str:
        """Map OpenAlex type to standard source type."""
        mapping = {
            "journal-article": "journal",
            "article": "journal",
            "proceedings-article": "conference",
            "book": "book",
            "book-chapter": "book",
            "dissertation": "report",
            "dataset": "report",
            "preprint": "preprint",
            "report": "report",
        }
        return mapping.get(oa_type, "journal")

    def _calculate_confidence(
        self,
        doi: str,
        journal: str,
        authors: list,
        citation_count: int,
    ) -> float:
        """Calculate confidence score for the result."""
        score = 0.5
        if doi:
            score += 0.25
        if journal:
            score += 0.10
        if citation_count > 10:
            score += 0.10
        elif citation_count > 0:
            score += 0.05
        if authors:
            score += 0.05
        return min(1.0, score)
