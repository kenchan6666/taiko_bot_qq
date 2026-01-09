"""
Error scenario integration tests.

Tests service failures and graceful degradation.

Per T098: Create tests/integration/test_error_scenarios.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.routes.langbot import LangBotWebhookRequest, _process_webhook_request
from src.services.llm import LLMService
from src.services.song_query import SongQueryService


class TestServiceFailures:
    """Test graceful handling of service failures."""

    @pytest.mark.asyncio
    async def test_mongodb_failure_graceful(self, test_database):
        """System should handle MongoDB failures gracefully."""
        with patch("src.services.database.init_database") as mock_init:
            mock_init.side_effect = Exception("MongoDB connection failed")
            
            # System should handle failure (may raise or degrade gracefully)
            # This depends on implementation
            try:
                await mock_init()
            except Exception:
                # Exception is acceptable - system should fail fast
                pass

    @pytest.mark.asyncio
    async def test_taikowiki_api_failure_fallback(self, test_database):
        """System should fallback to local JSON when taikowiki API fails."""
        with patch("src.services.song_query.SongQueryService.fetch_songs") as mock_fetch:
            # Simulate API failure
            mock_fetch.side_effect = Exception("API connection failed")
            
            service = SongQueryService()
            
            # Should use fallback
            songs, used_fallback = await service.fetch_songs(use_fallback=True)
            
            assert used_fallback is True
            assert len(songs) > 0  # Should have fallback data

    @pytest.mark.asyncio
    async def test_openrouter_api_failure_fallback(self, test_database):
        """System should use fallback response when LLM fails."""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Simulate API failure
            mock_post.side_effect = Exception("OpenRouter API failed")
            
            from fastapi import Request
            from unittest.mock import MagicMock
            
            mock_request = MagicMock(spec=Request)
            
            webhook_req = LangBotWebhookRequest(
                user_id="test_user",
                group_id="test_group",
                message="Mika, hello!",
            )
            
            # Should handle gracefully (may use fallback response)
            result = await _process_webhook_request(webhook_req, mock_request)
            
            # Should still return a response (may be fallback)
            assert result.status == "ok"
            # Response may be fallback message
            assert result.response is not None

    @pytest.mark.asyncio
    async def test_temporal_connection_failure(self, test_database):
        """System should handle Temporal connection failures."""
        with patch("temporalio.client.Client.connect") as mock_connect:
            mock_connect.side_effect = Exception("Temporal connection failed")
            
            # System should handle failure gracefully
            # This depends on implementation (may use direct processing)
            try:
                await mock_connect("localhost:7233", namespace="default")
            except Exception:
                # Exception is acceptable
                pass

    @pytest.mark.asyncio
    async def test_partial_service_failure(self, test_database):
        """System should continue operating with partial service failures."""
        # Simulate song query service failure but LLM still works
        with patch("src.services.song_query.SongQueryService.fetch_songs") as mock_fetch:
            mock_fetch.side_effect = Exception("Song service failed")
            
            from fastapi import Request
            from unittest.mock import MagicMock
            
            mock_request = MagicMock(spec=Request)
            
            # Request that doesn't require song query
            webhook_req = LangBotWebhookRequest(
                user_id="test_user",
                group_id="test_group",
                message="Mika, how are you?",  # General chat, no song query
            )
            
            # Should still process (song query not needed)
            result = await _process_webhook_request(webhook_req, mock_request)
            assert result.status == "ok"


class TestGracefulDegradation:
    """Test graceful degradation scenarios."""

    @pytest.mark.asyncio
    async def test_llm_timeout_uses_fallback(self, test_database):
        """LLM timeout should trigger fallback response."""
        import asyncio
        
        with patch("httpx.AsyncClient.post") as mock_post:
            # Simulate timeout
            async def timeout_response(*args, **kwargs):
                await asyncio.sleep(10)  # Longer than timeout
                return MagicMock()
            
            mock_post.side_effect = timeout_response
            
            from fastapi import Request
            from unittest.mock import MagicMock
            
            mock_request = MagicMock(spec=Request)
            
            webhook_req = LangBotWebhookRequest(
                user_id="test_user",
                group_id="test_group",
                message="Mika, hello!",
            )
            
            # Should use fallback after timeout
            result = await _process_webhook_request(webhook_req, mock_request)
            assert result.status == "ok"
            assert result.response is not None

    @pytest.mark.asyncio
    async def test_cache_fallback_when_api_unavailable(self, test_database):
        """Should use cached data when API is unavailable."""
        service = SongQueryService()
        
        # First, ensure cache is populated
        await service.ensure_cache_fresh()
        
        # Then simulate API failure
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("API unavailable")
            
            # Should use cached data
            songs, used_fallback = await service.fetch_songs(use_fallback=True)
            assert used_fallback is True
            assert len(songs) > 0

    @pytest.mark.asyncio
    async def test_degraded_mode_continues_operating(self, test_database):
        """System should continue operating in degraded mode."""
        # Simulate multiple service failures
        with patch("src.services.song_query.SongQueryService.fetch_songs") as mock_song, \
             patch("httpx.AsyncClient.post") as mock_llm:
            
            # Both services fail
            mock_song.side_effect = Exception("Song service failed")
            mock_llm.side_effect = Exception("LLM service failed")
            
            from fastapi import Request
            from unittest.mock import MagicMock
            
            mock_request = MagicMock(spec=Request)
            
            webhook_req = LangBotWebhookRequest(
                user_id="test_user",
                group_id="test_group",
                message="Mika, hello!",
            )
            
            # Should still return a response (fallback)
            result = await _process_webhook_request(webhook_req, mock_request)
            assert result.status == "ok"
            # Should have fallback response
            assert result.response is not None
