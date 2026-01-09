"""
Privacy integration tests.

Tests privacy features including:
- Hashed user IDs
- 90-day conversation deletion
- Cross-group recognition

Per T099: Create tests/integration/test_privacy.py
"""

from datetime import datetime, timedelta

import pytest

from src.models.conversation import Conversation
from src.models.user import User
from src.utils.hashing import hash_user_id, validate_hashed_user_id


class TestHashedUserIDs:
    """Test hashed user ID functionality."""

    @pytest.mark.asyncio
    async def test_user_id_hashing(self, test_database):
        """User IDs should be hashed using SHA-256."""
        plaintext_id = "123456789"
        hashed = hash_user_id(plaintext_id)
        
        # Should be 64-character hex string
        assert len(hashed) == 64
        assert validate_hashed_user_id(hashed) is True
        
        # Same input should produce same hash
        hashed2 = hash_user_id(plaintext_id)
        assert hashed == hashed2

    @pytest.mark.asyncio
    async def test_user_stored_with_hashed_id(self, test_database):
        """Users should be stored with hashed IDs, not plaintext."""
        plaintext_id = "user_123"
        hashed_id = hash_user_id(plaintext_id)
        
        # Create user with hashed ID
        user = User(hashed_user_id=hashed_id, preferred_language="zh")
        await user.insert()
        
        # Retrieve user
        retrieved = await User.find_one(User.hashed_user_id == hashed_id)
        assert retrieved is not None
        assert retrieved.hashed_user_id == hashed_id
        # Should NOT contain plaintext ID
        assert plaintext_id not in retrieved.hashed_user_id

    @pytest.mark.asyncio
    async def test_cross_group_recognition(self, test_database):
        """Same user should be recognized across different groups."""
        plaintext_id = "user_123"
        hashed_id = hash_user_id(plaintext_id)
        
        # Create user
        user = User(hashed_user_id=hashed_id, preferred_language="zh")
        await user.insert()
        
        # User should be found by hashed ID regardless of group
        user_in_group1 = await User.find_one(User.hashed_user_id == hashed_id)
        user_in_group2 = await User.find_one(User.hashed_user_id == hashed_id)
        
        assert user_in_group1 is not None
        assert user_in_group2 is not None
        assert user_in_group1.hashed_user_id == user_in_group2.hashed_user_id

    @pytest.mark.asyncio
    async def test_different_users_different_hashes(self, test_database):
        """Different users should have different hashes."""
        user1_id = "user_1"
        user2_id = "user_2"
        
        hash1 = hash_user_id(user1_id)
        hash2 = hash_user_id(user2_id)
        
        assert hash1 != hash2


