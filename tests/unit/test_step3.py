"""
Unit tests for step3.py (song query functionality).

Tests song query extraction, fuzzy matching, and integration
with song_query service.

Per T039: Create tests/unit/test_step3.py with song query and
fuzzy matching tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.steps import step3
from tests.fixtures.mock_songs import SAMPLE_SONGS, get_mock_song


class TestExtractSongQuery:
    """Test song query extraction from user messages."""

    def test_extract_bpm_query(self) -> None:
        """Test extracting song name from BPM query."""
        message = "What's the BPM of 千本桜?"
        result = step3.extract_song_query(message)
        assert result == "千本桜"

    def test_extract_difficulty_query(self) -> None:
        """Test extracting song name from difficulty query."""
        message = "难度: 紅蓮華"
        result = step3.extract_song_query(message)
        assert result == "紅蓮華"

    def test_extract_about_query(self) -> None:
        """Test extracting song name from 'about' query."""
        message = "Tell me about Bad Apple!!"
        result = step3.extract_song_query(message)
        assert result == "Bad Apple!!"

    def test_extract_chinese_about_query(self) -> None:
        """Test extracting song name from Chinese 'about' query."""
        message = "关于 千本桜"
        result = step3.extract_song_query(message)
        assert result == "千本桜"

    def test_extract_direct_song_name(self) -> None:
        """Test extracting direct song name (short message)."""
        message = "千本桜"
        result = step3.extract_song_query(message)
        assert result == "千本桜"

    def test_no_song_query_detected(self) -> None:
        """Test that non-song queries return None."""
        message = "Hello, how are you?"
        result = step3.extract_song_query(message)
        assert result is None

    def test_empty_message(self) -> None:
        """Test that empty message returns None."""
        result = step3.extract_song_query("")
        assert result is None

    def test_long_message_without_query(self) -> None:
        """Test that long messages without query patterns return None."""
        message = "This is a very long message that doesn't contain any song query patterns at all"
        result = step3.extract_song_query(message)
        assert result is None


class TestQuerySong:
    """Test song query with fuzzy matching."""

    @pytest.mark.asyncio
    async def test_query_exact_match(self) -> None:
        """Test querying song with exact name match."""
        # Mock song service
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock()
        mock_service.query_song.return_value = get_mock_song("千本桜")

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result = await step3.query_song("What's the BPM of 千本桜?")

        assert result is not None
        assert result["song_name"] == "千本桜"
        assert result["bpm"] == 200
        assert result["difficulty_stars"] == 9
        mock_service.ensure_cache_fresh.assert_called_once()
        mock_service.query_song.assert_called_once_with("千本桜", threshold=0.7)

    @pytest.mark.asyncio
    async def test_query_fuzzy_match(self) -> None:
        """Test querying song with fuzzy matching (misspelled name)."""
        # Mock song service with fuzzy match
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock()
        # Simulate fuzzy match: "千本桜" matched from "千本樱" (different character)
        mock_service.query_song.return_value = get_mock_song("千本桜")

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result = await step3.query_song("千本樱")  # Misspelled

        assert result is not None
        assert result["song_name"] == "千本桜"
        mock_service.query_song.assert_called_once_with("千本樱", threshold=0.7)

    @pytest.mark.asyncio
    async def test_query_no_match(self) -> None:
        """Test querying non-existent song returns None."""
        # Mock song service with no match
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock()
        mock_service.query_song.return_value = None

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result = await step3.query_song("Non-existent Song 12345")

        assert result is None
        mock_service.query_song.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_no_song_detected(self) -> None:
        """Test that messages without song queries return None."""
        # Mock service (should not be called)
        mock_service = MagicMock()

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result = await step3.query_song("Hello, how are you?")

        assert result is None
        mock_service.ensure_cache_fresh.assert_not_called()
        mock_service.query_song.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_ensures_cache_fresh(self) -> None:
        """Test that query_song ensures cache is fresh before querying."""
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock()
        mock_service.query_song.return_value = get_mock_song("千本桜")

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            await step3.query_song("千本桜")

        # Verify cache refresh is called before query
        mock_service.ensure_cache_fresh.assert_called_once()
        mock_service.query_song.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_returns_metadata(self) -> None:
        """Test that query result includes metadata."""
        mock_service = MagicMock()
        mock_service.ensure_cache_fresh = AsyncMock()
        song = get_mock_song("千本桜")
        mock_service.query_song.return_value = song

        with patch("src.steps.step3.get_song_service", return_value=mock_service):
            result = await step3.query_song("千本桜")

        assert result is not None
        assert "metadata" in result
        assert result["metadata"]["genre"] == "Vocaloid"
        assert result["metadata"]["artist"] == "Kurousa-P"
