"""arXiv API client for preprint discovery."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

try:
    import arxiv
except ImportError:
    arxiv = None  # type: ignore

from src.research.validators import validate_author_name


class ArxivClient:
    """arXiv API client — free, no auth, great for STEM preprints.

    Uses the `arxiv` Python package. No rate limiting needed (package handles it).
    """

    def __init__(self) -> None:
        if arxiv is None:
            raise ImportError(
                "arxiv package not installed. Run: pip install arxiv"
            )

    def search_papers(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search arXiv for papers.

        Args:
            query: Search query string.
            max_results: Maximum number of results.

        Returns:
            List of normalized metadata dicts.
        """
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        client = arxiv.Client()
        results = []
        for result in client.results(search):
            metadata = self._extract_metadata(result)
            if metadata:
                results.append(metadata)
        return results

    def search_paper(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for a single paper. Returns first result."""
        results = self.search_papers(query, max_results=1)
        return results[0] if results else None

    def _extract_metadata(self, result: Any) -> Optional[Dict[str, Any]]:
        """Extract normalized metadata from an arxiv result."""
        title = result.title
        if not title:
            return None

        # Authors
        authors = []
        for author in result.authors:
            name = author.name or ""
            if name:
                last_name = name.split()[-1]
                if last_name:
                    is_valid, _ = validate_author_name(last_name)
                    if is_valid:
                        authors.append(last_name)

        # Year from published date
        year = None
        if result.published:
            year = result.published.year

        if not year:
            return None

        # DOI
        doi = result.doi or ""

        # arXiv ID and URL
        arxiv_id = result.entry_id.split("/")[-1] if result.entry_id else ""
        url = result.entry_id or ""

        # Abstract
        abstract = result.summary or ""

        # Journal ref
        journal = result.journal_ref or ""

        return {
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi,
            "url": url,
            "journal": journal,
            "publisher": "arXiv",
            "volume": "",
            "issue": "",
            "pages": "",
            "source_type": "preprint",
            "confidence": 0.6,
            "abstract": abstract,
            "citation_count": 0,
            "arxiv_id": arxiv_id,
        }
