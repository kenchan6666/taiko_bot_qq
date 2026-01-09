"""
Rate limiter tests.

Tests rate limit enforcement and sliding window accuracy.

Per T096: Create tests/unit/test_rate_limiter.py
"""

import time

import pytest

from src.services.rate_limiter import RateLimiter


class TestUserRateLimit:
    """Test cases for user rate limiting."""

    def test_user_limit_enforcement(self):
        """User should be limited to configured requests per minute."""
        limiter = RateLimiter(user_limit=5, group_limit=10, window_seconds=60)
        
        user_id = "test_user_123"
        
        # Make 5 requests (should all pass)
        for i in range(5):
            allowed, remaining = limiter.check_user_limit(user_id)
            assert allowed is True
            assert remaining == 5 - i - 1
        
        # 6th request should be blocked
        allowed, remaining = limiter.check_user_limit(user_id)
        assert allowed is False
        assert remaining is None

    def test_user_limit_reset_after_window(self):
        """User limit should reset after time window."""
        limiter = RateLimiter(user_limit=2, group_limit=10, window_seconds=1)  # 1 second window
        
        user_id = "test_user_123"
        
        # Make 2 requests (should pass)
        allowed1, _ = limiter.check_user_limit(user_id)
        assert allowed1 is True
        
        allowed2, _ = limiter.check_user_limit(user_id)
        assert allowed2 is True
        
        # 3rd request should be blocked
        allowed3, _ = limiter.check_user_limit(user_id)
        assert allowed3 is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be able to make requests again
        allowed4, _ = limiter.check_user_limit(user_id)
        assert allowed4 is True

    def test_sliding_window_accuracy(self):
        """Sliding window should accurately track requests."""
        limiter = RateLimiter(user_limit=3, group_limit=10, window_seconds=2)
        
        user_id = "test_user_123"
        
        # Make 3 requests quickly
        for i in range(3):
            limiter.check_user_limit(user_id)
        
        # Wait 1 second (half of window)
        time.sleep(1.0)
        
        # Should still be blocked (window hasn't expired)
        allowed, _ = limiter.check_user_limit(user_id)
        assert allowed is False
        
        # Wait another 1.1 seconds (total > 2 seconds)
        time.sleep(1.1)
        
        # Should be able to make 1 request (2 old requests expired, 1 still in window)
        allowed, remaining = limiter.check_user_limit(user_id)
        assert allowed is True
        assert remaining == 2  # 3 limit - 1 current = 2 remaining

    def test_multiple_users_independent(self):
        """Multiple users should have independent rate limits."""
        limiter = RateLimiter(user_limit=2, group_limit=10, window_seconds=60)
        
        user1 = "user_1"
        user2 = "user_2"
        
        # User 1 makes 2 requests
        allowed1, _ = limiter.check_user_limit(user1)
        assert allowed1 is True
        allowed2, _ = limiter.check_user_limit(user1)
        assert allowed2 is True
        
        # User 1 should be blocked
        allowed3, _ = limiter.check_user_limit(user1)
        assert allowed3 is False
        
        # User 2 should still be able to make requests
        allowed4, _ = limiter.check_user_limit(user2)
        assert allowed4 is True


class TestGroupRateLimit:
    """Test cases for group rate limiting."""

    def test_group_limit_enforcement(self):
        """Group should be limited to configured requests per minute."""
        limiter = RateLimiter(user_limit=10, group_limit=5, window_seconds=60)
        
        group_id = "test_group_123"
        
        # Make 5 requests (should all pass)
        for i in range(5):
            allowed, remaining = limiter.check_group_limit(group_id)
            assert allowed is True
            assert remaining == 5 - i - 1
        
        # 6th request should be blocked
        allowed, remaining = limiter.check_group_limit(group_id)
        assert allowed is False
        assert remaining is None

    def test_group_limit_reset_after_window(self):
        """Group limit should reset after time window."""
        limiter = RateLimiter(user_limit=10, group_limit=2, window_seconds=1)
        
        group_id = "test_group_123"
        
        # Make 2 requests
        allowed1, _ = limiter.check_group_limit(group_id)
        assert allowed1 is True
        allowed2, _ = limiter.check_group_limit(group_id)
        assert allowed2 is True
        
        # 3rd request should be blocked
        allowed3, _ = limiter.check_group_limit(group_id)
        assert allowed3 is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be able to make requests again
        allowed4, _ = limiter.check_group_limit(group_id)
        assert allowed4 is True

    def test_multiple_groups_independent(self):
        """Multiple groups should have independent rate limits."""
        limiter = RateLimiter(user_limit=10, group_limit=2, window_seconds=60)
        
        group1 = "group_1"
        group2 = "group_2"
        
        # Group 1 makes 2 requests
        allowed1, _ = limiter.check_group_limit(group1)
        assert allowed1 is True
        allowed2, _ = limiter.check_group_limit(group1)
        assert allowed2 is True
        
        # Group 1 should be blocked
        allowed3, _ = limiter.check_group_limit(group1)
        assert allowed3 is False
        
        # Group 2 should still be able to make requests
        allowed4, _ = limiter.check_group_limit(group2)
        assert allowed4 is True


