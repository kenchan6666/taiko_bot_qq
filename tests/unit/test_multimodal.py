"""
Unit tests for multi-modal content support (image processing).

This module tests image validation, format detection, and multi-modal
LLM request handling.

Per FR-006: Image processing limits (10MB max, JPEG/PNG/WebP only).
Per Phase 7: User Story 4 - Multi-Modal Content Support.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.llm import LLMService, _detect_image_mime_type
from src.steps.step1 import _detect_image_format, _validate_images, parse_input


class TestImageValidation:
    """Test image validation in step1.py."""

    def test_validate_images_empty_list(self) -> None:
        """Test validation with empty image list."""
        result = _validate_images([], "zh")
        assert result == []

    def test_validate_images_valid_jpeg(self) -> None:
        """Test validation with valid JPEG image."""
        # Create a minimal valid JPEG base64 (JPEG magic bytes: FF D8 FF)
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"x" * 1000  # Small JPEG
        jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")

        result = _validate_images([jpeg_base64], "zh")
        assert result is not None
        assert len(result) == 1
        assert result[0] == jpeg_base64

    def test_validate_images_valid_png(self) -> None:
        """Test validation with valid PNG image."""
        # Create a minimal valid PNG base64 (PNG magic bytes: 89 50 4E 47)
        png_data = b"\x89PNG\r\n\x1a\n" + b"x" * 1000  # Small PNG
        png_base64 = base64.b64encode(png_data).decode("utf-8")

        result = _validate_images([png_base64], "zh")
        assert result is not None
        assert len(result) == 1
        assert result[0] == png_base64

    def test_validate_images_valid_webp(self) -> None:
        """Test validation with valid WebP image."""
        # Create a minimal valid WebP base64 (RIFF...WEBP)
        webp_data = b"RIFF" + b"x" * 4 + b"WEBP" + b"x" * 1000  # Small WebP
        webp_base64 = base64.b64encode(webp_data).decode("utf-8")

        result = _validate_images([webp_base64], "zh")
        assert result is not None
        assert len(result) == 1
        assert result[0] == webp_base64

    def test_validate_images_invalid_format(self) -> None:
        """Test validation with invalid image format."""
        # Create invalid format (GIF magic bytes)
        gif_data = b"GIF89a" + b"x" * 1000
        gif_base64 = base64.b64encode(gif_data).decode("utf-8")

        result = _validate_images([gif_base64], "zh")
        # Invalid format should be filtered out
        assert result is None

    def test_validate_images_too_large(self) -> None:
        """Test validation with image exceeding size limit."""
        # Create a large JPEG (exceeds 10MB limit)
        # Note: In actual test, we'd need to mock settings.image_max_size_mb
        # For now, we test with a smaller limit
        with patch("src.steps.step1.settings") as mock_settings:
            mock_settings.image_max_size_mb = 1  # 1MB limit for test
            mock_settings.image_allowed_formats = ["jpeg", "png", "webp"]

            # Create a 2MB JPEG
            large_jpeg_data = b"\xff\xd8\xff\xe0" + b"x" * (2 * 1024 * 1024)
            large_jpeg_base64 = base64.b64encode(large_jpeg_data).decode("utf-8")

            result = _validate_images([large_jpeg_base64], "zh")
            # Too large image should be filtered out
            assert result is None

    def test_validate_images_invalid_base64(self) -> None:
        """Test validation with invalid base64 string."""
        invalid_base64 = "not_valid_base64!!!"

        result = _validate_images([invalid_base64], "zh")
        # Invalid base64 should be filtered out
        assert result is None

    def test_validate_images_mixed_valid_invalid(self) -> None:
        """Test validation with mix of valid and invalid images."""
        # Valid JPEG
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"x" * 1000
        jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")

        # Invalid format (GIF)
        gif_data = b"GIF89a" + b"x" * 1000
        gif_base64 = base64.b64encode(gif_data).decode("utf-8")

        result = _validate_images([jpeg_base64, gif_base64], "zh")
        # Should return only valid images
        assert result is not None
        assert len(result) == 1
        assert result[0] == jpeg_base64


class TestImageFormatDetection:
    """Test image format detection functions."""

    def test_detect_image_format_jpeg(self) -> None:
        """Test JPEG format detection."""
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        result = _detect_image_format(jpeg_data)
        assert result == "jpeg"

    def test_detect_image_format_png(self) -> None:
        """Test PNG format detection."""
        png_data = b"\x89PNG\r\n\x1a\n"
        result = _detect_image_format(png_data)
        assert result == "png"

    def test_detect_image_format_webp(self) -> None:
        """Test WebP format detection."""
        webp_data = b"RIFF" + b"x" * 4 + b"WEBP"
        result = _detect_image_format(webp_data)
        assert result == "webp"

    def test_detect_image_format_unknown(self) -> None:
        """Test unknown format detection."""
        unknown_data = b"GIF89a"
        result = _detect_image_format(unknown_data)
        assert result is None

    def test_detect_image_format_too_short(self) -> None:
        """Test format detection with too short data."""
        short_data = b"AB"
        result = _detect_image_format(short_data)
        assert result is None


class TestImageMimeTypeDetection:
    """Test image MIME type detection in llm.py."""

    def test_detect_image_mime_type_jpeg(self) -> None:
        """Test JPEG MIME type detection."""
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")
        result = _detect_image_mime_type(jpeg_base64)
        assert result == "image/jpeg"

    def test_detect_image_mime_type_png(self) -> None:
        """Test PNG MIME type detection."""
        png_data = b"\x89PNG\r\n\x1a\n"
        png_base64 = base64.b64encode(png_data).decode("utf-8")
        result = _detect_image_mime_type(png_base64)
        assert result == "image/png"

    def test_detect_image_mime_type_webp(self) -> None:
        """Test WebP MIME type detection."""
        webp_data = b"RIFF" + b"x" * 4 + b"WEBP"
        webp_base64 = base64.b64encode(webp_data).decode("utf-8")
        result = _detect_image_mime_type(webp_base64)
        assert result == "image/webp"

    def test_detect_image_mime_type_invalid_base64(self) -> None:
        """Test MIME type detection with invalid base64."""
        invalid_base64 = "not_valid_base64!!!"
        result = _detect_image_mime_type(invalid_base64)
        # Should default to JPEG
        assert result == "image/jpeg"

    def test_detect_image_mime_type_unknown_format(self) -> None:
        """Test MIME type detection with unknown format."""
        gif_data = b"GIF89a"
        gif_base64 = base64.b64encode(gif_data).decode("utf-8")
        result = _detect_image_mime_type(gif_base64)
        # Should default to JPEG
        assert result == "image/jpeg"


class TestParseInputWithImages:
    """Test parse_input function with image handling."""

    @patch("src.steps.step1.check_content")
    @patch("src.steps.step1.get_deduplication_service")
    @patch("src.steps.step1.hash_user_id")
    @patch("src.steps.step1.detect_language")
    def test_parse_input_with_valid_images(
        self,
        mock_detect_language: MagicMock,
        mock_hash_user_id: MagicMock,
        mock_dedup_service: MagicMock,
        mock_check_content: MagicMock,
    ) -> None:
        """Test parse_input with valid images."""
        # Setup mocks
        mock_detect_language.return_value = "zh"
        mock_hash_user_id.return_value = "hashed_user_id_123"
        mock_check_content.return_value = (False, None)
        mock_dedup_service_instance = MagicMock()
        mock_dedup_service_instance.is_duplicate.return_value = False
        mock_dedup_service.return_value = mock_dedup_service_instance

        # Create valid JPEG
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"x" * 1000
        jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")

        # Parse input with images
        result = parse_input(
            user_id="123456789",
            group_id="987654321",
            message="Mika, 看看这张图片",
            images=[jpeg_base64],
        )

        # Should return ParsedInput with validated images
        assert result is not None
        assert result.hashed_user_id == "hashed_user_id_123"
        assert result.message == "Mika, 看看这张图片"
        assert len(result.images) == 1
        assert result.images[0] == jpeg_base64

    @patch("src.steps.step1.check_content")
    @patch("src.steps.step1.get_deduplication_service")
    @patch("src.steps.step1.hash_user_id")
    @patch("src.steps.step1.detect_language")
    def test_parse_input_with_invalid_images(
        self,
        mock_detect_language: MagicMock,
        mock_hash_user_id: MagicMock,
        mock_dedup_service: MagicMock,
        mock_check_content: MagicMock,
    ) -> None:
        """Test parse_input with invalid images (should reject)."""
        # Setup mocks
        mock_detect_language.return_value = "zh"
        mock_hash_user_id.return_value = "hashed_user_id_123"
        mock_check_content.return_value = (False, None)
        mock_dedup_service_instance = MagicMock()
        mock_dedup_service_instance.is_duplicate.return_value = False
        mock_dedup_service.return_value = mock_dedup_service_instance

        # Create invalid format (GIF)
        gif_data = b"GIF89a" + b"x" * 1000
        gif_base64 = base64.b64encode(gif_data).decode("utf-8")

        # Parse input with invalid images
        result = parse_input(
            user_id="123456789",
            group_id="987654321",
            message="Mika, 看看这张图片",
            images=[gif_base64],
        )

        # Should return None (rejected due to invalid image format)
        assert result is None


class TestLLMServiceMultiModal:
    """Test LLM service multi-modal support."""

    @pytest.mark.asyncio
    async def test_generate_response_with_images(self) -> None:
        """Test LLM service with image input."""
        # Create mock HTTP client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is a Taiko screenshot!"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        # Create LLM service with mocked client
        service = LLMService(api_key="test_key")
        service.client = mock_client

        # Create valid JPEG base64
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"x" * 1000
        jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")

        # Generate response with image
        response = await service.generate_response(
            prompt="Analyze this image",
            images=[jpeg_base64],
        )

        # Verify response
        assert response == "This is a Taiko screenshot!"

        # Verify API call was made with image
        call_args = mock_client.post.call_args
        assert call_args is not None
        payload = call_args[1]["json"]
        assert "messages" in payload
        message = payload["messages"][0]
        assert "content" in message
        content = message["content"]
        assert len(content) == 2  # Text + image
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image_url"
        assert "data:image/jpeg;base64," in content[1]["image_url"]["url"]
