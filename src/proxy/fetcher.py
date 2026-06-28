"""Fetch free proxies from 20+ sources."""

from __future__ import annotations

import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Regex to match ip:port or protocol://ip:port
_PROXY_RE = re.compile(
    r"(?:(?:https?|socks[45])://)?"
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})"
)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
]


def _ua() -> str:
    import random
    return random.choice(_USER_AGENTS)


def _safe_get(url: str, timeout: int = 10, **kwargs) -> Optional[requests.Response]:
    """GET with timeout and User-Agent."""
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", _ua())
    try:
        return requests.get(url, headers=headers, timeout=timeout, **kwargs)
    except Exception as e:
        logger.debug(f"Failed to fetch {url[:80]}: {e}")
        return None


def _extract_proxies(text: str) -> list[str]:
    """Extract unique ip:port strings from text."""
    found = set()
    for m in _PROXY_RE.finditer(text):
        ip, port = m.group(1), m.group(2)
        if ip.startswith("0.") or ip.startswith("127."):
            continue
        found.add(f"{ip}:{port}")
    return list(found)


# ─── Individual source fetchers ───────────────────────────────────────────────

def fetch_proxyscrape_api(protocol: str = "http", limit: int = 500) -> list[str]:
    """ProxyScrape v4 public API — updated every minute."""
    url = (
        f"https://api.proxyscrape.com/v4/free-proxy-list/get"
        f"?request=display_proxies&proxy_format=protocolipport&format=text"
        f"&protocol={protocol}&timeout=5000&anonymity=all"
    )
    r = _safe_get(url, timeout=15)
    if not r:
        return []
    proxies = []
    for line in r.text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: protocol://ip:port or ip:port
        m = _PROXY_RE.search(line)
        if m:
            proxies.append(f"{m.group(1)}:{m.group(2)}")
    logger.info(f"ProxyScrape API ({protocol}): {len(proxies)} proxies")
    return proxies[:limit]


def fetch_proxyscrape_github(protocol: str = "http") -> list[str]:
    """ProxyScrape GitHub mirror via jsDelivr CDN — updated every 5 min."""
    url = f"https://cdn.jsdelivr.net/gh/proxyscrape/free-proxy-list@main/proxies/protocols/{protocol}/data.txt"
    r = _safe_get(url, timeout=15)
    if not r:
        return []
    proxies = _extract_proxies(r.text)
    logger.info(f"ProxyScrape GitHub ({protocol}): {len(proxies)} proxies")
    return proxies


def fetch_the_speed_x() -> list[str]:
    """TheSpeedX/SOCKS-List — GitHub raw, popular proxy list."""
    urls = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    ]
    proxies = []
    for url in urls:
        r = _safe_get(url, timeout=15)
        if r:
            proxies.extend(_extract_proxies(r.text))
    logger.info(f"TheSpeedX: {len(proxies)} proxies")
    return proxies


def fetch_clarketm() -> list[str]:
    """clarketm/proxy-list — GitHub raw, updated daily."""
    url = "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
    r = _safe_get(url, timeout=15)
    if not r:
        return []
    proxies = _extract_proxies(r.text)
    logger.info(f"clarketm: {len(proxies)} proxies")
    return proxies


def fetch_monosans() -> list[str]:
    """monosans/proxy-list — GitHub raw, updated hourly."""
    urls = [
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    ]
    proxies = []
    for url in urls:
        r = _safe_get(url, timeout=15)
        if r:
            proxies.extend(_extract_proxies(r.text))
    logger.info(f"monosans: {len(proxies)} proxies")
    return proxies


def fetch_roosterkid() -> list[str]:
    """roosterkid/openproxylist — GitHub raw."""
    urls = [
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
    ]
    proxies = []
    for url in urls:
        r = _safe_get(url, timeout=15)
        if r:
            proxies.extend(_extract_proxies(r.text))
    logger.info(f"roosterkid: {len(proxies)} proxies")
    return proxies


def fetch_proxifly() -> list[str]:
    """proxifly/free-proxy-list — GitHub/jsDelivr, updated every 5 min."""
    urls = [
        "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt",
        "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt",
    ]
    proxies = []
    for url in urls:
        r = _safe_get(url, timeout=15)
        if r:
            proxies.extend(_extract_proxies(r.text))
    logger.info(f"proxifly: {len(proxies)} proxies")
    return proxies


def fetch_hw630590() -> list[str]:
    """hw630590/free-proxies — GitHub raw, updated every 15 min."""
    urls = [
        "https://raw.githubusercontent.com/hw630590/free-proxies/main/proxies/http/http.txt",
        "https://raw.githubusercontent.com/hw630590/free-proxies/main/proxies/socks5/socks5.txt",
    ]
    proxies = []
    for url in urls:
        r = _safe_get(url, timeout=15)
        if r:
            proxies.extend(_extract_proxies(r.text))
    logger.info(f"hw630590: {len(proxies)} proxies")
    return proxies


def fetch_iplocate() -> list[str]:
    """iplocate/free-proxy-list — GitHub raw, validated every 30 min."""
    urls = [
        "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/proxies/socks5.txt",
    ]
    proxies = []
    for url in urls:
        r = _safe_get(url, timeout=15)
        if r:
            proxies.extend(_extract_proxies(r.text))
    logger.info(f"iplocate: {len(proxies)} proxies")
    return proxies


def fetch_pubproxy() -> list[str]:
    """pubproxy.com API — no signup, random proxy per request."""
    proxies = []
    for ptype in ["http", "socks5"]:
        for _ in range(5):  # 5 requests per type = 10 total
            r = _safe_get(
                f"http://pubproxy.com/api/proxy?format=txt&type={ptype}&limit=5",
                timeout=10,
            )
            if r and r.status_code == 200:
                proxies.extend(_extract_proxies(r.text))
    logger.info(f"pubproxy: {len(proxies)} proxies")
    return proxies


