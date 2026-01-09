"""
Multi-group integration tests.

Tests concurrent requests from multiple groups to ensure
system handles multi-group scenarios correctly.

Per T097: Create tests/integration/test_multi_group.py
"""

import asyncio

import pytest

from src.api.routes.langbot import LangBotWebhookRequest, _process_webhook_request
from src.utils.hashing import hash_user_id


class TestMultiGroupConcurrency:
    """Test concurrent requests from multiple groups."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_groups(self, test_database):
        """Multiple groups should be able to send requests concurrently."""
        # Create requests from different groups
        requests = [
            LangBotWebhookRequest(
                user_id="user_1",
                group_id="group_1",
                message="Mika, hello from group 1!",
            ),
            LangBotWebhookRequest(
                user_id="user_2",
                group_id="group_2",
                message="Mika, hello from group 2!",
            ),
            LangBotWebhookRequest(
                user_id="user_3",
                group_id="group_3",
                message="Mika, hello from group 3!",
            ),
        ]
        
        # Process all requests concurrently
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        tasks = [
            _process_webhook_request(req, mock_request)
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert result.status == "ok"
            assert result.response is not None

    @pytest.mark.asyncio
    async def test_same_user_different_groups(self, test_database):
        """Same user in different groups should be recognized."""
        user_id = "same_user_123"
        hashed_id = hash_user_id(user_id)
        
        # Create requests from same user in different groups
        requests = [
            LangBotWebhookRequest(
                user_id=user_id,
                group_id="group_1",
                message="Mika, I'm in group 1",
            ),
            LangBotWebhookRequest(
                user_id=user_id,
                group_id="group_2",
                message="Mika, I'm in group 2",
            ),
        ]
        
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        # Process requests
        for req in requests:
            result = await _process_webhook_request(req, mock_request)
            assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_group_isolation(self, test_database):
        """Groups should be isolated (rate limits, etc.)."""
        # Test that rate limits are per-group
        from src.services.rate_limiter import RateLimiter
        
        limiter = RateLimiter(user_limit=10, group_limit=2, window_seconds=60)
        
        user_id = "test_user"
        group1 = "group_1"
        group2 = "group_2"
        
        # Exhaust group 1 limit
        limiter.check_rate_limit(user_id, group1)
        limiter.check_rate_limit(user_id, group1)
        
        # Group 1 should be blocked
        allowed1, _, _ = limiter.check_rate_limit(user_id, group1)
        assert allowed1 is False
        
        # Group 2 should still work
        allowed2, _, _ = limiter.check_rate_limit(user_id, group2)
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_high_concurrency_multiple_groups(self, test_database):
        """System should handle high concurrency from multiple groups."""
        num_groups = 10
        requests_per_group = 5
        
        from fastapi import Request
        from unittest.mock import MagicMock
        
        mock_request = MagicMock(spec=Request)
        
        # Create requests from multiple groups
        all_requests = []
        for group_num in range(num_groups):
            for req_num in range(requests_per_group):
                all_requests.append(
                    LangBotWebhookRequest(
                        user_id=f"user_{group_num}_{req_num}",
                        group_id=f"group_{group_num}",
                        message=f"Mika, request {req_num} from group {group_num}",
                    )
                )
        
        # Process all requests concurrently
        tasks = [
            _process_webhook_request(req, mock_request)
            for req in all_requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Most requests should succeed (some may fail due to rate limits)
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status == "ok")
        assert success_count > len(all_requests) * 0.8  # At least 80% success rate