class TestCombinedRateLimit:
    """Test cases for combined user and group rate limiting."""

    def test_both_limits_must_pass(self):
        """Both user and group limits must pass for request to be allowed."""
        limiter = RateLimiter(user_limit=2, group_limit=2, window_seconds=60)
        
        user_id = "test_user"
        group_id = "test_group"
        
        # Make 2 requests (both user and group limits)
        allowed1, reason1, remaining1 = limiter.check_rate_limit(user_id, group_id)
        assert allowed1 is True
        assert reason1 is None
        
        allowed2, reason2, remaining2 = limiter.check_rate_limit(user_id, group_id)
        assert allowed2 is True
        assert reason2 is None
        
        # 3rd request should be blocked (both limits exceeded)
        allowed3, reason3, remaining3 = limiter.check_rate_limit(user_id, group_id)
        assert allowed3 is False
        assert reason3 in ["user limit exceeded", "group limit exceeded"]

    def test_user_limit_exceeded_first(self):
        """If user limit exceeded, should return user limit reason."""
        limiter = RateLimiter(user_limit=1, group_limit=10, window_seconds=60)
        
        user_id = "test_user"
        group_id = "test_group"
        
        # First request should pass
        allowed1, reason1, _ = limiter.check_rate_limit(user_id, group_id)
        assert allowed1 is True
        
        # Second request should fail with user limit reason
        allowed2, reason2, _ = limiter.check_rate_limit(user_id, group_id)
        assert allowed2 is False
        assert reason2 == "user limit exceeded"

    def test_group_limit_exceeded_first(self):
        """If group limit exceeded, should return group limit reason."""
        limiter = RateLimiter(user_limit=10, group_limit=1, window_seconds=60)
        
        user_id = "test_user"
        group_id = "test_group"
        
        # First request should pass
        allowed1, reason1, _ = limiter.check_rate_limit(user_id, group_id)
        assert allowed1 is True
        
        # Second request should fail with group limit reason
        allowed2, reason2, _ = limiter.check_rate_limit(user_id, group_id)
        assert allowed2 is False
        assert reason2 == "group limit exceeded"

    def test_remaining_requests_calculation(self):
        """Remaining requests should be minimum of user and group remaining."""
        limiter = RateLimiter(user_limit=5, group_limit=10, window_seconds=60)
        
        user_id = "test_user"
        group_id = "test_group"
        
        # Make 3 requests
        for i in range(3):
            allowed, reason, remaining = limiter.check_rate_limit(user_id, group_id)
            assert allowed is True
            # Remaining should be min(user_remaining, group_remaining)
            # After 3 requests: user has 2 remaining, group has 7 remaining
            # So remaining should be 2 (minimum)
            if i == 2:  # After 3rd request
                assert remaining == 2  # min(5-3, 10-3) = min(2, 7) = 2


class TestSlidingWindowAccuracy:
    """Test sliding window algorithm accuracy."""

    def test_old_timestamps_removed(self):
        """Old timestamps outside window should be removed."""
        limiter = RateLimiter(user_limit=10, group_limit=10, window_seconds=2)
        
        user_id = "test_user"
        
        # Make request at time 0
        limiter.check_user_limit(user_id)
        
        # Simulate time passing (manipulate timestamps)
        # Wait 2.1 seconds
        time.sleep(2.1)
        
        # Make another request
        # Old timestamp should be cleaned up
        allowed, remaining = limiter.check_user_limit(user_id)
        assert allowed is True
        # Should have full limit available (old request expired)
        assert remaining == 9  # 10 - 1 current = 9

    def test_gradual_expiration(self):
        """Requests should expire gradually as window slides."""
        limiter = RateLimiter(user_limit=5, group_limit=10, window_seconds=5)
        
        user_id = "test_user"
        
        # Make 5 requests at time 0
        for i in range(5):
            limiter.check_user_limit(user_id)
        
        # Wait 2 seconds (some requests still in window)
        time.sleep(2.0)
        
        # Should still be blocked
        allowed, _ = limiter.check_user_limit(user_id)
        assert allowed is False
        
        # Wait 3 more seconds (total 5 seconds, all requests expired)
        time.sleep(3.1)
        
        # Should be able to make requests again
        allowed, remaining = limiter.check_user_limit(user_id)
        assert allowed is True
        assert remaining == 4  # 5 - 1 current = 4


class TestResetFunctions:
    """Test reset functions for rate limiter."""

    def test_reset_user(self):
        """Reset user should clear user's request history."""
        limiter = RateLimiter(user_limit=2, group_limit=10, window_seconds=60)
        
        user_id = "test_user"
        
        # Make 2 requests (exhaust limit)
        limiter.check_user_limit(user_id)
        limiter.check_user_limit(user_id)
        
        # Should be blocked
        allowed, _ = limiter.check_user_limit(user_id)
        assert allowed is False
        
        # Reset user
        limiter.reset_user(user_id)
        
        # Should be able to make requests again
        allowed, remaining = limiter.check_user_limit(user_id)
        assert allowed is True
        assert remaining == 1  # 2 - 1 current = 1

    def test_reset_group(self):
        """Reset group should clear group's request history."""
        limiter = RateLimiter(user_limit=10, group_limit=2, window_seconds=60)
        
        group_id = "test_group"
        
        # Make 2 requests (exhaust limit)
        limiter.check_group_limit(group_id)
        limiter.check_group_limit(group_id)
        
        # Should be blocked
        allowed, _ = limiter.check_group_limit(group_id)
        assert allowed is False
        
        # Reset group
        limiter.reset_group(group_id)
        
        # Should be able to make requests again
        allowed, remaining = limiter.check_group_limit(group_id)
        assert allowed is True
        assert remaining == 1  # 2 - 1 current = 1
