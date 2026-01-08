"""
Step 2: Context retrieval.

This module handles retrieving user context from MongoDB:
- User information (preferred language, etc.)
- Impression (bot's memory of user)
- Recent conversation history (last 10 conversations)

Per FR-005: System MUST store and retrieve user conversation history
and preferences to enable contextual responses.
"""

from typing import Optional

from src.models.conversation import Conversation
from src.models.impression import Impression
from src.models.user import User


class UserContext:
    """
    User context data structure.

    Contains all relevant user information for generating contextual responses.
    """

    def __init__(
        self,
        user: Optional[User] = None,
        impression: Optional[Impression] = None,
        recent_conversations: Optional[list[Conversation]] = None,
    ) -> None:
        """
        Initialize user context.

        Args:
            user: User document (None if new user).
            impression: Impression document (None if new user).
            recent_conversations: List of recent conversations (last 10).
        """
        self.user = user
        self.impression = impression
        self.recent_conversations = recent_conversations or []

    @property
    def is_new_user(self) -> bool:
        """
        Check if this is a new user (no existing user record).

        Returns:
            True if new user, False if existing user.
        """
        return self.user is None

    @property
    def preferred_language(self) -> Optional[str]:
        """
        Get user's preferred language.

        Returns:
            Language code ("zh", "en", or None for auto-detect).
        """
        if self.user:
            return self.user.preferred_language
        return None

    @property
    def relationship_status(self) -> str:
        """
        Get relationship status with user.

        Returns:
            Relationship status ("new", "acquaintance", "friend", "regular").
        """
        if self.impression:
            return self.impression.relationship_status
        return "new"

    @property
    def interaction_count(self) -> int:
        """
        Get total interaction count.

        Returns:
            Number of interactions with this user.
        """
        if self.impression:
            return self.impression.interaction_count
        return 0


async def retrieve_context(hashed_user_id: str) -> UserContext:
    """
    Retrieve user context from MongoDB.

    This function queries:
    1. User document by hashed_user_id
    2. Impression document (1:1 with User)
    3. Recent conversations (last 10, ordered by timestamp descending)

    Per FR-005: Retrieve conversation history for contextual responses.

    Args:
        hashed_user_id: SHA-256 hashed QQ user ID.

    Returns:
        UserContext object containing user, impression, and recent conversations.
        If user doesn't exist, returns UserContext with None values.

    Example:
        >>> context = await retrieve_context("abc123...")
        >>> if context.is_new_user:
        ...     print("New user!")
        >>> print(f"Relationship: {context.relationship_status}")
        >>> print(f"Interactions: {context.interaction_count}")
    """
    # Query User by hashed_user_id
    # Beanie uses async queries, so we await the result
    # Use dictionary query syntax for Indexed fields
    user = await User.find_one({"hashed_user_id": hashed_user_id})

    # Query Impression (1:1 relationship with User)
    impression: Optional[Impression] = None
    if user:
        # If user exists, try to find their impression
        impression = await Impression.find_one({"user_id": hashed_user_id})

    # Query recent conversations (configurable limit)
    # Per FR-005: Retrieve conversation history for context with configurable limit
    # Per FR-005 Enhancement: Limit configurable via environment variable (default: 10)
    from src.config import settings
    limit = settings.conversation_history_limit
    
    # Order by timestamp descending (most recent first)
    # Use string notation for sort when using dictionary query
    recent_conversations = (
        await Conversation.find({"user_id": hashed_user_id})
        .sort("-timestamp")  # Descending order (most recent first)
        .limit(limit)  # Configurable limit (default: 10)
        .to_list()
    )

    # Create and return context object
    return UserContext(
        user=user,
        impression=impression,
        recent_conversations=recent_conversations,
    )
