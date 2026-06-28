"""Multi-source citation research orchestrator.

Coordinates parallel queries across Semantic Scholar, OpenAlex, Crossref, and arXiv
with caching, round-robin selection, and graceful fallback.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.research.base import BaseAPIClient
from src.research.semantic_scholar import SemanticScholarClient
from src.research.openalex import OpenAlexClient
from src.research.crossref import CrossrefClient
from src.research.cache import CitationCache
from src.research.query_router import QueryRouter, QueryClassification
from src.research.validators import (
    validate_author_name,
    validate_publication_year,
    is_preprint_doi,
)

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A single citation entry for the citation database."""
    cite_id: str
    title: str
    authors: list[str]
    year: int | None
    venue: str
    abstract_summary: str
    paper_url: str
    paper_id: str
    doi: str = ""
    source_type: str = "journal"
    citation_count: int = 0
    confidence: float = 0.0
    api_source: str = ""


@dataclass
class ResearchSummary:
    """Aggregated research results for a chapter."""
    citations: list[Citation]
    summaries: dict[str, str]  # section_id -> summary text
    raw_results: list[dict]  # raw metadata dicts from APIs


class CitationResearcher:
    """Multi-source citation research orchestrator.

    Queries Semantic Scholar, OpenAlex, Crossref, and arXiv in parallel,
    deduplicates by DOI, validates results, and caches to disk.
    """

    def __init__(
        self,
        enable_semantic_scholar: bool = True,
        enable_openalex: bool = True,
        enable_crossref: bool = True,
        enable_arxiv: bool = True,
        enable_smart_routing: bool = True,
        cache_file: str = ".citation_cache.json",
        verbose: bool = False,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.enable_semantic_scholar = enable_semantic_scholar
        self.enable_openalex = enable_openalex
        self.enable_crossref = enable_crossref
        self.enable_arxiv = enable_arxiv
        self.enable_smart_routing = enable_smart_routing
        self.verbose = verbose
        self.progress_callback = progress_callback

        # Initialize API clients
        self._clients: Dict[str, BaseAPIClient] = {}
        if enable_semantic_scholar:
            self._clients["semantic_scholar"] = SemanticScholarClient()
        if enable_openalex:
            self._clients["openalex"] = OpenAlexClient()
        if enable_crossref:
            self._clients["crossref"] = CrossrefClient()
        if enable_arxiv:
            try:
                from src.research.arxiv import ArxivClient
                self._arxiv_client = ArxivClient()
            except ImportError:
                logger.warning("arxiv package not installed — arXiv search disabled")
                self._arxiv_client = None
        else:
            self._arxiv_client = None

        # Query router
        self.query_router = QueryRouter() if enable_smart_routing else None

        # Cache
        self.cache = CitationCache(cache_file)

        # Round-robin tracking
        self.source_usage_count: Dict[str, int] = {
            "semantic_scholar": 0,
            "openalex": 0,
            "crossref": 0,
            "arxiv": 0,
        }

    def research(self, query: str) -> list[Citation]:
        """Research a query across all enabled sources.

        Args:
            query: Research query/topic string.

        Returns:
            List of validated Citation objects.
        """
        # Check cache first
        cached = self.cache.get(query)
        if cached is not None:
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return [self._dict_to_citation(r) for r in cached]

        # Classify query and get API chain
        if self.query_router:
            classification = self.query_router.classify_and_route(query)
            api_chain = classification.api_chain
            logger.debug(
                f"Query classified as {classification.query_type} "
                f"(confidence={classification.confidence:.2f}) -> chain: {api_chain}"
            )
        else:
            api_chain = ["openalex", "semantic_scholar", "crossref", "arxiv"]

        # Filter to enabled APIs
        enabled_chain = [a for a in api_chain if self._is_api_enabled(a)]

        # Execute queries — parallel if multiple APIs
        all_results: list[dict] = []
        if len(enabled_chain) > 1:
            all_results = self._parallel_query(query, enabled_chain)
        else:
            all_results = self._sequential_query(query, enabled_chain)

        # Deduplicate by DOI
        deduplicated = self._deduplicate(all_results)

        # Validate
        validated = [r for r in deduplicated if self._validate_result(r)]

        # Cache (even if empty)
        self.cache.set(query, validated)

        # Convert to Citation objects
        citations = [self._dict_to_citation(r) for r in validated]

        logger.info(
            f"Research for '{query[:40]}...': "
            f"{len(validated)} citations from {len(all_results)} raw results"
        )
        return citations

    def research_batch(self, queries: list[str]) -> list[Citation]:
        """Research multiple queries and combine results.

        Args:
            queries: List of research queries.

        Returns:
            Combined list of Citation objects, deduplicated across queries.
        """
        all_citations: list[Citation] = []
        seen_dois: set[str] = set()
        seen_titles: set[str] = set()

        for query in queries:
            citations = self.research(query)
            for c in citations:
                doi_key = c.doi.lower() if c.doi else ""
                title_key = c.title.lower().strip() if c.title else ""
                if doi_key and doi_key in seen_dois:
                    continue
                if title_key and title_key in seen_titles:
                    continue
                if doi_key:
                    seen_dois.add(doi_key)
                if title_key:
                    seen_titles.add(title_key)
                all_citations.append(c)

        return all_citations

    def _parallel_query(self, query: str, api_chain: list[str]) -> list[dict]:
        """Query multiple APIs in parallel."""
        all_results: list[dict] = []
        futures_map: dict = {}

        executor = ThreadPoolExecutor(max_workers=4)
        try:
            for api_name in api_chain:
                future = executor.submit(self._query_single_api, query, api_name)
                futures_map[future] = api_name

            for future in as_completed(futures_map, timeout=30):
                api_name = futures_map[future]
                try:
                    results = future.result(timeout=0)
                    if results:
                        all_results.extend(results)
                        logger.debug(f"{api_name}: {len(results)} results")
                except Exception as e:
                    logger.warning(f"{api_name} query failed: {e}")
        except TimeoutError:
            logger.debug("Parallel query timeout — collecting completed results")
            for future, api_name in futures_map.items():
                if future.done():
                    try:
                        results = future.result(timeout=0)
                        if results:
                            all_results.extend(results)
                    except Exception:
                        pass
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        return all_results

    def _sequential_query(self, query: str, api_chain: list[str]) -> list[dict]:
        """Query APIs sequentially (fallback)."""
        all_results: list[dict] = []

        for api_name in api_chain:
            try:
                results = self._query_single_api(query, api_name)
                if results:
                    all_results.extend(results)
                    logger.debug(f"{api_name}: {len(results)} results")
            except Exception as e:
                logger.warning(f"{api_name} query failed: {e}")

        return all_results

    def _query_single_api(self, query: str, api_name: str) -> list[dict]:
        """Query a single API and return results."""
        if api_name == "arxiv":
            if self._arxiv_client:
                return self._arxiv_client.search_papers(query, max_results=10)
            return []

        client = self._clients.get(api_name)
        if not client:
            return []

        # For OpenAlex and Crossref, get multiple results
        if api_name in ("openalex", "crossref") and hasattr(client, "search_papers"):
            return client.search_papers(query, limit=10)

        # For Semantic Scholar, get multiple results
        if api_name == "semantic_scholar" and hasattr(client, "search_papers"):
            return client.search_papers(query, limit=10)

        # Fallback to single result
        result = client.search_paper(query)
        return [result] if result else []

    def _deduplicate(self, results: list[dict]) -> list[dict]:
        """Deduplicate results by DOI (primary) and title (secondary)."""
        seen_dois: dict[str, dict] = {}
        seen_titles: dict[str, dict] = {}
        unique: list[dict] = []

        for result in results:
            doi = (result.get("doi") or "").lower().strip()
            title = (result.get("title") or "").lower().strip()

            # DOI-based dedup (strongest)
            if doi:
                if doi in seen_dois:
                    # Keep the one with more metadata
                    existing = seen_dois[doi]
                    if self._has_better_metadata(result, existing):
                        unique.remove(existing)
                        unique.append(result)
                        seen_dois[doi] = result
                    continue
                seen_dois[doi] = result

            # Title-based dedup (fallback)
            if title:
                if title in seen_titles:
                    continue
                seen_titles[title] = result

            unique.append(result)

        return unique

    def _has_better_metadata(self, new: dict, existing: dict) -> bool:
        """Check if 'new' has better metadata than 'existing'."""
        score_new = sum(1 for k in ["abstract", "journal", "doi", "authors"]
                       if new.get(k))
        score_existing = sum(1 for k in ["abstract", "journal", "doi", "authors"]
                            if existing.get(k))
        return score_new > score_existing

    def _validate_result(self, result: dict) -> bool:
        """Validate a result has minimum required fields."""
        title = result.get("title", "")
        if not title or len(title) < 5:
            return False

        year = result.get("year")
        if year:
            is_valid, reason, _ = validate_publication_year(year)
            if not is_valid:
                return False

        authors = result.get("authors", [])
        if not authors:
            return False

        return True

    def _dict_to_citation(self, data: dict) -> Citation:
        """Convert a metadata dict to a Citation object."""
        return Citation(
            cite_id="",  # Assigned later by compiler
            title=data.get("title", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            venue=data.get("journal", ""),
            abstract_summary=(data.get("abstract") or "")[:300],
            paper_url=data.get("url", ""),
            paper_id=data.get("doi", "") or data.get("url", ""),
            doi=data.get("doi", ""),
            source_type=data.get("source_type", "journal"),
            citation_count=data.get("citation_count", 0),
            confidence=data.get("confidence", 0.0),
            api_source=data.get("api_source", ""),
        )

    def _is_api_enabled(self, api_name: str) -> bool:
        """Check if an API source is enabled."""
        mapping = {
            "semantic_scholar": self.enable_semantic_scholar,
            "openalex": self.enable_openalex,
            "crossref": self.enable_crossref,
            "arxiv": self.enable_arxiv,
        }
        return mapping.get(api_name, False)

    def close(self) -> None:
        """Close all API client sessions."""
        for client in self._clients.values():
            client.close()

    def __enter__(self) -> CitationResearcher:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
