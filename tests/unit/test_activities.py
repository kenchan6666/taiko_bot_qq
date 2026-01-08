"""
Unit tests for Temporal Activities.

Tests all 5 activities (step1-step5) to ensure they correctly wrap
step functions and handle serialization/deserialization.

Per T051: Create tests/unit/test_activities.py with Activity tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.activities.step1_activity import step1_parse_input_activity
from src.activities.step2_activity import step2_retrieve_context_activity
from src.activities.step3_activity import step3_query_song_activity
from src.activities.step4_activity import step4_invoke_llm_activity
from src.activities.step5_activity import step5_update_impression_activity
from tests.fixtures.mock_songs import get_mock_song


class TestStep1Activity:
    """Test step1_parse_input_activity."""

    @pytest.mark.asyncio
    async def test_parse_input_valid_message(self) -> None:
        """Test parsing valid message with 'Mika' mention."""
        result = await step1_parse_input_activity(
            user_id="123456789",
            group_id="987654321",
            message="Mika, hello!",
        )

        assert result is not None
        assert result["hashed_user_id"] is not None
        assert result["group_id"] == "987654321"
        assert result["message"] == "Mika, hello!"
        assert result["language"] in ["zh", "en"]

    def test_parse_input_no_mika_mention(self) -> None:
        """Test parsing message without 'Mika' mention returns None."""
        result = step1_parse_input_activity(
            user_id="123456789",
            group_id="987654321",
            message="Hello, world!",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_input_with_images(self) -> None:
        """Test parsing message with images."""
        images = ["base64_image_1", "base64_image_2"]
        result = await step1_parse_input_activity(
            user_id="123456789",
            group_id="987654321",
            message="Mika, look at this image!",
            images=images,
        )

        assert result is not None
        assert result["images"] == images


class TestStep2Activity:
    """Test step2_retrieve_context_activity."""

    @pytest.mark.asyncio
    async def test_retrieve_context_new_user(self) -> None:
        """Test retrieving context for new user."""
        # Mock MongoDB queries to return None (new user)
        with patch("src.steps.step2.User.find_one", new_callable=AsyncMock, return_value=None):
            with patch("src.steps.step2.Impression.find_one", new_callable=AsyncMock, return_value=None):
                with patch("src.steps.step2.Conversation.find") as mock_find:
                    mock_find.return_value.sort.return_value.limit.return_value.to_list = (
                        AsyncMock(return_value=[])
                    )

                    result = await step2_retrieve_context_activity("hashed_user_id_123")

                    assert result["is_new_user"] is True
                    assert result["user"] is None
                    assert result["impression"] is None
                    assert result["recent_conversations"] == []

    @pytest.mark.asyncio
    async def test_retrieve_context_existing_user(self) -> None:
        """Test retrieving context for existing user."""
        from src.models.user import User
        from src.models.impression import Impression
        from datetime import datetime

        # Create mock user and impression
        mock_user = User(
            hashed_user_id="hashed_user_id_123",
            preferred_language="zh",
        )
        mock_user.created_at = datetime.utcnow()
        mock_user.updated_at = datetime.utcnow()

        mock_impression = Impression(
            user_id="hashed_user_id_123",
            relationship_status="friend",
            interaction_count=10,
        )
        mock_impression.last_interaction = datetime.utcnow()

        # Mock MongoDB queries
        with patch("src.steps.step2.User.find_one", new_callable=AsyncMock, return_value=mock_user):
            with patch("src.steps.step2.Impression.find_one", new_callable=AsyncMock, return_value=mock_impression):
                with patch("src.steps.step2.Conversation.find") as mock_find:
                    mock_find.return_value.sort.return_value.limit.return_value.to_list = (
                        AsyncMock(return_value=[])
                    )

                    result = await step2_retrieve_context_activity("hashed_user_id_123")

                    assert result["is_new_user"] is False
                    assert result["user"] is not None
                    assert result["impression"] is not None
                    assert result["relationship_status"] == "friend"
                    assert result["interaction_count"] == 10


class TestStep3Activity:
    """Test step3_query_song_activity."""

    @pytest.mark.asyncio
    async def test_query_song_found(self) -> None:
        """Test querying song that exists."""
        # Mock song service
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))
        mock_service.query_song.return_value = get_mock_song("千本桜")

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result = await step3_query_song_activity("What's the BPM of 千本桜?")

            assert result is not None
            assert result["song_name"] == "千本桜"
            assert result["bpm"] == 200

    @pytest.mark.asyncio
    async def test_query_song_not_found(self) -> None:
        """Test querying song that doesn't exist."""
        # Mock song service with no match
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))
        mock_service.query_song.return_value = None

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result = await step3_query_song_activity("Non-existent song")

            assert result is None


