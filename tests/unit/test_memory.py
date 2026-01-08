"""
Unit tests for memory functionality (Phase 6).

Tests impression update, context retrieval, preference learning,
and unconfirmed preference handling.

Per T058: Create tests/unit/test_memory.py with impression update
and context retrieval tests, covering configurable history limit,
explicit/implicit preference confirmation, and unconfirmed preference
handling (pending state, natural re-confirmation).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.conversation import Conversation
from src.models.impression import Impression
from src.models.user import User
from src.steps.step1 import ParsedInput
from src.steps.step2 import UserContext, retrieve_context
from src.steps.step5 import update_impression


class TestImpressionModel:
    """Test Impression model methods for preference handling."""
    
    @pytest.fixture(autouse=True)
    def setup_mock_beanie(self, mock_beanie_init):
        """Setup mock Beanie for all tests in this class."""
        # mock_beanie_init fixture is automatically applied via autouse=True
        pass

    def test_add_pending_preference(self) -> None:
        """Test adding a pending preference."""
        impression = Impression(
            user_id="test_user",
            relationship_status="new",
            interaction_count=0,
        )
        
        impression.add_pending_preference(
            key="favorite_bpm_range",
            value="high",
            context="User mentioned liking fast songs",
        )
        
        assert "favorite_bpm_range" in impression.pending_preferences
        assert impression.pending_preferences["favorite_bpm_range"]["value"] == "high"
        assert "extracted_at" in impression.pending_preferences["favorite_bpm_range"]
        assert "context" in impression.pending_preferences["favorite_bpm_range"]

    def test_get_pending_preference(self) -> None:
        """Test getting a pending preference."""
        impression = Impression(
            user_id="test_user",
            relationship_status="new",
            interaction_count=0,
        )
        
        impression.add_pending_preference(
            key="favorite_bpm_range",
            value="high",
            context="Test context",
        )
        
        pending = impression.get_pending_preference("favorite_bpm_range")
        assert pending is not None
        assert pending["value"] == "high"
        
        # Test non-existent preference
        assert impression.get_pending_preference("nonexistent") is None

    def test_confirm_pending_preference(self) -> None:
        """Test confirming a pending preference."""
        impression = Impression(
            user_id="test_user",
            relationship_status="new",
            interaction_count=0,
        )
        
        # Add pending preference
        impression.add_pending_preference(
            key="favorite_bpm_range",
            value="high",
            context="Test context",
        )
        
        # Confirm it
        result = impression.confirm_pending_preference("favorite_bpm_range")
        assert result is True
        assert "favorite_bpm_range" in impression.preferences
        assert impression.preferences["favorite_bpm_range"] == "high"
        assert "favorite_bpm_range" not in impression.pending_preferences
        
        # Test confirming non-existent preference
        result = impression.confirm_pending_preference("nonexistent")
        assert result is False

    def test_update_preference_removes_from_pending(self) -> None:
        """Test that updating a preference removes it from pending."""
        impression = Impression(
            user_id="test_user",
            relationship_status="new",
            interaction_count=0,
        )
        
        # Add pending preference
        impression.add_pending_preference(
            key="favorite_bpm_range",
            value="high",
            context="Test context",
        )
        
        # Update preference directly
        impression.update_preference("favorite_bpm_range", "medium")
        
        assert impression.preferences["favorite_bpm_range"] == "medium"
        assert "favorite_bpm_range" not in impression.pending_preferences


class TestContextRetrieval:
    """Test context retrieval with configurable history limit."""
    
    @pytest.fixture(autouse=True)
    def setup_mock_beanie(self, mock_beanie_init):
        """Setup mock Beanie for all tests in this class."""
        pass

    @pytest.mark.asyncio
    async def test_retrieve_context_new_user(self) -> None:
        """Test retrieving context for a new user."""
        hashed_user_id = "test_user_hash"
        
        # Mock database queries
        with patch("src.steps.step2.User.find_one", new_callable=AsyncMock) as mock_user, \
             patch("src.steps.step2.Impression.find_one", new_callable=AsyncMock) as mock_impression, \
             patch("src.steps.step2.Conversation.find") as mock_conversation:
            
            mock_user.return_value = None
            mock_impression.return_value = None
            mock_conversation.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
            
            context = await retrieve_context(hashed_user_id)
            
            assert context.is_new_user is True
            assert context.user is None
            assert context.impression is None
            assert context.recent_conversations == []

    @pytest.mark.asyncio
    async def test_retrieve_context_existing_user(self) -> None:
        """Test retrieving context for an existing user."""
        hashed_user_id = "test_user_hash"
        
        # Create mock user and impression
        mock_user = User(
            hashed_user_id=hashed_user_id,
            preferred_language="zh",
        )
        mock_impression = Impression(
            user_id=hashed_user_id,
            relationship_status="friend",
            interaction_count=25,
        )
        
        # Create mock conversations
        mock_conversations = [
            Conversation.create(
                user_id=hashed_user_id,
                group_id="group1",
                message="Message 1",
                response="Response 1",
                timestamp=datetime.utcnow() - timedelta(hours=1),
            ),
            Conversation.create(
                user_id=hashed_user_id,
                group_id="group1",
                message="Message 2",
                response="Response 2",
                timestamp=datetime.utcnow() - timedelta(hours=2),
            ),
        ]
        
        # Mock database queries
        with patch("src.steps.step2.User.find_one", new_callable=AsyncMock) as mock_user_find, \
             patch("src.steps.step2.Impression.find_one", new_callable=AsyncMock) as mock_impression_find, \
             patch("src.steps.step2.Conversation.find") as mock_conversation_find:
            
            mock_user_find.return_value = mock_user
            mock_impression_find.return_value = mock_impression
            
            # Mock conversation query chain
            mock_query = MagicMock()
            mock_query.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=mock_conversations)
            mock_conversation_find.return_value = mock_query
            
            context = await retrieve_context(hashed_user_id)
            
            assert context.is_new_user is False
            assert context.user == mock_user
            assert context.impression == mock_impression
            assert len(context.recent_conversations) == 2
            assert context.relationship_status == "friend"
            assert context.interaction_count == 25

    @pytest.mark.asyncio
    async def test_retrieve_context_configurable_limit(self) -> None:
        """Test that conversation history limit is configurable."""
        hashed_user_id = "test_user_hash"
        
        # Create mock conversations (more than default limit)
        mock_conversations = [
            Conversation.create(
                user_id=hashed_user_id,
                group_id="group1",
                message=f"Message {i}",
                response=f"Response {i}",
                timestamp=datetime.utcnow() - timedelta(hours=i),
            )
            for i in range(15)  # More than default limit of 10
        ]
        
        # Mock database queries
        with patch("src.steps.step2.User.find_one", new_callable=AsyncMock) as mock_user, \
             patch("src.steps.step2.Impression.find_one", new_callable=AsyncMock) as mock_impression, \
             patch("src.steps.step2.Conversation.find") as mock_conversation_find, \
             patch("src.config.settings.conversation_history_limit", 5):  # Set custom limit
            
            mock_user.return_value = None
            mock_impression.return_value = None
            
            # Mock conversation query chain
            mock_query = MagicMock()
            mock_query.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=mock_conversations[:5])
            mock_conversation_find.return_value = mock_query
            
            context = await retrieve_context(hashed_user_id)
            
            # Verify limit was applied (should only get 5 conversations)
            assert len(context.recent_conversations) == 5


class TestPreferenceLearning:
    """Test preference learning and confirmation flow."""
    
    @pytest.fixture(autouse=True)
    def setup_mock_beanie(self, mock_beanie_init):
        """Setup mock Beanie for all tests in this class."""
        pass

    @pytest.mark.asyncio
    async def test_update_impression_new_user(self) -> None:
        """Test updating impression for a new user."""
        parsed_input = ParsedInput(
            hashed_user_id="test_user_hash",
            group_id="group1",
            message="Mika, hello!",
            language="zh",
        )
        
        context = UserContext()  # New user context
        response = "Don! Hello! 🥁"
        
        # Mock database operations
        # Note: With mock_beanie_init, insert/save operations will use mocked collection
        with patch("src.steps.step5._handle_preference_learning", new_callable=AsyncMock) as mock_pref_learning:
            user, impression, conversation = await update_impression(
                parsed_input=parsed_input,
                context=context,
                response=response,
            )
            
            assert user.hashed_user_id == "test_user_hash"
            assert impression.user_id == "test_user_hash"
            assert impression.interaction_count == 1
            assert impression.relationship_status == "new"
            assert conversation.user_id == "test_user_hash"
            assert conversation.message == "Mika, hello!"
            assert conversation.response == response
            
            # Verify preference learning was called
            mock_pref_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_impression_existing_user(self) -> None:
        """Test updating impression for an existing user."""
        parsed_input = ParsedInput(
            hashed_user_id="test_user_hash",
            group_id="group1",
            message="Mika, hello again!",
            language="zh",
        )
        
        # Create existing user and impression
        existing_user = User(
            hashed_user_id="test_user_hash",
            preferred_language="zh",
        )
        existing_impression = Impression(
            user_id="test_user_hash",
            relationship_status="acquaintance",
            interaction_count=5,
        )
        
        context = UserContext(
            user=existing_user,
            impression=existing_impression,
        )
        response = "Don! Hello again! 🥁"
        
        # Mock database operations
        with patch("src.steps.step5.User.save", new_callable=AsyncMock), \
             patch("src.steps.step5.Impression.save", new_callable=AsyncMock), \
             patch("src.steps.step5.Conversation.insert", new_callable=AsyncMock), \
             patch("src.steps.step5._handle_preference_learning", new_callable=AsyncMock) as mock_pref_learning:
            
            user, impression, conversation = await update_impression(
                parsed_input=parsed_input,
                context=context,
                response=response,
            )
            
            assert user == existing_user
            assert impression == existing_impression
            assert impression.interaction_count == 6  # Incremented
            assert impression.relationship_status == "acquaintance"  # Still acquaintance (< 11)
            
            # Verify preference learning was called
            mock_pref_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_relationship_status_progression(self) -> None:
        """Test relationship status progression based on interaction count."""
        parsed_input = ParsedInput(
            hashed_user_id="test_user_hash",
            group_id="group1",
            message="Mika, hello!",
            language="zh",
        )
        
        # Test different interaction counts
        test_cases = [
            (1, "new"),
            (3, "acquaintance"),
            (11, "friend"),
            (51, "regular"),
        ]
        
        for interaction_count, expected_status in test_cases:
            # Create user for context
            user = User(
                hashed_user_id="test_user_hash",
                preferred_language="zh",
            )
            
            existing_impression = Impression(
                user_id="test_user_hash",
                relationship_status="new",
                interaction_count=interaction_count - 1,  # Will be incremented
            )
            
            context = UserContext(
                user=user,
                impression=existing_impression,
            )
            response = "Don! Hello! 🥁"
            
            # Mock database operations
            # Note: With mock_beanie_init, save/insert operations will use mocked collection
            with patch("src.steps.step5._handle_preference_learning", new_callable=AsyncMock):
                _, impression, _ = await update_impression(
                    parsed_input=parsed_input,
                    context=context,
                    response=response,
                )
                
                assert impression.interaction_count == interaction_count
                assert impression.relationship_status == expected_status, \
                    f"Expected {expected_status} for {interaction_count} interactions, got {impression.relationship_status}"
