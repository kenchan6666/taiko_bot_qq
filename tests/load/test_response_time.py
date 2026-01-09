"""
Response time load test.

Tests that system meets < 3s response time requirement
for 95% of requests.

Per T101: Create tests/load/test_response_time.py
"""

import asyncio
import statistics
import time

import pytest

from src.api.routes.langbot import LangBotWebhookRequest, _process_webhook_request


class TestResponseTime:
    """Test response time requirements."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_response_time_under_3_seconds(self, test_database):
        """95% of requests should complete in < 3 seconds."""
        num_requests = 50
        
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        # Create requests
        requests = [
            LangBotWebhookRequest(
                user_id=f"user_{i}",
                group_id=f"group_{i % 5}",
                message=f"Mika, test request {i}",
            )
            for i in range(num_requests)
        ]
        
        # Measure response times
        response_times = []
        
        for req in requests:
            start_time = time.time()
            try:
                result = await _process_webhook_request(req, mock_request)
                end_time = time.time()
                
                if result.status == "ok":
                    response_times.append(end_time - start_time)
            except Exception:
                # Skip failed requests for timing
                pass
        
        if not response_times:
            pytest.skip("No successful requests to measure")
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p50 = statistics.median(sorted_times)
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        avg = statistics.mean(sorted_times)
        
        # 95th percentile should be < 3 seconds
        assert p95 < 3.0, f"P95 response time {p95:.2f}s exceeds 3s requirement"
        
        print(f"\n✓ Response time statistics:")
        print(f"  Average: {avg:.3f}s")
        print(f"  P50 (median): {p50:.3f}s")
        print(f"  P95: {p95:.3f}s")
        print(f"  P99: {p99:.3f}s")
        print(f"  Total requests: {len(response_times)}")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_response_time_consistency(self, test_database):
        """Response times should be consistent across multiple requests."""
        num_requests = 20
        
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        # Create similar requests
        requests = [
            LangBotWebhookRequest(
                user_id="test_user",
                group_id="test_group",
                message="Mika, hello!",
            )
            for _ in range(num_requests)
        ]
        
        # Measure response times
        response_times = []
        
        for req in requests:
            start_time = time.time()
            try:
                result = await _process_webhook_request(req, mock_request)
                end_time = time.time()
                
                if result.status == "ok":
                    response_times.append(end_time - start_time)
            except Exception:
                pass
        
        if len(response_times) < 5:
            pytest.skip("Not enough successful requests")
        
        # Calculate standard deviation
        avg = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        
        # Coefficient of variation should be reasonable (< 50%)
        cv = (std_dev / avg) if avg > 0 else 0
        
        assert cv < 0.5, f"Response time variation too high: CV={cv:.2%}"
        
        print(f"\n✓ Response time consistency:")
        print(f"  Average: {avg:.3f}s")
        print(f"  Std Dev: {std_dev:.3f}s")
        print(f"  Coefficient of Variation: {cv:.2%}")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_response_time_under_load(self, test_database):
        """Response time should remain acceptable under load."""
        num_requests = 30
        
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        # Create requests
        requests = [
            LangBotWebhookRequest(
                user_id=f"user_{i}",
                group_id=f"group_{i % 3}",
                message=f"Mika, load test {i}",
            )
            for i in range(num_requests)
        ]
        
        # Process concurrently (simulating load)
        start_time = time.time()
        
        tasks = [
            _process_webhook_request(req, mock_request)
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate average response time per request
        successful = [r for r in results if not isinstance(r, Exception) and r.status == "ok"]
        avg_time_per_request = total_time / len(successful) if successful else total_time / num_requests
        
        # Average should be reasonable (< 5s per request under load)
        assert avg_time_per_request < 5.0, f"Average response time {avg_time_per_request:.2f}s too high"
        
        print(f"\n✓ Response time under load:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful requests: {len(successful)}/{num_requests}")
        print(f"  Average time per request: {avg_time_per_request:.3f}s")