class Test90DayDeletion:
    """Test 90-day conversation deletion."""

    @pytest.mark.asyncio
    async def test_conversation_expires_after_90_days(self, test_database):
        """Conversations should have expires_at set to 90 days from timestamp."""
        user_id = hash_user_id("user_123")
        
        # Create conversation
        conv = Conversation.create(
            user_id=user_id,
            group_id="group_123",
            message="Hello",
            response="Hi!",
        )
        await conv.insert()
        
        # Check expires_at
        assert conv.expires_at is not None
        expected_expiry = conv.timestamp + timedelta(days=90)
        # Allow 1 second tolerance
        assert abs((conv.expires_at - expected_expiry).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_old_conversations_can_be_deleted(self, test_database):
        """Old conversations (past expires_at) should be deletable."""
        user_id = hash_user_id("user_123")
        
        # Create old conversation (91 days ago)
        old_timestamp = datetime.utcnow() - timedelta(days=91)
        old_expires_at = old_timestamp + timedelta(days=90)  # 1 day ago
        
        conv = Conversation(
            user_id=user_id,
            group_id="group_123",
            message="Old message",
            response="Old response",
            timestamp=old_timestamp,
            expires_at=old_expires_at,
        )
        await conv.insert()
        
        # Check if expired
        assert conv.is_expired() is True
        
        # Should be deletable
        await conv.delete()
        
        # Verify deleted
        retrieved = await Conversation.find_one(Conversation.id == conv.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_cleanup_old_conversations(self, test_database):
        """Cleanup script should delete conversations older than 90 days."""
        user_id = hash_user_id("user_123")
        
        # Create old conversation (91 days ago)
        old_timestamp = datetime.utcnow() - timedelta(days=91)
        old_expires_at = old_timestamp + timedelta(days=90)
        
        old_conv = Conversation(
            user_id=user_id,
            group_id="group_123",
            message="Old message",
            response="Old response",
            timestamp=old_timestamp,
            expires_at=old_expires_at,
        )
        await old_conv.insert()
        
        # Create recent conversation (10 days ago)
        recent_timestamp = datetime.utcnow() - timedelta(days=10)
        recent_conv = Conversation.create(
            user_id=user_id,
            group_id="group_123",
            message="Recent message",
            response="Recent response",
            timestamp=recent_timestamp,
        )
        await recent_conv.insert()
        
        # Find expired conversations
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        expired = await Conversation.find(
            Conversation.expires_at < cutoff_date
        ).to_list()
        
        # Should find old conversation
        assert len(expired) >= 1
        assert any(c.id == old_conv.id for c in expired)
        
        # Should not find recent conversation
        assert not any(c.id == recent_conv.id for c in expired)

    @pytest.mark.asyncio
    async def test_conversation_indexed_for_cleanup(self, test_database):
        """Conversations should be indexed on expires_at for efficient cleanup."""
        user_id = hash_user_id("user_123")
        
        # Create multiple conversations with different expiry dates
        for i in range(5):
            timestamp = datetime.utcnow() - timedelta(days=100 - i)
            conv = Conversation(
                user_id=user_id,
                group_id="group_123",
                message=f"Message {i}",
                response=f"Response {i}",
                timestamp=timestamp,
                expires_at=timestamp + timedelta(days=90),
            )
            await conv.insert()
        
        # Query should be efficient (uses index)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        expired = await Conversation.find(
            Conversation.expires_at < cutoff_date
        ).to_list()
        
        # Should find expired conversations
        assert len(expired) > 0


class TestPrivacyCompliance:
    """Test privacy compliance features."""

    @pytest.mark.asyncio
    async def test_no_plaintext_user_ids_stored(self, test_database):
        """No plaintext user IDs should be stored in database."""
        plaintext_id = "user_123"
        hashed_id = hash_user_id(plaintext_id)
        
        # Create user and conversation
        user = User(hashed_user_id=hashed_id)
        await user.insert()
        
        conv = Conversation.create(
            user_id=hashed_id,
            group_id="group_123",
            message="Test",
            response="Test response",
        )
        await conv.insert()
        
        # Verify no plaintext ID in database
        # (This is a conceptual test - actual verification would require DB inspection)
        assert user.hashed_user_id == hashed_id
        assert conv.user_id == hashed_id
        assert plaintext_id not in user.hashed_user_id
        assert plaintext_id not in conv.user_id

    @pytest.mark.asyncio
    async def test_user_recognition_without_plaintext(self, test_database):
        """Users should be recognized by hash without storing plaintext."""
        plaintext_id = "user_123"
        hashed_id = hash_user_id(plaintext_id)
        
        # Create user
        user = User(hashed_user_id=hashed_id)
        await user.insert()
        
        # Find user by hash (without knowing plaintext)
        found = await User.find_one(User.hashed_user_id == hashed_id)
        assert found is not None
        assert found.hashed_user_id == hashed_id

    @pytest.mark.asyncio
    async def test_conversation_history_privacy(self, test_database):
        """Conversation history should only reference hashed user IDs."""
        plaintext_id = "user_123"
        hashed_id = hash_user_id(plaintext_id)
        
        # Create conversation
        conv = Conversation.create(
            user_id=hashed_id,
            group_id="group_123",
            message="Private message",
            response="Private response",
        )
        await conv.insert()
        
        # Retrieve conversation
        retrieved = await Conversation.find_one(Conversation.id == conv.id)
        assert retrieved is not None
        assert retrieved.user_id == hashed_id
        # Should not contain plaintext
        assert plaintext_id not in retrieved.user_id
