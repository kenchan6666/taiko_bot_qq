"""
Impression data model.

This module defines the Impression model for storing the bot's
"memory" or understanding of users for personalized responses.

Per FR-010: System MUST inform users when the bot learns or
remembers information about them.
"""

from datetime import datetime
from typing import Any, Optional

from beanie import Document
from pydantic import Field


class Impression(Document):
    """
    Impression model representing the bot's memory of a user.

    Stores learned preferences, relationship status, and interaction
    patterns for personalized responses. Has 1:1 relationship with User.

    Attributes:
        user_id: Reference to User.hashed_user_id (unique, indexed).
        preferences: Learned preferences dict (e.g., favorite BPM range).
        relationship_status: Relationship level (new, acquaintance, friend, regular).
        interaction_count: Total number of interactions.
        last_interaction: Timestamp of last interaction.
        learned_facts: List of facts learned about user.
    """

    # Reference to User.hashed_user_id (1:1 relationship)
    # Unique index enforces one impression per user (index defined in Settings.indexes)
    user_id: str

    # Learned preferences (e.g., {"favorite_bpm_range": "high", "favorite_difficulty": "extreme"})
    preferences: dict[str, Any] = {}
    
    # Pending preferences awaiting user confirmation
    # Per FR-010 Enhancement: Retain unconfirmed preferences in pending state
    # Format: {"preference_key": {"value": ..., "extracted_at": datetime, "context": str}}
    pending_preferences: dict[str, dict[str, Any]] = {}

    # Relationship status based on interaction count
    # State transitions:
    # - 0-2: "new"
    # - 3-10: "acquaintance"
    # - 11-50: "friend"
    # - 51+: "regular"
    relationship_status: str = "new"

    # Total number of interactions with this user
    interaction_count: int = 0

    # Timestamp of last interaction
    # Use Field(default_factory) with lambda to avoid calling datetime.utcnow() at class definition time
    # This is required for Temporal workflow sandbox compatibility
    # Lambda wrapper prevents Pydantic from inspecting datetime.utcnow.__wrapped__
    last_interaction: datetime = Field(default_factory=lambda: datetime.utcnow())

    # List of facts learned about user
    # Per FR-010: Bot informs users when it learns new facts
    learned_facts: list[str] = []

    class Settings:
        """Beanie document settings."""

        # Collection name in MongoDB
        name = "impressions"

        # Indexes for fast queries
        indexes = [
            [("user_id", 1)],  # Unique index (enforces 1:1 with User)
        ]
        # Note: Unique constraint should be enforced at application level
        # or via MongoDB unique index creation script

    def update_relationship_status(self) -> None:
        """
        Update relationship status based on interaction count.

        Automatically updates relationship_status based on the number
        of interactions:
        - 0-2: "new"
        - 3-10: "acquaintance"
        - 11-50: "friend"
        - 51+: "regular"
        """
        if self.interaction_count < 3:
            self.relationship_status = "new"
        elif self.interaction_count < 11:
            self.relationship_status = "acquaintance"
        elif self.interaction_count < 51:
            self.relationship_status = "friend"
        else:
            self.relationship_status = "regular"

    def increment_interaction(self) -> None:
        """
        Increment interaction count and update timestamps.

        Also updates relationship status automatically.
        """
        self.interaction_count += 1
        self.last_interaction = datetime.utcnow()
        self.update_relationship_status()

    def add_learned_fact(self, fact: str) -> None:
        """
        Add a learned fact about the user.

        Per FR-010: Bot informs users when it learns new information.

        Args:
            fact: Fact string to add (e.g., "likes high-BPM songs").
        """
        if fact and fact not in self.learned_facts:
            self.learned_facts.append(fact)

    def update_preference(self, key: str, value: Any) -> None:
        """
        Update a user preference.

        Args:
            key: Preference key (e.g., "favorite_bpm_range").
            value: Preference value.
        """
        self.preferences[key] = value
        # Remove from pending if it was pending
        if key in self.pending_preferences:
            del self.pending_preferences[key]

    def add_pending_preference(
        self,
        key: str,
        value: Any,
        context: str,
    ) -> None:
        """
        Add a pending preference awaiting user confirmation.
        
        Per FR-010 Enhancement: Retain unconfirmed preferences in pending state.
        
        Args:
            key: Preference key (e.g., "favorite_bpm_range").
            value: Preference value.
            context: Context where preference was extracted (for natural re-confirmation).
        """
        from datetime import datetime
        self.pending_preferences[key] = {
            "value": value,
            "extracted_at": datetime.utcnow(),
            "context": context,
        }

    def get_pending_preference(self, key: str) -> Optional[dict[str, Any]]:
        """
        Get a pending preference by key.
        
        Args:
            key: Preference key.
            
        Returns:
            Pending preference dict or None if not found.
        """
        return self.pending_preferences.get(key)

    def confirm_pending_preference(self, key: str) -> bool:
        """
        Confirm and move a pending preference to confirmed preferences.
        
        Args:
            key: Preference key to confirm.
            
        Returns:
            True if preference was confirmed, False if not found in pending.
        """
        if key not in self.pending_preferences:
            return False
        
        pending = self.pending_preferences[key]
        self.preferences[key] = pending["value"]
        del self.pending_preferences[key]
        return True
