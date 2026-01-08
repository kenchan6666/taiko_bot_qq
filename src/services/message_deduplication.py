"""
Message deduplication service.

This module provides message deduplication functionality to skip duplicate
or highly similar messages from the same user within a time window.

Per FR-008 Enhancement: System MUST process messages in order but MUST skip
duplicate or highly similar messages (deduplication). Similarity threshold
and deduplication window MUST be configurable via environment variables.
"""

import time
from collections import defaultdict
from typing import Optional

from rapidfuzz import fuzz

from src.config import settings


class MessageDeduplicationService:
    """
    Message deduplication service.
    
    Tracks recent messages per user and skips duplicate or highly similar
    messages within a configurable time window.
    """

    def __init__(
        self,
        enabled: Optional[bool] = None,
        similarity_threshold: Optional[float] = None,
        window_seconds: Optional[int] = None,
    ) -> None:
        """
        Initialize message deduplication service.
        
        Args:
            enabled: Whether deduplication is enabled (defaults to config).
            similarity_threshold: Similarity threshold 0.0-1.0 (defaults to config).
            window_seconds: Deduplication window in seconds (defaults to config).
        """
        self.enabled = (
            enabled
            if enabled is not None
            else settings.message_deduplication_enabled
        )
        self.similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else settings.message_deduplication_similarity_threshold
        )
        self.window_seconds = (
            window_seconds
            if window_seconds is not None
            else settings.message_deduplication_window_seconds
        )
        
        # Track recent messages per user: {hashed_user_id: [(timestamp, message), ...]}
        self._recent_messages: dict[str, list[tuple[float, str]]] = defaultdict(list)
        
        # Cleanup old entries periodically
        self._last_cleanup = time.time()
        self._cleanup_interval = 60.0  # Cleanup every 60 seconds

    def _cleanup_old_entries(self) -> None:
        """Remove old message entries outside the deduplication window."""
        current_time = time.time()
        
        # Only cleanup periodically to avoid overhead
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = current_time
        cutoff_time = current_time - self.window_seconds
        
        # Remove old entries for all users
        for user_id in list(self._recent_messages.keys()):
            self._recent_messages[user_id] = [
                (ts, msg)
                for ts, msg in self._recent_messages[user_id]
                if ts > cutoff_time
            ]
            
            # Remove empty user entries
            if not self._recent_messages[user_id]:
                del self._recent_messages[user_id]

    def is_duplicate(
        self,
        hashed_user_id: str,
        message: str,
    ) -> bool:
        """
        Check if message is duplicate or highly similar to recent messages.
        
        Per FR-008 Enhancement: Skip duplicate or highly similar messages
        within the deduplication window.
        
        Args:
            hashed_user_id: Hashed user ID.
            message: Message content to check.
            
        Returns:
            True if message is duplicate/similar, False otherwise.
        """
        if not self.enabled:
            return False
        
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        # Get recent messages for this user
        recent = self._recent_messages[hashed_user_id]
        
        # Remove messages outside the window
        recent = [(ts, msg) for ts, msg in recent if ts > cutoff_time]
        self._recent_messages[hashed_user_id] = recent
        
        # Check similarity with recent messages
        for _, recent_msg in recent:
            # Use rapidfuzz for similarity comparison
            similarity = fuzz.ratio(message, recent_msg) / 100.0  # Convert to 0.0-1.0
            
            if similarity >= self.similarity_threshold:
                # Message is too similar to a recent message - skip it
                return True
        
        # Message is not duplicate - add it to recent messages
        recent.append((current_time, message))
        self._recent_messages[hashed_user_id] = recent
        
        return False


# Global deduplication service instance
_deduplication_service: Optional[MessageDeduplicationService] = None


def get_deduplication_service() -> MessageDeduplicationService:
    """
    Get global message deduplication service instance.
    
    Returns:
        Global MessageDeduplicationService instance.
    """
    global _deduplication_service
    
    if _deduplication_service is None:
        _deduplication_service = MessageDeduplicationService()
    
    return _deduplication_service
