"""Tests for cppload Python SDK metrics and rate limiting."""

import threading
import time

import pytest

from volley import MetricsCollector, TokenBucket


class TestMetricsCollector:
    def test_record_and_snapshot(self) -> None:
        m = MetricsCollector()
        m.record_request(200, 1000)
        m.record_request(200, 2000)
        m.record_request(500, 3000)

        s = m.snapshot()
        assert s["total_requests"] == 3
        assert s["successful_requests"] == 2
        assert s["failed_requests"] == 1
        assert s["error_rate"] == pytest.approx(33.33, rel=0.1)
        assert s["mean_latency_us"] == pytest.approx(2000)
        assert s["min_latency_us"] == 1000
        assert s["max_latency_us"] == 3000

    def test_percentiles(self) -> None:
        m = MetricsCollector()
        for i in range(1, 101):
            m.record_request(200, i * 10)
        assert m.p95_latency_us == 960
        assert m.p99_latency_us == 1000

    def test_empty_snapshot(self) -> None:
        m = MetricsCollector()
        s = m.snapshot()
        assert s["total_requests"] == 0
        assert s["p95_latency_us"] == 0
        assert s["error_rate"] == 0.0

    def test_reset(self) -> None:
        m = MetricsCollector()
        m.record_request(200, 100)
        m.reset()
        assert m.snapshot()["total_requests"] == 0

    def test_latency_cap(self) -> None:
        m = MetricsCollector()
        for _ in range(120_000):
            m.record_request(200, 5)
        assert len(m._latencies) <= 100_000

    def test_thread_safety(self) -> None:
        m = MetricsCollector()

        def record_requests() -> None:
            for _ in range(2000):
                m.record_request(200, 1)

        threads: list[threading.Thread] = []
        for _ in range(8):
            t = threading.Thread(target=record_requests)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        assert m.snapshot()["total_requests"] == 16_000


class TestTokenBucket:
    def test_initial_tokens(self) -> None:
        b = TokenBucket(100)
        b.consume()  # burst == rate

    def test_rate_limit_slow(self) -> None:
        b = TokenBucket(1)
        start = time.time()
        b.consume()
        b.consume()
        elapsed = time.time() - start
        assert elapsed >= 0.5

    def test_negative_rate_rejected(self) -> None:
        with pytest.raises(ValueError):
            TokenBucket(-1)

    def test_try_consume_honors_burst(self) -> None:
        b = TokenBucket(2)
        assert b.try_consume()
        assert b.try_consume()
        assert not b.try_consume()
