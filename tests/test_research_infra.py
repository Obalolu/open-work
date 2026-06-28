"""Tests for the research infrastructure modules."""

import json
import time
import threading
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.research.retry import (
    exponential_backoff_with_jitter,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
)
from src.research.validators import (
    is_safe_url,
    validate_author_name,
    validate_publication_year,
    is_preprint_doi,
    strip_html_tags,
)
from src.research.backpressure import BackpressureManager, APIType
from src.research.cache import CitationCache
from src.research.query_router import QueryRouter


# === retry.py tests ===

class TestExponentialBackoff:
    def test_attempt_0(self):
        delay = exponential_backoff_with_jitter(0, base_delay=1.0, jitter=False)
        assert delay == 1.0

    def test_attempt_1(self):
        delay = exponential_backoff_with_jitter(1, base_delay=1.0, jitter=False)
        assert delay == 2.0

    def test_attempt_3(self):
        delay = exponential_backoff_with_jitter(3, base_delay=1.0, jitter=False)
        assert delay == 8.0

    def test_max_delay_cap(self):
        delay = exponential_backoff_with_jitter(100, base_delay=1.0, max_delay=30.0, jitter=False)
        assert delay == 30.0

    def test_jitter_adds_variance(self):
        delays = [exponential_backoff_with_jitter(2, base_delay=1.0, jitter=True) for _ in range(20)]
        # All should be around 4.0 ± 25%
        assert all(2.0 <= d <= 6.0 for d in delays)
        # Should have some variance
        assert len(set(round(d, 2) for d in delays)) > 1


class TestCircuitBreaker:
    def setup_method(self):
        # Reset singleton instances
        CircuitBreaker._instances.clear()

    def test_starts_closed(self):
        cb = CircuitBreaker("test1")
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test2", CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            cb.record_failure(Exception("test"))
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(
            "test3",
            CircuitBreakerConfig(failure_threshold=2, reset_timeout=0.1),
        )
        cb.record_failure(Exception("test"))
        cb.record_failure(Exception("test"))
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_after_successes_in_half_open(self):
        cb = CircuitBreaker(
            "test4",
            CircuitBreakerConfig(failure_threshold=2, reset_timeout=0.05, success_threshold=2),
        )
        cb.record_failure(Exception("test"))
        cb.record_failure(Exception("test"))
        time.sleep(0.1)
        cb.allow_request()  # -> HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_singleton_per_name(self):
        cb1 = CircuitBreaker("singleton_test")
        cb2 = CircuitBreaker("singleton_test")
        assert cb1 is cb2

    def test_protect_decorator(self):
        cb = CircuitBreaker("protect_test", CircuitBreakerConfig(failure_threshold=2))

        @cb.protect
        def sometimes_fails(should_fail):
            if should_fail:
                raise ValueError("fail")
            return "ok"

        assert sometimes_fails(False) == "ok"
        with pytest.raises(ValueError):
            sometimes_fails(True)  # raises, recorded as failure
        with pytest.raises(ValueError):
            sometimes_fails(True)  # 2nd failure -> OPEN
        with pytest.raises(CircuitOpenError):
            sometimes_fails(False)  # Circuit is open

    def test_reset(self):
        cb = CircuitBreaker("reset_test", CircuitBreakerConfig(failure_threshold=2))
        cb.record_failure(Exception("test"))
        cb.record_failure(Exception("test"))
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


# === validators.py tests ===

class TestIsSafeUrl:
    def test_safe_https(self):
        assert is_safe_url("https://example.com/paper")[0] is True

    def test_safe_http(self):
        assert is_safe_url("http://example.com/paper")[0] is True

    def test_empty_url(self):
        assert is_safe_url("")[0] is False

    def test_ftp_scheme(self):
        assert is_safe_url("ftp://example.com")[0] is False

    def test_localhost(self):
        assert is_safe_url("http://localhost:8080")[0] is False

    def test_127_0_0_1(self):
        assert is_safe_url("http://127.0.0.1/api")[0] is False

    def test_private_ip(self):
        assert is_safe_url("http://192.168.1.1/api")[0] is False

    def test_cloud_metadata(self):
        assert is_safe_url("http://169.254.169.254/metadata")[0] is False


class TestValidateAuthorName:
    def test_valid_name(self):
        assert validate_author_name("Smith")[0] is True

    def test_empty(self):
        assert validate_author_name("")[0] is False

    def test_too_short(self):
        assert validate_author_name("A")[0] is False

    def test_domain_name(self):
        assert validate_author_name("example.com")[0] is False

    def test_url(self):
        assert validate_author_name("https://example.com")[0] is False

    def test_generic_name(self):
        assert validate_author_name("Anonymous")[0] is False
        assert validate_author_name("Author")[0] is False


class TestValidatePublicationYear:
    def test_valid_year(self):
        is_valid, reason, is_recent = validate_publication_year(2023)
        assert is_valid is True

    def test_none_year(self):
        is_valid, reason, _ = validate_publication_year(None)
        assert is_valid is False

    def test_future_year(self):
        is_valid, reason, _ = validate_publication_year(2099)
        assert is_valid is False

    def test_old_year(self):
        is_valid, reason, _ = validate_publication_year(1800)
        assert is_valid is False


