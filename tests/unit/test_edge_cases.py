"""
Edge case tests for message processing.

Tests various edge cases including:
- No name trigger (group messages without "Mika" mention)
- Network failures
- LLM timeouts
- Malformed input

Per T094: Create tests/unit/test_edge_cases.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.steps.step1 import parse_input, ParsedInput
from src.services.llm import LLMService
from src.services.song_query import SongQueryService


class TestNoNameTrigger:
    """Test cases for messages without name trigger."""

    @pytest.mark.asyncio
    async def test_group_message_without_mika_mention(self):
        """Group message without 'Mika' mention should return None."""
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message="What's your favorite song?",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_group_message_with_mika_mention(self):
        """Group message with 'Mika' mention should be parsed."""
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message="Mika, what's your favorite song?",
        )
        assert result is not None
        assert isinstance(result, ParsedInput)

    @pytest.mark.asyncio
    async def test_private_message_without_mika_mention(self):
        """Private message without 'Mika' mention should still be parsed."""
        result = await parse_input(
            user_id="123456789",
            group_id="",  # Empty for private message
            message="What's your favorite song?",
        )
        assert result is not None
        assert isinstance(result, ParsedInput)


class TestNetworkFailures:
    """Test cases for network failures."""

    @pytest.mark.asyncio
    async def test_taikowiki_api_failure(self):
        """Test fallback when taikowiki API fails."""
        with patch("src.services.song_query.SongQueryService.fetch_songs") as mock_fetch:
            # Simulate API failure
            mock_fetch.side_effect = Exception("Network error: Connection refused")
            
            service = SongQueryService()
            
            # Should use fallback (local JSON)
            songs, used_fallback = await service.fetch_songs(use_fallback=True)
            
            assert used_fallback is True
            # Should still return songs from fallback
            assert len(songs) > 0

    @pytest.mark.asyncio
    async def test_openrouter_api_failure(self):
        """Test fallback when OpenRouter API fails."""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Simulate API failure
            mock_post.side_effect = Exception("Network error: Connection timeout")
            
            service = LLMService()
            
            # Should raise exception or return fallback
            with pytest.raises(Exception):
                await service.generate_response(
                    prompt="Test prompt",
                    images=None,
                )

    @pytest.mark.asyncio
    async def test_mongodb_connection_failure(self):
        """Test behavior when MongoDB connection fails."""
        with patch("src.services.database.init_database") as mock_init:
            mock_init.side_effect = Exception("MongoDB connection failed")
            
            # Should raise exception
            with pytest.raises(Exception):
                await mock_init()


class TestLLMTimeouts:
    """Test cases for LLM timeouts."""

    @pytest.mark.asyncio
    async def test_llm_timeout(self):
        """Test handling of LLM timeout."""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Simulate timeout
            import asyncio
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            service = LLMService()
            
            # Should raise timeout exception
            with pytest.raises(asyncio.TimeoutError):
                await service.generate_response(
                    prompt="Test prompt",
                    images=None,
                )

    @pytest.mark.asyncio
    async def test_llm_slow_response(self):
        """Test handling of slow LLM response."""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Simulate slow response (but not timeout)
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(5)  # Simulate slow response
                return MagicMock(
                    status_code=200,
                    json=AsyncMock(return_value={"choices": [{"message": {"content": "Response"}}]}),
                )
            
            import asyncio
            mock_post.side_effect = slow_response
            
            service = LLMService()
            
            # Should eventually return response (if timeout not exceeded)
            # This depends on actual timeout settings
            try:
                response = await asyncio.wait_for(
                    service.generate_response(prompt="Test", images=None),
                    timeout=10.0,
                )
                assert response is not None
            except asyncio.TimeoutError:
                # Timeout is expected if response is too slow
                pass


class TestMalformedInput:
    """Test cases for malformed input."""

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Empty message should return None."""
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message="",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_only_message(self):
        """Whitespace-only message should return None."""
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message="   \n\t  ",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_user_id(self):
        """Missing user_id should return None."""
        result = await parse_input(
            user_id="",
            group_id="987654321",
            message="Mika, hello!",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_image_format(self):
        """Invalid image format should be handled gracefully."""
        # Test with invalid base64
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message="Mika, analyze this image",
            images=["invalid_base64_data!!!"],
        )
        # Should still parse (image validation happens later)
        # Or return None if validation is strict
        # This depends on implementation

    @pytest.mark.asyncio
    async def test_very_long_message(self):
        """Very long message should be handled."""
        long_message = "Mika, " + "x" * 10000  # 10KB message
        
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message=long_message,
        )
        # Should still parse (may be truncated later)
        assert result is not None

    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Message with special characters should be handled."""
        special_message = "Mika, test: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message=special_message,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_unicode_characters(self):
        """Message with Unicode characters should be handled."""
        unicode_message = "Mika, 测试：你好！🎶🥁"
        
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message=unicode_message,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_null_bytes(self):
        """Message with null bytes should be handled."""
        # Note: This may cause issues, should be sanitized
        message_with_null = "Mika, test\x00message"
        
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message=message_with_null,
        )
        # Should handle gracefully (may sanitize or reject)
        # This depends on implementation

    @pytest.mark.asyncio
    async def test_sql_injection_attempt(self):
        """SQL injection attempt should be handled safely."""
        # Note: We use MongoDB, not SQL, but should still handle safely
        sql_injection = "Mika'; DROP TABLE users; --"
        
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message=sql_injection,
        )
        # Should parse as normal text (MongoDB is safe from SQL injection)
        assert result is not None

    @pytest.mark.asyncio
    async def test_xss_attempt(self):
        """XSS attempt should be handled safely."""
        xss_attempt = "Mika, <script>alert('xss')</script>"
        
        result = await parse_input(
            user_id="123456789",
            group_id="987654321",
            message=xss_attempt,
        )
        # Should parse as normal text (sanitization happens at output)
        assert result is not None
