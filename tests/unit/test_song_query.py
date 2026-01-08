"""
Unit tests for song_query.py service.

Tests taikowiki integration, caching, and fuzzy matching functionality.

Per T040: Create tests/unit/test_song_query.py with taikowiki
integration tests (mocked).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.services.song_query import (
    SongQueryService,
    get_song_service,
    initialize_song_cache,
)
from tests.fixtures.mock_taikowiki import (
    get_mock_taikowiki_response,
    get_mock_taikowiki_response_dict,
    get_mock_taikowiki_json_string,
)
from tests.fixtures.mock_songs import SAMPLE_SONGS, get_mock_song


class TestSongQueryServiceFetchSongs:
    """Test fetching songs from taikowiki."""

    @pytest.mark.asyncio
    async def test_fetch_songs_list_format(self) -> None:
        """Test fetching songs when taikowiki returns list format."""
        mock_response = MagicMock()
        mock_response.json.return_value = get_mock_taikowiki_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            service = SongQueryService(json_url="https://test.example.com/songs.json")
            songs = await service.fetch_songs()

        assert len(songs) == len(SAMPLE_SONGS)
        assert songs[0]["name"] == "千本桜"
        assert songs[0]["bpm"] == 200

    @pytest.mark.asyncio
    async def test_fetch_songs_dict_format(self) -> None:
        """Test fetching songs when taikowiki returns dict with 'songs' key."""
        mock_response = MagicMock()
        mock_response.json.return_value = get_mock_taikowiki_response_dict()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            service = SongQueryService(json_url="https://test.example.com/songs.json")
            songs = await service.fetch_songs()

        assert len(songs) == len(SAMPLE_SONGS)
        assert songs[0]["name"] == "千本桜"

    @pytest.mark.asyncio
    async def test_fetch_songs_http_error(self) -> None:
        """Test handling HTTP errors from taikowiki."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock()
        )

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            service = SongQueryService(json_url="https://test.example.com/songs.json")
            with pytest.raises(RuntimeError, match="Failed to fetch songs"):
                await service.fetch_songs()

    @pytest.mark.asyncio
    async def test_fetch_songs_invalid_json(self) -> None:
        """Test handling invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            service = SongQueryService(json_url="https://test.example.com/songs.json")
            with pytest.raises(ValueError, match="Invalid JSON response"):
                await service.fetch_songs()


class TestSongQueryServiceCaching:
    """Test song cache management."""

    @pytest.mark.asyncio
    async def test_refresh_cache(self) -> None:
        """Test refreshing song cache."""
        # Reset global cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = []
        song_query_module._cache_timestamp = None

        mock_response = MagicMock()
        mock_response.json.return_value = get_mock_taikowiki_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            service = SongQueryService(json_url="https://test.example.com/songs.json")
            await service.refresh_cache()

        assert len(song_query_module._songs_cache) == len(SAMPLE_SONGS)
        assert song_query_module._cache_timestamp is not None

    def test_is_cache_stale_empty_cache(self) -> None:
        """Test that empty cache is considered stale."""
        # Reset global cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = []
        song_query_module._cache_timestamp = None

        service = SongQueryService()
        assert service.is_cache_stale() is True

    def test_is_cache_stale_fresh_cache(self) -> None:
        """Test that fresh cache is not stale."""
        # Set up fresh cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = SAMPLE_SONGS.copy()
        song_query_module._cache_timestamp = datetime.utcnow()

        service = SongQueryService()
        assert service.is_cache_stale() is False

    def test_is_cache_stale_old_cache(self) -> None:
        """Test that old cache (older than 1 hour) is stale."""
        # Set up old cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = SAMPLE_SONGS.copy()
        song_query_module._cache_timestamp = datetime.utcnow() - timedelta(hours=2)

        service = SongQueryService()
        assert service.is_cache_stale() is True

    @pytest.mark.asyncio
    async def test_ensure_cache_fresh_refreshes_stale(self) -> None:
        """Test that ensure_cache_fresh refreshes stale cache."""
        # Set up stale cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = []
        song_query_module._cache_timestamp = None

        mock_response = MagicMock()
        mock_response.json.return_value = get_mock_taikowiki_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            service = SongQueryService(json_url="https://test.example.com/songs.json")
            await service.ensure_cache_fresh()

        assert len(song_query_module._songs_cache) > 0


class TestSongQueryServiceFuzzyMatching:
    """Test fuzzy matching functionality."""

    def test_query_song_exact_match(self) -> None:
        """Test querying song with exact name match."""
        # Set up cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = SAMPLE_SONGS.copy()

        service = SongQueryService()
        result = service.query_song("千本桜", threshold=0.7)

        assert result is not None
        assert result["name"] == "千本桜"
        assert result["bpm"] == 200

    def test_query_song_fuzzy_match(self) -> None:
        """Test querying song with fuzzy matching (partial name)."""
        # Set up cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = SAMPLE_SONGS.copy()

        service = SongQueryService()
        # "千本" should match "千本桜" with high similarity
        result = service.query_song("千本", threshold=0.5)

        assert result is not None
        assert result["name"] == "千本桜"

    def test_query_song_no_match(self) -> None:
        """Test querying non-existent song returns None."""
        # Set up cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = SAMPLE_SONGS.copy()

        service = SongQueryService()
        result = service.query_song("NonExistentSong12345", threshold=0.7)

        assert result is None

    def test_query_song_empty_cache(self) -> None:
        """Test querying when cache is empty returns None."""
        # Set up empty cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = []

        service = SongQueryService()
        result = service.query_song("千本桜", threshold=0.7)

        assert result is None

    def test_query_song_threshold_filtering(self) -> None:
        """Test that threshold filters out low-similarity matches."""
        # Set up cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = SAMPLE_SONGS.copy()

        service = SongQueryService()
        # Very low similarity query with high threshold should return None
        result = service.query_song("XYZ123", threshold=0.9)

        assert result is None


class TestSongQueryServiceGlobal:
    """Test global service instance and initialization."""

    def test_get_song_service_returns_singleton(self) -> None:
        """Test that get_song_service returns the same instance."""
        service1 = get_song_service()
        service2 = get_song_service()

        assert service1 is service2

    @pytest.mark.asyncio
    async def test_initialize_song_cache(self) -> None:
        """Test initializing song cache at startup."""
        # Reset global cache
        import src.services.song_query as song_query_module
        song_query_module._songs_cache = []
        song_query_module._cache_timestamp = None

        mock_response = MagicMock()
        mock_response.json.return_value = get_mock_taikowiki_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await initialize_song_cache()

        assert len(song_query_module._songs_cache) == len(SAMPLE_SONGS)
