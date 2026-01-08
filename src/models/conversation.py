"""
Conversation data model.

This module defines the Conversation model for storing individual
message interactions with automatic 90-day expiration.

Per FR-005: Conversation history MUST be automatically deleted after 90 days
to balance memory functionality with privacy compliance and storage cost control.
"""

from datetime import datetime, timedelta
from typing import Optional

from beanie import Document
from pydantic import Field


class Conversation(Document):
    """
    Conversation model representing a single message interaction.

    Conversations store user messages and bot responses for context retrieval.
    They are automatically deleted after 90 days via cleanup job.

    Attributes:
        user_id: Reference to User.hashed_user_id (indexed).
        group_id: QQ group ID where message was sent.
        message: User's message content.
        response: Bot's response content.
        images: Optional list of base64-encoded images.
        timestamp: Message timestamp.
        expires_at: Auto-deletion date (90 days from timestamp, indexed).
    """

    # Reference to User.hashed_user_id
    # Indexed for fast user history retrieval (index defined in Settings.indexes)
    user_id: str

    # QQ group ID where message was sent
    group_id: str

    # Message content
    message: str
    response: str

    # Optional images (base64-encoded)
    # Per FR-006: Support multi-modal image processing
    images: Optional[list[str]] = None

    # Timestamps
    # Use Field(default_factory) with lambda to avoid calling datetime.utcnow() at class definition time
    # This is required for Temporal workflow sandbox compatibility
    # Lambda wrapper prevents Pydantic from inspecting datetime.utcnow.__wrapped__
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())

    # Auto-deletion date (90 days from timestamp)
    # Per FR-005: Conversations auto-deleted after 90 days
    # Indexed for efficient cleanup job queries (index defined in Settings.indexes)
    expires_at: datetime

    class Settings:
        """Beanie document settings."""

        # Collection name in MongoDB
        name = "conversations"

        # Indexes for fast queries
        indexes = [
            [("user_id", 1)],  # Index for user history retrieval
            [("expires_at", 1)],  # Index for cleanup job efficiency
            [("user_id", 1), ("timestamp", -1)],  # Compound index for chronological queries
        ]

    def __init__(self, **data):
        """
        Initialize Conversation with automatic expires_at calculation.

        If expires_at is not provided, it is automatically set to
        90 days after timestamp (per FR-005).
        """
        super().__init__(**data)

        # Auto-set expires_at if not provided
        if not self.expires_at:
            # Per FR-005: 90-day retention period
            self.expires_at = self.timestamp + timedelta(days=90)

    @classmethod
    def create(
        cls,
        user_id: str,
        group_id: str,
        message: str,
        response: str,
        images: Optional[list[str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "Conversation":
        """
        Create a new Conversation with automatic expiration.

        Args:
            user_id: Hashed user ID.
            group_id: QQ group ID.
            message: User's message.
            response: Bot's response.
            images: Optional list of base64-encoded images.
            timestamp: Message timestamp (default: now).

        Returns:
            New Conversation instance.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Calculate expiration date (90 days from timestamp)
        expires_at = timestamp + timedelta(days=90)

        return cls(
            user_id=user_id,
            group_id=group_id,
            message=message,
            response=response,
            images=images,
            timestamp=timestamp,
            expires_at=expires_at,
        )

    def is_expired(self) -> bool:
        """
        Check if conversation has expired (past expires_at date).

        Returns:
            True if expired, False otherwise.
        """
        return datetime.utcnow() > self.expires_at