def fetch_spys() -> list[str]:
    """spys.one raw proxy list."""
    url = "http://spys.me/proxy.txt"
    r = _safe_get(url, timeout=10)
    if not r:
        return []
    proxies = _extract_proxies(r.text)
    logger.info(f"spys.one: {len(proxies)} proxies")
    return proxies


def fetch_free_proxy_list_net() -> list[str]:
    """freeproxylist.net API."""
    url = "https://www.freeproxylist.net/api/proxylist?limit=100&type=http&anonymity=elite"
    r = _safe_get(url, timeout=10)
    if not r:
        return []
    proxies = _extract_proxies(r.text)
    logger.info(f"freeproxylist.net: {len(proxies)} proxies")
    return proxies


def fetch_proxy_list_download() -> list[str]:
    """proxy-list.download API."""
    proxies = []
    for proto in ["http", "socks5"]:
        url = f"https://www.proxy-list.download/api/v1/get?type={proto}&anon=elite"
        r = _safe_get(url, timeout=10)
        if r:
            for line in r.text.strip().splitlines():
                line = line.strip()
                if line and _PROXY_RE.match(line):
                    m = _PROXY_RE.search(line)
                    if m:
                        proxies.append(f"{m.group(1)}:{m.group(2)}")
    logger.info(f"proxy-list.download: {len(proxies)} proxies")
    return proxies


def fetch_databay() -> list[str]:
    """databay.com API — updated every 5 min."""
    url = "https://databay.com/api/v1/proxy-list?format=txt&limit=200"
    r = _safe_get(url, timeout=10)
    if not r:
        return []
    proxies = _extract_proxies(r.text)
    logger.info(f"databay: {len(proxies)} proxies")
    return proxies


def fetch_niek() -> list[str]:
    """niek.github.io/free-proxy-list — GitHub Pages."""
    url = "https://raw.githubusercontent.com/niek/niek.github.io/master/public/proxy-list/data.json"
    r = _safe_get(url, timeout=10)
    if not r:
        return []
    proxies = _extract_proxies(r.text)
    logger.info(f"niek: {len(proxies)} proxies")
    return proxies


def fetch_gfpcom() -> list[str]:
    """GetFreeProxy (gfpcom) — GitHub raw, updated hourly."""
    urls = [
        "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/http.txt",
        "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/socks5.txt",
    ]
    proxies = []
    for url in urls:
        r = _safe_get(url, timeout=15)
        if r:
            proxies.extend(_extract_proxies(r.text))
    logger.info(f"gfpcom: {len(proxies)} proxies")
    return proxies


def fetch_geonode() -> list[str]:
    """Geonode free proxy API — thousands of proxies."""
    url = "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps%2Csocks5"
    r = _safe_get(url, timeout=15)
    if not r:
        return []
    proxies = _extract_proxies(r.text)
    logger.info(f"geonode: {len(proxies)} proxies")
    return proxies


# ─── Master fetcher ────────────────────────────────────────────────────────────

# Source priority: high-quality sources first, bulk sources last
# Format: (name, function, priority) where 1=highest
SOURCES: list[tuple[str, callable, int]] = [
    # Tier 1 — curated, validated lists (high hit rate)
    ("ProxyScrape API (HTTP)", lambda: fetch_proxyscrape_api("http"), 1),
    ("ProxyScrape API (SOCKS5)", lambda: fetch_proxyscrape_api("socks5"), 1),
    ("ProxyScrape GitHub (HTTP)", lambda: fetch_proxyscrape_github("http"), 1),
    ("ProxyScrape GitHub (SOCKS5)", lambda: fetch_proxyscrape_github("socks5"), 1),
    ("databay", fetch_databay, 1),
    ("proxifly", fetch_proxifly, 1),
    # Tier 2 — good lists, moderate size
    ("TheSpeedX", fetch_the_speed_x, 2),
    ("clarketm", fetch_clarketm, 2),
    ("monosans", fetch_monosans, 2),
    ("roosterkid", fetch_roosterkid, 2),
    ("spys.one", fetch_spys, 2),
    ("pubproxy", fetch_pubproxy, 2),
    # Tier 3 — large but lower quality (bulk lists with many dead entries)
    ("hw630590", fetch_hw630590, 3),
    ("iplocate", fetch_iplocate, 3),
    ("gfpcom", fetch_gfpcom, 3),
    ("niek.github.io", fetch_niek, 3),
    ("geonode", fetch_geonode, 3),
]


def fetch_all(max_workers: int = 12) -> tuple[list[str], list[str]]:
    """Fetch proxies from all sources in parallel.

    Returns:
        (tier1_proxies, all_proxies) — tier1 are curated/high-quality.
    """
    all_proxies: set[str] = set()
    tier1_set: set[str] = set()
    source_counts: dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fn): (name, priority)
            for name, fn, priority in SOURCES
        }
        for future in as_completed(futures):
            name, priority = futures[future]
            try:
                proxies = future.result()
                source_counts[name] = len(proxies)
                all_proxies.update(proxies)
                if priority == 1:
                    tier1_set.update(proxies)
            except Exception as e:
                logger.warning(f"Source {name} failed: {e}")
                source_counts[name] = 0

    total_raw = sum(source_counts.values())
    logger.info(f"Fetched {total_raw} raw proxies from {len(SOURCES)} sources")
    logger.info(f"After dedup: {len(all_proxies)} total ({len(tier1_set)} tier-1)")
    for name, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {name}: {count}")

    return list(tier1_set), list(all_proxies)
