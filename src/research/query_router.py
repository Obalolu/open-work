"""Smart query classification and API routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

QueryType = Literal["academic", "industry", "mixed"]
APIName = Literal["crossref", "openalex", "semantic_scholar", "arxiv"]


@dataclass
class QueryClassification:
    """Result of query classification."""
    query_type: QueryType
    confidence: float
    matched_patterns: list[str]
    api_chain: list[APIName]


# Academic keyword patterns
ACADEMIC_PATTERNS = [
    # Publication types
    "peer-reviewed", "peer reviewed", "scholarly article", "journal article",
    "academic paper", "research paper", "conference paper", "proceedings",
    "dissertation", "monograph",
    # Methodology
    "empirical study", "empirical research", "empirical analysis",
    "systematic review", "meta-analysis", "literature review",
    "randomized controlled trial", "rct", "cohort study",
    "longitudinal study", "qualitative research", "quantitative research",
    # Academic rigor
    "published in", "indexed in", "scopus", "web of science",
    "impact factor", "cited by", "citations",
    # Databases
    "pubmed", "jstor", "springer", "elsevier", "wiley",
    "taylor & francis", "sage", "oxford university press",
    # Research focus
    "theoretical framework", "conceptual model", "research methodology",
    "data analysis",
    # Fields
    "algorithm", "computational complexity", "machine learning",
    "neural network", "natural language processing", "computer vision",
    "climate science", "environmental impact", "carbon emissions",
    "sociological", "psychological", "behavioral", "cognitive",
]

# Industry keyword patterns
INDUSTRY_PATTERNS = [
    # Consulting firms
    "mckinsey", "boston consulting", "bcg", "bain", "deloitte",
    "accenture", "pwc", "kpmg", "gartner", "forrester",
    # Think tanks & orgs
    "brookings", "rand corporation", "world bank", "imf",
    "oecd", "united nations", "world health organization",
    "world economic forum", "wto",
    # Government
    "european commission", "us congress", "federal reserve",
    "fda", "epa", "cdc", "nih", "nasa",
    # Standards
    "iso standard", "ieee standard", "ietf", "w3c",
    # Document types
    "white paper", "whitepaper", "policy brief", "policy paper",
    "technical report", "industry report", "market research",
    "working paper", "briefing", "position paper",
    # Business
    "market analysis", "industry trends", "competitive landscape",
    "market forecast", "benchmark", "vendor", "saas",
    # Tech companies
    "openai", "anthropic", "google deepmind", "microsoft research",
]


class QueryRouter:
    """Classifies queries and routes to appropriate API chains."""

    def __init__(self) -> None:
        self.academic_patterns = ACADEMIC_PATTERNS
        self.industry_patterns = INDUSTRY_PATTERNS

    def classify_query(self, query: str) -> tuple[QueryType, float, list[str]]:
        """Classify a query as academic, industry, or mixed.

        Returns:
            (query_type, confidence, matched_patterns)
        """
        query_lower = query.lower()

        academic_matches = [p for p in self.academic_patterns if p in query_lower]
        industry_matches = [p for p in self.industry_patterns if p in query_lower]

        all_matches = academic_matches + industry_matches

        if industry_matches and not academic_matches:
            confidence = min(0.9, 0.5 + len(industry_matches) * 0.1)
            return "industry", confidence, industry_matches

        if academic_matches and not industry_matches:
            confidence = min(0.9, 0.5 + len(academic_matches) * 0.1)
            return "academic", confidence, academic_matches

        if academic_matches and industry_matches:
            if len(academic_matches) > len(industry_matches):
                return "academic", 0.6, all_matches
            elif len(industry_matches) > len(academic_matches):
                return "industry", 0.6, all_matches
            else:
                return "mixed", 0.5, all_matches

        return "mixed", 0.3, []

    def get_api_chain(self, query_type: QueryType) -> list[APIName]:
        """Get prioritized API chain for a query type.

        Strategy:
        - OpenAlex: fastest, broadest coverage, best for bulk discovery
        - Semantic Scholar: best relevance ranking, citation graphs
        - Crossref: DOI verification, clean metadata
        - arXiv: preprints, STEM focus
        """
        chains = {
            "academic": ["openalex", "semantic_scholar", "crossref", "arxiv"],
            "industry": ["openalex", "crossref", "semantic_scholar", "arxiv"],
            "mixed": ["openalex", "semantic_scholar", "crossref", "arxiv"],
        }
        return chains.get(query_type, chains["mixed"])

    def classify_and_route(self, query: str) -> QueryClassification:
        """Classify a query and return the full routing recommendation."""
        query_type, confidence, patterns = self.classify_query(query)
        api_chain = self.get_api_chain(query_type)
        return QueryClassification(
            query_type=query_type,
            confidence=confidence,
            matched_patterns=patterns,
            api_chain=api_chain,
        )
