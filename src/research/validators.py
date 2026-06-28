"""Validation utilities for citations, URLs, authors, and years."""

from __future__ import annotations

import re
import ipaddress
from urllib.parse import urlparse
from datetime import datetime
from typing import Tuple

CURRENT_YEAR = datetime.now().year

# DOI prefixes indicating preprints (not peer-reviewed)
PREPRINT_DOI_PREFIXES = [
    "10.2139/ssrn",       # SSRN
    "10.48550/arxiv",     # arXiv
    "10.1101/",           # bioRxiv/medRxiv
    "10.20944/preprints", # Preprints.org
    "10.31219/osf",       # OSF Preprints
    "10.21203/rs",        # Research Square
    "10.26434/chemrxiv",  # ChemRxiv
]

# Generic/institutional author names to reject
GENERIC_AUTHOR_NAMES = {
    "working paper", "discussion paper", "technical report", "staff report",
    "research paper", "policy brief", "white paper", "occasional paper",
    "series", "anonymous", "unknown", "author", "authors", "editor",
    "editors", "committee", "commission", "group", "team", "staff",
    "admin", "administrator",
}

# Domain TLDs to reject as author names
DOMAIN_TLDS = {".com", ".org", ".net", ".edu", ".gov", ".io", ".ai", ".int", ".co"}


def is_safe_url(url: str) -> Tuple[bool, str]:
    """Check if a URL is safe to fetch (no SSRF).

    Returns:
        (is_safe, reason) tuple.
    """
    if not url:
        return False, "empty URL"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "invalid URL"

    if parsed.scheme not in ("http", "https"):
        return False, f"non-http scheme: {parsed.scheme}"

    hostname = parsed.hostname or ""
    if not hostname:
        return False, "no hostname"

    blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if hostname in blocked_hosts:
        return False, f"blocked host: {hostname}"

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False, f"private/reserved IP: {hostname}"
    except ValueError:
        pass  # Not an IP address, that's fine

    metadata_hosts = {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.azure.com",
    }
    if hostname in metadata_hosts:
        return False, f"cloud metadata endpoint: {hostname}"

    return True, "safe"


def validate_author_name(author_name: str) -> Tuple[bool, str]:
    """Validate an author name.

    Returns:
        (is_valid, reason) tuple.
    """
    if not author_name or not author_name.strip():
        return False, "empty name"

    name = author_name.strip()

    if len(name) <= 2:
        return False, f"too short: {name}"

    # Check for domain-like names
    name_lower = name.lower()
    for tld in DOMAIN_TLDS:
        if "." in name_lower and tld in name_lower:
            return False, f"domain-like name: {name}"

    # Check for URLs
    if name_lower.startswith(("http://", "https://")):
        return False, f"URL as author: {name}"

    # Check for generic/institutional names
    if name_lower in GENERIC_AUTHOR_NAMES:
        return False, f"generic/institutional name: {name}"

    return True, "valid"


def validate_publication_year(year: int | None) -> Tuple[bool, str, bool]:
    """Validate a publication year.

    Returns:
        (is_valid, reason, is_recent) tuple.
        is_recent is True if year == CURRENT_YEAR.
    """
    if year is None:
        return False, "year is None", False

    if not isinstance(year, int):
        return False, f"non-integer year: {year}", False

    if year > CURRENT_YEAR + 1:
        return False, f"future year: {year}", False

    if year < 1900:
        return False, f"year before 1900: {year}", False

    is_recent = year == CURRENT_YEAR
    return True, "valid", is_recent


def is_preprint_doi(doi: str) -> bool:
    """Check if a DOI indicates a preprint (not peer-reviewed)."""
    if not doi:
        return False
    doi_lower = doi.lower()
    return any(doi_lower.startswith(prefix) for prefix in PREPRINT_DOI_PREFIXES)


def strip_html_tags(text: str) -> str:
    """Strip HTML/JATS XML tags from text (e.g., Crossref abstracts)."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()
