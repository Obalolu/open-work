"""Proxy manager — fetch, validate, rotate, and auto-refresh free proxies."""

from src.proxy.fetcher import fetch_all
from src.proxy.validator import validate_proxies, ProxyResult
from src.proxy.manager import ProxyManager

__all__ = ["fetch_all", "validate_proxies", "ProxyResult", "ProxyManager"]