class TestStep4Activity:
    """Test step4_invoke_llm_activity."""

    @pytest.mark.asyncio
    async def test_invoke_llm_general_chat(self) -> None:
        """Test invoking LLM for general chat."""
        parsed_input_dict = {
            "hashed_user_id": "abc123",
            "group_id": "group123",
            "message": "Mika, hello!",
            "language": "en",
            "images": [],
        }
        context_dict = {
            "user": None,
            "impression": None,
            "recent_conversations": [],
            "is_new_user": True,
            "preferred_language": None,
            "relationship_status": "new",
            "interaction_count": 0,
        }

        # Mock LLM service
        mock_llm = MagicMock()
        mock_llm.generate_response = AsyncMock(return_value="Don! Hello! I'm Mika! 🥁")

        with patch("src.steps.step4.get_llm_service", return_value=mock_llm):
            result = await step4_invoke_llm_activity(parsed_input_dict, context_dict)

            assert result == "Don! Hello! I'm Mika! 🥁"
            mock_llm.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_llm_with_song_info(self) -> None:
        """Test invoking LLM with song information."""
        parsed_input_dict = {
            "hashed_user_id": "abc123",
            "group_id": "group123",
            "message": "What's the BPM of 千本桜?",
            "language": "en",
            "images": [],
        }
        context_dict = {
            "user": None,
            "impression": None,
            "recent_conversations": [],
            "is_new_user": True,
            "preferred_language": None,
            "relationship_status": "new",
            "interaction_count": 0,
        }
        song_info = {
            "song_name": "千本桜",
            "bpm": 200,
            "difficulty_stars": 9,
            "metadata": {"genre": "Vocaloid"},
        }

        # Mock LLM service
        mock_llm = MagicMock()
        mock_llm.generate_response = AsyncMock(
            return_value="Don! 千本桜 has a BPM of 200! 🥁"
        )

        with patch("src.steps.step4.get_llm_service", return_value=mock_llm):
            result = await step4_invoke_llm_activity(
                parsed_input_dict, context_dict, song_info
            )

            assert "千本桜" in result
            assert "200" in result
            mock_llm.generate_response.assert_called_once()


class TestStep5Activity:
    """Test step5_update_impression_activity."""

    @pytest.mark.asyncio
    async def test_update_impression_new_user(self) -> None:
        """Test updating impression for new user."""
        parsed_input_dict = {
            "hashed_user_id": "abc123",
            "group_id": "group123",
            "message": "Mika, hello!",
            "language": "en",
            "images": [],
        }
        context_dict = {
            "user": None,
            "impression": None,
            "recent_conversations": [],
            "is_new_user": True,
            "preferred_language": None,
            "relationship_status": "new",
            "interaction_count": 0,
        }
        response = "Don! Hello! I'm Mika! 🥁"

        # Mock database operations
        with patch("src.models.user.User.insert", new_callable=AsyncMock):
            with patch("src.models.impression.Impression.insert", new_callable=AsyncMock):
                with patch("src.models.conversation.Conversation.insert", new_callable=AsyncMock):
                    result = await step5_update_impression_activity(
                        parsed_input_dict, context_dict, response
                    )

                    assert result["interaction_count"] == 1
                    assert result["relationship_status"] == "new"
                    assert result["user"] is not None
                    assert result["impression"] is not None
                    assert result["conversation"] is not None
