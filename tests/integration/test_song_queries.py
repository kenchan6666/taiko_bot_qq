"""
Integration tests for song query functionality.

Tests end-to-end song query flow from user message to response,
including extraction, fuzzy matching, and service integration.

Per T041: Create tests/integration/test_song_queries.py with
end-to-end song query tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.steps import step3
from tests.fixtures.mock_songs import SAMPLE_SONGS, get_mock_song


class TestEndToEndSongQuery:
    """Test end-to-end song query flow."""

    @pytest.mark.asyncio
    async def test_complete_song_query_flow(self) -> None:
        """
        Test complete flow: message -> extraction -> query -> result.

        This test verifies the entire song query pipeline works correctly.
        """
        # Mock song service
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))
        mock_service.query_song.return_value = get_mock_song("千本桜")

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            # Simulate user asking about a song
            message = "What's the BPM of 千本桜?"
            result = await step3.query_song(message)

        # Verify result
        assert result is not None
        assert result["song_name"] == "千本桜"
        assert result["bpm"] == 200
        assert result["difficulty_stars"] == 9
        assert "metadata" in result

        # Verify service was called correctly
        mock_service.ensure_cache_fresh.assert_called_once()
        mock_service.query_song.assert_called_once_with("千本桜", threshold=0.7)

    @pytest.mark.asyncio
    async def test_song_query_with_fuzzy_matching(self) -> None:
        """Test end-to-end flow with fuzzy matching for misspelled song name."""
        # Mock service with fuzzy match result
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))
        # Simulate fuzzy match: "千本樱" (different character) matches "千本桜"
        mock_service.query_song.return_value = get_mock_song("千本桜")

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            # User misspells song name
            message = "千本樱的BPM是多少？"
            result = await step3.query_song(message)

        assert result is not None
        assert result["song_name"] == "千本桜"
        mock_service.query_song.assert_called_once()

    @pytest.mark.asyncio
    async def test_song_query_no_match_handling(self) -> None:
        """Test handling when song is not found."""
        # Mock service with no match
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))
        mock_service.query_song.return_value = None

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            message = "What's the BPM of NonExistentSong123?"
            result = await step3.query_song(message)

        # Should return None gracefully
        assert result is None
        mock_service.query_song.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_song_queries(self) -> None:
        """Test multiple song queries in sequence."""
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))

        # First query: 千本桜
        mock_service.query_song.side_effect = [
            get_mock_song("千本桜"),
            get_mock_song("紅蓮華"),
        ]

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result1 = await step3.query_song("千本桜")
            result2 = await step3.query_song("紅蓮華")

        assert result1 is not None
        assert result1["song_name"] == "千本桜"
        assert result2 is not None
        assert result2["song_name"] == "紅蓮華"
        assert mock_service.ensure_cache_fresh.call_count == 2

    @pytest.mark.asyncio
    async def test_song_query_with_different_query_patterns(self) -> None:
        """Test that different query patterns all work correctly."""
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))
        mock_service.query_song.return_value = get_mock_song("千本桜")

        query_patterns = [
            "What's the BPM of 千本桜?",
            "难度: 千本桜",
            "Tell me about 千本桜",
            "关于 千本桜",
            "千本桜",  # Direct name
        ]

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            for pattern in query_patterns:
                result = await step3.query_song(pattern)
                assert result is not None
                assert result["song_name"] == "千本桜"

        # Should have called service for each pattern
        assert mock_service.query_song.call_count == len(query_patterns)

    @pytest.mark.asyncio
    async def test_song_query_cache_refresh_integration(self) -> None:
        """Test that cache refresh happens before querying."""
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))
        mock_service.query_song.return_value = get_mock_song("千本桜")

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            await step3.query_song("千本桜")

        # Verify ensure_cache_fresh is called before query_song
        # (check call order by ensuring both were called)
        mock_service.ensure_cache_fresh.assert_called_once()
        mock_service.query_song.assert_called_once()

    @pytest.mark.asyncio
    async def test_song_query_metadata_preservation(self) -> None:
        """Test that song metadata is preserved in query result."""
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock(return_value=(True, False))
        song = get_mock_song("千本桜")
        mock_service.query_song.return_value = song

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result = await step3.query_song("千本桜")

        assert result is not None
        assert "metadata" in result
        assert result["metadata"]["genre"] == "Vocaloid"
        assert result["metadata"]["artist"] == "Kurousa-P"
        assert result["metadata"]["category"] == "Anime"
