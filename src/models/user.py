"""
User data model.

This module defines the User model for storing QQ user information
with privacy-compliant hashed user IDs.

Per FR-011: User identification MUST use hashed QQ user IDs (SHA-256)
to enable cross-group memory while protecting user privacy.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class User(Document):
    """
    User model representing a QQ user.

    Users are identified by hashed QQ user IDs (SHA-256) to ensure
    privacy compliance while enabling cross-group recognition.

    Attributes:
        hashed_user_id: SHA-256 hash of QQ user ID (unique, indexed).
        preferred_language: User's preferred language ("zh", "en", or None).
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
    """

    # Unique hashed user ID (64-character hex string from SHA-256)
    # Per FR-011: Use hashed QQ user ID as unique identifier
    # Unique index defined in Settings.indexes
    hashed_user_id: str

    # User's preferred language (None = auto-detect)
    # Per NFR-008: Allow users to explicitly specify preferred language
    preferred_language: Optional[str] = None

    # Timestamps
    # Use Field(default_factory) with lambda to avoid calling datetime.utcnow() at class definition time
    # This is required for Temporal workflow sandbox compatibility
    # Lambda wrapper prevents Pydantic from inspecting datetime.utcnow.__wrapped__
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    class Settings:
        """Beanie document settings."""

        # Collection name in MongoDB
        name = "users"

        # Indexes for fast queries
        indexes = [
            [("hashed_user_id", 1)],  # Unique index for fast lookups
        ]
        # Note: Unique constraint should be enforced at application level
        # or via MongoDB unique index creation script

    def update_timestamp(self) -> None:
        """
        Update the updated_at timestamp to current time.

        Call this method whenever the user record is modified.
        """
        self.updated_at = datetime.utcnow()

    def set_preferred_language(self, language: Optional[str]) -> None:
        """
        Set user's preferred language.

        Args:
            language: Language code ("zh", "en", or None for auto-detect).

        Raises:
            ValueError: If language code is invalid.
        """
        if language is not None and language not in ("zh", "en"):
            raise ValueError(f"Invalid language code: {language}. Must be 'zh', 'en', or None.")

        self.preferred_language = language
        self.update_timestamp()