class TestIsPreprintDoi:
    def test_arxiv(self):
        assert is_preprint_doi("10.48550/arXiv.2301.12345") is True

    def test_ssrn(self):
        assert is_preprint_doi("10.2139/ssrn.1234567") is True

    def test_regular_doi(self):
        assert is_preprint_doi("10.1038/s41586-021-03819-2") is False

    def test_empty(self):
        assert is_preprint_doi("") is False


class TestStripHtmlTags:
    def test_strips_tags(self):
        assert strip_html_tags("<p>Hello <b>world</b></p>") == "Hello world"

    def test_empty(self):
        assert strip_html_tags("") == ""

    def test_no_tags(self):
        assert strip_html_tags("plain text") == "plain text"


# === backpressure.py tests ===

class TestBackpressureManager:
    def test_initial_state(self):
        bp = BackpressureManager()
        assert bp.get_global_pressure() == 0.0

    def test_signal_429_increases_pressure(self):
        bp = BackpressureManager()
        bp.signal_429(APIType.SEMANTIC_SCHOLAR)
        assert bp.get_global_pressure() > 0.0

    def test_multiple_429s_increase_pressure(self):
        bp = BackpressureManager()
        # Signal on all APIs to build real pressure
        for api in [APIType.SEMANTIC_SCHOLAR, APIType.OPENALEX, APIType.CROSSREF]:
            for _ in range(10):
                bp.signal_429(api)
        assert bp.get_global_pressure() > 0.25

    def test_recommended_delay_increases(self):
        bp = BackpressureManager()
        for _ in range(5):
            bp.signal_429(APIType.OPENALEX)
        delay = bp.get_recommended_delay()
        assert delay > 0.1

    def test_adaptive_batch_size_decreases(self):
        bp = BackpressureManager()
        # Heavy pressure across all APIs
        for api in [APIType.SEMANTIC_SCHOLAR, APIType.OPENALEX, APIType.CROSSREF, APIType.ARXIV]:
            for _ in range(20):
                bp.signal_429(api)
        size = bp.get_adaptive_batch_size()
        assert size <= 15

    def test_reset(self):
        bp = BackpressureManager()
        bp.signal_429(APIType.SEMANTIC_SCHOLAR)
        bp.reset()
        assert bp.get_global_pressure() == 0.0

    def test_stats(self):
        bp = BackpressureManager()
        stats = bp.get_stats()
        assert "global_pressure" in stats
        assert "apis" in stats
        assert "semantic_scholar" in stats["apis"]


# === cache.py tests ===

class TestCitationCache:
    def test_round_trip(self, tmp_path):
        cache_file = tmp_path / "test_cache.json"
        cache = CitationCache(cache_file)

        results = [{"title": "Test Paper", "year": 2023, "doi": "10.1234/test"}]
        cache.set("AI in healthcare", results)

        loaded = CitationCache(cache_file)
        assert loaded.get("AI in healthcare") == results

    def test_miss_returns_none(self, tmp_path):
        cache = CitationCache(tmp_path / "miss.json")
        assert cache.get("nonexistent") is None

    def test_empty_results(self, tmp_path):
        cache = CitationCache(tmp_path / "empty.json")
        cache.set("no results query", [])
        loaded = CitationCache(tmp_path / "empty.json")
        assert loaded.get("no results query") == []

    def test_has(self, tmp_path):
        cache = CitationCache(tmp_path / "has.json")
        assert cache.has("test") is False
        cache.set("test", [])
        assert cache.has("test") is True

    def test_clear(self, tmp_path):
        cache = CitationCache(tmp_path / "clear.json")
        cache.set("test", [{"x": 1}])
        cache.clear()
        assert cache.get("test") is None

    def test_len(self, tmp_path):
        cache = CitationCache(tmp_path / "len.json")
        assert len(cache) == 0
        cache.set("a", [])
        cache.set("b", [])
        assert len(cache) == 2


# === query_router.py tests ===

class TestQueryRouter:
    def setup_method(self):
        self.router = QueryRouter()

    def test_academic_query(self):
        q, conf, patterns = self.router.classify_query(
            "peer-reviewed study on machine learning"
        )
        assert q == "academic"
        assert conf > 0.5
        assert len(patterns) > 0

    def test_industry_query(self):
        q, conf, patterns = self.router.classify_query(
            "McKinsey report on AI in healthcare"
        )
        assert q == "industry"
        assert conf > 0.5

    def test_mixed_query(self):
        q, conf, patterns = self.router.classify_query(
            "impact of climate change"
        )
        assert q == "mixed"

    def test_academic_chain(self):
        chain = self.router.get_api_chain("academic")
        assert chain[0] == "openalex"
        assert "semantic_scholar" in chain

    def test_industry_chain(self):
        chain = self.router.get_api_chain("industry")
        assert "openalex" in chain
        assert "crossref" in chain

    def test_classify_and_route(self):
        result = self.router.classify_and_route(
            "systematic review of deep learning"
        )
        assert result.query_type == "academic"
        assert len(result.api_chain) > 0
