"""
Concurrent requests load test.

Tests system's ability to handle 100 concurrent requests
without degradation.

Per T100: Create tests/load/test_concurrent_requests.py
"""

import asyncio
import time

import pytest

from src.api.routes.langbot import LangBotWebhookRequest, _process_webhook_request


class TestConcurrentRequests:
    """Test concurrent request handling."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_100_concurrent_requests(self, test_database):
        """System should handle 100 concurrent requests."""
        num_requests = 100
        
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        # Create 100 requests
        requests = [
            LangBotWebhookRequest(
                user_id=f"user_{i}",
                group_id=f"group_{i % 10}",  # 10 groups
                message=f"Mika, concurrent request {i}",
            )
            for i in range(num_requests)
        ]
        
        # Process all requests concurrently
        start_time = time.time()
        
        tasks = [
            _process_webhook_request(req, mock_request)
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Calculate success rate
        success_count = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status == "ok"
        )
        success_rate = success_count / num_requests
        
        # At least 80% should succeed (some may fail due to rate limits)
        assert success_rate >= 0.8, f"Success rate {success_rate:.2%} below 80%"
        
        # Should complete in reasonable time (< 60 seconds for 100 requests)
        assert elapsed < 60, f"Took {elapsed:.2f}s, expected < 60s"
        
        print(f"\n✓ Processed {num_requests} concurrent requests")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Elapsed time: {elapsed:.2f}s")
        print(f"  Average time per request: {elapsed/num_requests:.3f}s")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_requests_different_groups(self, test_database):
        """System should handle concurrent requests from different groups."""
        num_groups = 20
        requests_per_group = 5
        total_requests = num_groups * requests_per_group
        
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        # Create requests from different groups
        requests = [
            LangBotWebhookRequest(
                user_id=f"user_{group}_{req}",
                group_id=f"group_{group}",
                message=f"Mika, request {req} from group {group}",
            )
            for group in range(num_groups)
            for req in range(requests_per_group)
        ]
        
        # Process concurrently
        start_time = time.time()
        
        tasks = [
            _process_webhook_request(req, mock_request)
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Calculate success rate
        success_count = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status == "ok"
        )
        success_rate = success_count / total_requests
        
        # Should handle multi-group concurrency
        assert success_rate >= 0.7, f"Success rate {success_rate:.2%} below 70%"
        
        print(f"\n✓ Processed {total_requests} requests from {num_groups} groups")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Elapsed time: {elapsed:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_requests_same_group(self, test_database):
        """System should handle concurrent requests from same group."""
        num_requests = 50
        group_id = "test_group_123"
        
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        # Create requests from same group
        requests = [
            LangBotWebhookRequest(
                user_id=f"user_{i}",
                group_id=group_id,
                message=f"Mika, request {i}",
            )
            for i in range(num_requests)
        ]
        
        # Process concurrently
        start_time = time.time()
        
        tasks = [
            _process_webhook_request(req, mock_request)
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Some may fail due to group rate limits (50/group/minute)
        success_count = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status == "ok"
        )
        
        # Should handle at least some requests (rate limits may block some)
        assert success_count > 0, "No requests succeeded"
        
        print(f"\n✓ Processed {num_requests} requests from same group")
        print(f"  Successful: {success_count}/{num_requests}")
        print(f"  Elapsed time: {elapsed:.2f}s")
