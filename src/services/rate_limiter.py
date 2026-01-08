"""
Rate limiting service.

This module implements sliding window rate limiting for user and group
requests to prevent abuse in large group environments.

Per FR-012: System MUST support rate limiting (20 requests/user/minute,
50 requests/group/minute). System MUST implement high-quality concurrent
multi-threaded code architecture to efficiently handle high concurrency.
"""

import time
from collections import deque
from typing import Optional

from src.config import settings


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.

    Tracks request timestamps per user and per group to enforce
    rate limits. Uses in-memory storage with sliding window for
    accurate rate limiting.

    Per FR-012:
    - 20 requests per user per minute
    - 50 requests per group per minute
    """

    def __init__(
        self,
        user_limit: Optional[int] = None,
        group_limit: Optional[int] = None,
        window_seconds: int = 60,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            user_limit: Requests per user per window (default: from settings).
            group_limit: Requests per group per window (default: from settings).
            window_seconds: Time window in seconds (default: 60 for 1 minute).
        """
        # Rate limits from settings (per FR-012)
        self.user_limit = user_limit or settings.rate_limit_user_per_minute
        self.group_limit = group_limit or settings.rate_limit_group_per_minute
        self.window_seconds = window_seconds

        # In-memory storage: {identifier: deque of timestamps}
        # Per user: {hashed_user_id: deque}
        self._user_requests: dict[str, deque[float]] = {}

        # Per group: {group_id: deque}
        self._group_requests: dict[str, deque[float]] = {}

    def check_user_limit(self, user_id: str) -> tuple[bool, Optional[int]]:
        """
        Check if user has exceeded rate limit.

        Args:
            user_id: Hashed user ID.

        Returns:
            Tuple of (allowed: bool, remaining: Optional[int]).
            If allowed=False, remaining is None.
            If allowed=True, remaining is number of requests left in window.
        """
        now = time.time()

        # Get or create deque for this user
        if user_id not in self._user_requests:
            self._user_requests[user_id] = deque()

        # Clean old timestamps outside window
        user_deque = self._user_requests[user_id]
        self._clean_old_timestamps(user_deque, now)

        # Check limit
        if len(user_deque) >= self.user_limit:
            return False, None

        # Add current request timestamp
        user_deque.append(now)

        # Calculate remaining requests
        remaining = self.user_limit - len(user_deque)
        return True, remaining

    def check_group_limit(self, group_id: str) -> tuple[bool, Optional[int]]:
        """
        Check if group has exceeded rate limit.

        Args:
            group_id: QQ group ID.

        Returns:
            Tuple of (allowed: bool, remaining: Optional[int]).
            If allowed=False, remaining is None.
            If allowed=True, remaining is number of requests left in window.
        """
        now = time.time()

        # Get or create deque for this group
        if group_id not in self._group_requests:
            self._group_requests[group_id] = deque()

        # Clean old timestamps outside window
        group_deque = self._group_requests[group_id]
        self._clean_old_timestamps(group_deque, now)

        # Check limit
        if len(group_deque) >= self.group_limit:
            return False, None

        # Add current request timestamp
        group_deque.append(now)

        # Calculate remaining requests
        remaining = self.group_limit - len(group_deque)
        return True, remaining

    def check_rate_limit(
        self, user_id: str, group_id: str
    ) -> tuple[bool, Optional[str], Optional[int]]:
        """
        Check both user and group rate limits.

        Request is allowed only if BOTH user and group limits are not exceeded.

        Args:
            user_id: Hashed user ID.
            group_id: QQ group ID.

        Returns:
            Tuple of (allowed: bool, reason: Optional[str], remaining: Optional[int]).
            If allowed=False, reason explains why (e.g., "user limit exceeded").
            If allowed=True, remaining is minimum of user/group remaining requests.
        """
        # Check user limit
        user_allowed, user_remaining = self.check_user_limit(user_id)
        if not user_allowed:
            return False, "user limit exceeded", None

        # Check group limit
        group_allowed, group_remaining = self.check_group_limit(group_id)
        if not group_allowed:
            return False, "group limit exceeded", None

        # Both limits passed
        # Return minimum remaining (most restrictive)
        remaining = min(user_remaining or 0, group_remaining or 0)
        return True, None, remaining

    def _clean_old_timestamps(self, deque_obj: deque[float], now: float) -> None:
        """
        Remove timestamps outside the time window.

        Sliding window: remove all timestamps older than (now - window_seconds).

        Args:
            deque_obj: Deque of timestamps to clean.
            now: Current timestamp.
        """
        cutoff_time = now - self.window_seconds

        # Remove old timestamps from left (oldest first)
        while deque_obj and deque_obj[0] < cutoff_time:
            deque_obj.popleft()

    def reset_user(self, user_id: str) -> None:
        """
        Reset rate limit for a specific user.

        Useful for testing or manual rate limit clearing.

        Args:
            user_id: Hashed user ID.
        """
        if user_id in self._user_requests:
            del self._user_requests[user_id]

    def reset_group(self, group_id: str) -> None:
        """
        Reset rate limit for a specific group.

        Useful for testing or manual rate limit clearing.

        Args:
            group_id: QQ group ID.
        """
        if group_id in self._group_requests:
            del self._group_requests[group_id]


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(
    user_id: str, group_id: str
) -> tuple[bool, Optional[str], Optional[int]]:
    """
    Convenience function to check rate limits.

    Args:
        user_id: Hashed user ID.
        group_id: QQ group ID.

    Returns:
        Tuple of (allowed: bool, reason: Optional[str], remaining: Optional[int]).
    """
    return rate_limiter.check_rate_limit(user_id, group_id)
