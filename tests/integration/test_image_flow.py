"""
Integration tests for image processing flow.

This module tests end-to-end image processing from webhook input
through LLM response generation.

Per FR-006: Image processing with detailed analysis for Taiko images
and themed responses for non-Taiko images.
Per Phase 7: User Story 4 - Multi-Modal Content Support.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.conversation import Conversation
from src.models.impression import Impression
from src.models.user import User
from src.steps.step1 import ParsedInput, parse_input
from src.steps.step2 import UserContext, retrieve_context
from src.steps.step4 import invoke_llm
from src.steps.step5 import update_impression


# Helper function to create valid JPEG test data
def create_test_jpeg_data(size: int = 5000) -> tuple[bytes, str]:
    """
    Create valid JPEG test data.

    Args:
        size: Size of additional data to append (default: 5000 bytes).

    Returns:
        Tuple of (binary_data, base64_encoded_string).
    """
    # Valid JPEG header: FF D8 FF E0 (SOI + APP0 marker)
    # Followed by JFIF header
    jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01" + b"x" * size
    jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")
    return jpeg_data, jpeg_base64


# Helper to disable message deduplication for tests
def disable_deduplication_for_test():
    """
    Disable message deduplication for testing.
    
    This clears the message cache to prevent deduplication from
    rejecting test messages that might be similar to previous test runs.
    """
    from src.services.message_deduplication import get_deduplication_service
    dedup_service = get_deduplication_service()
    # Clear the deduplication cache to avoid false positives
    if hasattr(dedup_service, "_message_cache"):
        dedup_service._message_cache.clear()
    # Also disable deduplication temporarily
    original_enabled = dedup_service.enabled
    dedup_service.enabled = False
    return original_enabled  # Return original state for restoration if needed


class TestImageProcessingFlow:
    """Test end-to-end image processing flow."""

    @pytest.mark.asyncio
    async def test_image_processing_with_valid_jpeg(
        self, test_database: None
    ) -> None:
        """Test complete flow with valid JPEG image."""
        # Use consistent user_id for hashing
        test_user_id = "123456789"
        from src.utils.hashing import hash_user_id
        
        # Create test user and impression with correct hashed_id
        hashed_user_id = hash_user_id(test_user_id)
        user = User(
            hashed_user_id=hashed_user_id,
            preferred_language="zh",
        )
        await user.insert()

        impression = Impression(
            user_id=hashed_user_id,
            relationship_status="new",
            interaction_count=0,
        )
        await impression.insert()

        # Create valid JPEG base64 (larger to ensure it passes validation)
        _, jpeg_base64 = create_test_jpeg_data(size=5000)

        # Disable message deduplication for this test
        disable_deduplication_for_test()
        
        # Step 1: Parse input with image
        parsed_input = parse_input(
            user_id=test_user_id,
            group_id="987654321",
            message="Mika, 看看这张图片",
            images=[jpeg_base64],
        )

        # Should parse successfully with validated image
        assert parsed_input is not None, "parse_input should succeed with valid JPEG"
        assert len(parsed_input.images) == 1, "Should have 1 validated image"
        assert parsed_input.images[0] == jpeg_base64, "Image should be preserved"

        # Step 2: Retrieve context
        context = await retrieve_context(parsed_input.hashed_user_id)
        assert context.user is not None, "User should be retrieved from database"
        assert context.user.hashed_user_id == user.hashed_user_id, "User IDs should match"

        # Step 3: Mock LLM service for image analysis
        with patch("src.steps.step4.get_llm_service") as mock_get_llm:
            mock_llm_service = AsyncMock()
            mock_llm_service.generate_response = AsyncMock(
                return_value="Don! 这是一张太鼓の達人的截图！我看到了歌曲《千本桜》和难度等级！🥁"
            )
            mock_get_llm.return_value = mock_llm_service

            # Step 4: Invoke LLM with image
            response = await invoke_llm(
                parsed_input=parsed_input,
                context=context,
                song_info=None,
            )

            # Verify LLM was called with image
            assert response is not None
            assert "太鼓" in response or "Taiko" in response
            mock_llm_service.generate_response.assert_called_once()
            call_args = mock_llm_service.generate_response.call_args
            assert call_args[1]["images"] == [jpeg_base64]

        # Step 5: Update impression and save conversation
        user_updated, impression_updated, conversation = await update_impression(
            parsed_input=parsed_input,
            context=context,
            response=response,
        )

        # Verify conversation was saved with image
        assert conversation is not None
        assert conversation.user_id == parsed_input.hashed_user_id
        assert conversation.message == parsed_input.message
        assert conversation.response == response
        # Note: Images are stored in conversation.images field
        assert conversation.images is not None
        assert len(conversation.images) == 1

    @pytest.mark.asyncio
    async def test_image_processing_with_invalid_format(
        self, test_database: None
    ) -> None:
        """Test flow with invalid image format (should reject)."""
        # Disable message deduplication for this test
        disable_deduplication_for_test()
        
        # Create invalid format (GIF) - not in allowed formats
        gif_data = b"GIF89a" + b"x" * 1000
        gif_base64 = base64.b64encode(gif_data).decode("utf-8")

        # Step 1: Parse input with invalid image
        # Note: If all images fail validation, parse_input returns None
        parsed_input = parse_input(
            user_id="123456789",
            group_id="987654321",
            message="Mika, 看看这张图片",
            images=[gif_base64],
        )

        # Should reject due to invalid format (all images failed validation)
        assert parsed_input is None, "parse_input should reject when all images are invalid"

    @pytest.mark.asyncio
    async def test_image_processing_with_multiple_images(
        self, test_database: None
    ) -> None:
        """Test flow with multiple valid images."""
        # Use consistent user_id for hashing
        test_user_id = "123456789"
        from src.utils.hashing import hash_user_id
        
        # Create test user with correct hashed_id
        hashed_user_id = hash_user_id(test_user_id)
        user = User(
            hashed_user_id=hashed_user_id,
            preferred_language="zh",
        )
        await user.insert()

        # Create multiple valid JPEG images (larger to ensure validation passes)
        _, jpeg1_base64 = create_test_jpeg_data(size=5000)
        _, jpeg2_base64 = create_test_jpeg_data(size=5000)

        # Disable message deduplication for this test
        disable_deduplication_for_test()
        
        # Step 1: Parse input with multiple images
        parsed_input = parse_input(
            user_id=test_user_id,
            group_id="987654321",
            message="Mika, 看看这些图片",
            images=[jpeg1_base64, jpeg2_base64],
        )

        # Should parse successfully with all validated images
        assert parsed_input is not None, "parse_input should succeed with valid JPEGs"
        assert len(parsed_input.images) == 2, "Should have 2 validated images"

        # Step 2: Retrieve context
        context = await retrieve_context(parsed_input.hashed_user_id)

        # Step 3: Mock LLM service
        with patch("src.steps.step4.get_llm_service") as mock_get_llm:
            mock_llm_service = AsyncMock()
            mock_llm_service.generate_response = AsyncMock(
                return_value="Don! 我看到了两张太鼓の達人的截图！🥁"
            )
            mock_get_llm.return_value = mock_llm_service

            # Step 4: Invoke LLM with multiple images
            response = await invoke_llm(
                parsed_input=parsed_input,
                context=context,
                song_info=None,
            )

            # Verify LLM was called with all images
            call_args = mock_llm_service.generate_response.call_args
            assert call_args[1]["images"] == [jpeg1_base64, jpeg2_base64]

    @pytest.mark.asyncio
    async def test_image_processing_with_mixed_valid_invalid(
        self, test_database: None
    ) -> None:
        """Test flow with mix of valid and invalid images."""
        # Use consistent user_id for hashing
        test_user_id = "123456789"
        from src.utils.hashing import hash_user_id
        
        # Create test user with correct hashed_id
        hashed_user_id = hash_user_id(test_user_id)
        user = User(
            hashed_user_id=hashed_user_id,
            preferred_language="zh",
        )
        await user.insert()
        
        # Disable message deduplication for this test
        disable_deduplication_for_test()

        # Create valid JPEG and invalid GIF
        _, jpeg_base64 = create_test_jpeg_data(size=5000)
        
        gif_data = b"GIF89a" + b"x" * 1000
        gif_base64 = base64.b64encode(gif_data).decode("utf-8")

        # Step 1: Parse input with mixed images
        parsed_input = parse_input(
            user_id=test_user_id,
            group_id="987654321",
            message="Mika, 看看这些图片",
            images=[jpeg_base64, gif_base64],
        )

        # Current implementation: If at least one image is valid,
        # the message is accepted with only valid images
        # If all images fail, message is rejected (returns None)
        # Since we have one valid JPEG, message should be accepted
        assert parsed_input is not None, "parse_input should accept message with at least one valid image"
        # Should only have valid images (JPEG, not GIF)
        assert len(parsed_input.images) == 1, "Should have only valid images"
        assert parsed_input.images[0] == jpeg_base64, "Should contain the valid JPEG"

    @pytest.mark.asyncio
    async def test_image_processing_llm_fallback(
        self, test_database: None
    ) -> None:
        """Test image processing with LLM service failure (graceful degradation)."""
        # Use consistent user_id for hashing
        test_user_id = "123456789"
        from src.utils.hashing import hash_user_id
        
        # Create test user with correct hashed_id
        hashed_user_id = hash_user_id(test_user_id)
        user = User(
            hashed_user_id=hashed_user_id,
            preferred_language="zh",
        )
        await user.insert()

        # Create valid JPEG (larger to ensure validation passes)
        _, jpeg_base64 = create_test_jpeg_data(size=5000)

        # Disable message deduplication for this test
        disable_deduplication_for_test()
        
        # Step 1: Parse input
        parsed_input = parse_input(
            user_id=test_user_id,
            group_id="987654321",
            message="Mika, 看看这张图片",
            images=[jpeg_base64],
        )
        assert parsed_input is not None, "parse_input should succeed with valid JPEG"

        # Step 2: Retrieve context
        context = await retrieve_context(parsed_input.hashed_user_id)

        # Step 3: Mock LLM service to raise error
        with patch("src.steps.step4.get_llm_service") as mock_get_llm:
            mock_llm_service = AsyncMock()
            mock_llm_service.generate_response = AsyncMock(
                side_effect=RuntimeError("LLM service unavailable")
            )
            mock_get_llm.return_value = mock_llm_service

            # Step 4: Invoke LLM (should return fallback response)
            response = await invoke_llm(
                parsed_input=parsed_input,
                context=context,
                song_info=None,
            )

            # Should return fallback themed response
            assert response is not None
            assert "Mika" in response or "暂时无法回应" in response

    @pytest.mark.asyncio
    async def test_image_processing_with_song_info(
        self, test_database: None
    ) -> None:
        """Test image processing when song info is also available."""
        # Use consistent user_id for hashing
        test_user_id = "123456789"
        from src.utils.hashing import hash_user_id
        
        # Create test user with correct hashed_id
        hashed_user_id = hash_user_id(test_user_id)
        user = User(
            hashed_user_id=hashed_user_id,
            preferred_language="zh",
        )
        await user.insert()

        # Create valid JPEG (larger to ensure validation passes)
        _, jpeg_base64 = create_test_jpeg_data(size=5000)

        # Disable message deduplication for this test
        disable_deduplication_for_test()
        
        # Step 1: Parse input
        parsed_input = parse_input(
            user_id=test_user_id,
            group_id="987654321",
            message="Mika, 看看这张图片",
            images=[jpeg_base64],
        )
        assert parsed_input is not None, "parse_input should succeed with valid JPEG"

        # Step 2: Retrieve context
        context = await retrieve_context(parsed_input.hashed_user_id)

        # Step 3: Mock LLM service
        # Note: Images take priority over song_info in prompt selection
        with patch("src.steps.step4.get_llm_service") as mock_get_llm:
            mock_llm_service = AsyncMock()
            mock_llm_service.generate_response = AsyncMock(
                return_value="Don! 我看到了太鼓の達人的截图！🥁"
            )
            mock_get_llm.return_value = mock_llm_service

            # Step 4: Invoke LLM with both image and song_info
            # Image analysis should take priority
            song_info = {
                "song_name": "千本桜",
                "bpm": 200,
                "difficulty_stars": 5,
            }

            response = await invoke_llm(
                parsed_input=parsed_input,
                context=context,
                song_info=song_info,
            )

            # Verify response and that image was included
            assert response is not None
            call_args = mock_llm_service.generate_response.call_args
            assert call_args[1]["images"] == [jpeg_base64]
