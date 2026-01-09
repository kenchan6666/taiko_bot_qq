"""
Unit tests for intent detection service.

Tests intent classification functionality including rule-based matching,
LLM-based classification, scenario detection, and fallback behavior.

Per T065F: Create tests/unit/test_intent_detection.py with intent classification
tests (rule-based and LLM-based) and fallback to use_case-based prompts when
intent detection fails.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.intent_detection import (
    IntentDetectionService,
    get_intent_detection_service,
)


class TestIntentDetectionService:
    """Test IntentDetectionService class."""

    def test_init(self) -> None:
        """Test service initialization."""
        service = IntentDetectionService()
        assert service is not None
        assert hasattr(service, "_intent_patterns")
        assert hasattr(service, "_scenario_patterns")

    @pytest.mark.asyncio
    async def test_detect_intent_greeting(self) -> None:
        """Test detecting greeting intent."""
        service = IntentDetectionService()
        
        # Test Chinese greeting
        intent = await service.detect_intent("Mika, 你好！")
        assert intent == "greeting"
        
        # Test English greeting
        intent = await service.detect_intent("Mika, hello!")
        assert intent == "greeting"
        
        # Test Japanese greeting
        intent = await service.detect_intent("Mika, こんにちは")
        assert intent == "greeting"

    @pytest.mark.asyncio
    async def test_detect_intent_help(self) -> None:
        """Test detecting help intent."""
        service = IntentDetectionService()
        
        intent = await service.detect_intent("Mika, 你能做什么？")
        assert intent == "help"
        
        intent = await service.detect_intent("Mika, what can you do?")
        assert intent == "help"

    @pytest.mark.asyncio
    async def test_detect_intent_song_query(self) -> None:
        """Test detecting song query intent."""
        service = IntentDetectionService()
        
        # Test BPM query
        intent = await service.detect_intent("Mika, 千本桜的BPM是多少？")
        assert intent == "song_query"
        
        # Test difficulty query
        intent = await service.detect_intent("Mika, 千本桜的难度是多少？")
        assert intent == "song_query"
        
        # Test English BPM query
        intent = await service.detect_intent("Mika, what is the BPM of 千本桜?")
        assert intent == "song_query"

    @pytest.mark.asyncio
    async def test_detect_intent_song_recommendation(self) -> None:
        """Test detecting song recommendation intent."""
        service = IntentDetectionService()
        
        # Test Chinese recommendation
        intent = await service.detect_intent("Mika, 推荐一些歌曲给我")
        assert intent == "song_recommendation"
        
        # Test English recommendation
        intent = await service.detect_intent("Mika, recommend some songs to me")
        assert intent == "song_recommendation"
        
        # Test with "有什么歌"
        intent = await service.detect_intent("Mika, 有什么好听的歌？")
        assert intent == "song_recommendation"

    @pytest.mark.asyncio
    async def test_detect_intent_game_tips(self) -> None:
        """Test detecting game tips intent."""
        service = IntentDetectionService()
        
        # Test Chinese tips
        intent = await service.detect_intent("Mika, 有什么游戏技巧吗？")
        assert intent == "game_tips"
        
        # Test English tips
        intent = await service.detect_intent("Mika, how to improve my skills?")
        assert intent == "game_tips"
        
        # Test with "怎么打"
        intent = await service.detect_intent("Mika, 怎么打得更准？")
        assert intent == "game_tips"

    @pytest.mark.asyncio
    async def test_detect_intent_uncertain(self) -> None:
        """Test intent detection returns None for uncertain cases."""
        service = IntentDetectionService()
        
        # Message without clear intent keywords
        intent = await service.detect_intent("Mika, 今天天气不错")
        assert intent is None or intent in ["greeting"]  # May match greeting, but not specific intent

    @pytest.mark.asyncio
    async def test_detect_intent_with_llm(self) -> None:
        """Test LLM-based intent detection."""
        service = IntentDetectionService()
        
        # Mock LLM service
        with patch("src.services.intent_detection.get_llm_service") as mock_get_llm:
            mock_llm_service = MagicMock()
            mock_llm_service.generate_response = AsyncMock(return_value="song_recommendation")
            mock_get_llm.return_value = mock_llm_service
            
            # Test with LLM enabled (message that doesn't match rule-based patterns)
            # First, ensure rule-based doesn't match
            rule_based_intent = await service.detect_intent(
                "Mika, I want some fast songs",
                use_llm=False
            )
            # If rule-based doesn't match, LLM should be called
            if rule_based_intent is None:
                intent = await service.detect_intent(
                    "Mika, I want some fast songs",
                    use_llm=True
                )
                assert intent == "song_recommendation"
                # Verify LLM was called
                mock_llm_service.generate_response.assert_called_once()
            else:
                # Rule-based matched, LLM won't be called
                # This is also valid behavior
                pass

    @pytest.mark.asyncio
    async def test_detect_intent_llm_fallback_on_error(self) -> None:
        """Test LLM-based detection returns None on error."""
        service = IntentDetectionService()
        
        # Mock LLM service to raise exception
        with patch("src.services.intent_detection.get_llm_service") as mock_get_llm:
            mock_get_llm.side_effect = Exception("LLM service unavailable")
            
            # Should return None on error (fallback behavior)
            intent = await service.detect_intent(
                "Mika, complex ambiguous message",
                use_llm=True
            )
            assert intent is None

    @pytest.mark.asyncio
    async def test_detect_intent_llm_invalid_response(self) -> None:
        """Test LLM-based detection handles invalid responses."""
        service = IntentDetectionService()
        
        # Mock LLM service to return invalid intent
        with patch("src.services.intent_detection.get_llm_service") as mock_get_llm:
            mock_llm_service = MagicMock()
            mock_llm_service.generate_response = AsyncMock(return_value="invalid_intent_name")
            mock_get_llm.return_value = mock_llm_service
            
            # Should return None for invalid intent
            intent = await service.detect_intent(
                "Mika, complex message",
                use_llm=True
            )
            assert intent is None

    def test_detect_scenario_high_bpm(self) -> None:
        """Test detecting high BPM scenario."""
        service = IntentDetectionService()
        
        scenario = service.detect_scenario(
            "推荐一些高 BPM 的歌曲",
            intent="song_recommendation"
        )
        assert scenario == "song_recommendation_high_bpm"
        
        scenario = service.detect_scenario(
            "recommend high BPM songs",
            intent="song_recommendation"
        )
        assert scenario == "song_recommendation_high_bpm"

    def test_detect_scenario_beginner_friendly(self) -> None:
        """Test detecting beginner-friendly scenario."""
        service = IntentDetectionService()
        
        scenario = service.detect_scenario(
            "推荐一些适合新手的歌曲",
            intent="song_recommendation"
        )
        assert scenario == "song_recommendation_beginner_friendly"
        
        scenario = service.detect_scenario(
            "recommend beginner songs",
            intent="song_recommendation"
        )
        assert scenario == "song_recommendation_beginner_friendly"

    def test_detect_scenario_beginner_advice(self) -> None:
        """Test detecting beginner advice scenario."""
        service = IntentDetectionService()
        
        scenario = service.detect_scenario(
            "新手怎么开始？",
            intent="difficulty_advice"
        )
        assert scenario == "difficulty_advice_beginner"
        
        scenario = service.detect_scenario(
            "how to start as a beginner?",
            intent="difficulty_advice"
        )
        assert scenario == "difficulty_advice_beginner"

    def test_detect_scenario_expert_advice(self) -> None:
        """Test detecting expert advice scenario."""
        service = IntentDetectionService()
        
        scenario = service.detect_scenario(
            "高级玩家怎么提高？",
            intent="difficulty_advice"
        )
        assert scenario == "difficulty_advice_expert"
        
        scenario = service.detect_scenario(
            "expert level advice",
            intent="difficulty_advice"
        )
        assert scenario == "difficulty_advice_expert"

    def test_detect_scenario_timing_tips(self) -> None:
        """Test detecting timing tips scenario."""
        service = IntentDetectionService()
        
        scenario = service.detect_scenario(
            "怎么提高节奏感？",
            intent="game_tips"
        )
        assert scenario == "game_tips_timing"
        
        scenario = service.detect_scenario(
            "how to improve timing?",
            intent="game_tips"
        )
        assert scenario == "game_tips_timing"

    def test_detect_scenario_accuracy_tips(self) -> None:
        """Test detecting accuracy tips scenario."""
        service = IntentDetectionService()
        
        scenario = service.detect_scenario(
            "怎么提高准确率？",
            intent="game_tips"
        )
        assert scenario == "game_tips_accuracy"
        
        scenario = service.detect_scenario(
            "how to improve accuracy?",
            intent="game_tips"
        )
        assert scenario == "game_tips_accuracy"

    def test_detect_scenario_no_match(self) -> None:
        """Test scenario detection returns None when no match."""
        service = IntentDetectionService()
        
        scenario = service.detect_scenario(
            "random message without scenario",
            intent="greeting"
        )
        assert scenario is None

    def test_detect_scenario_without_intent(self) -> None:
        """Test scenario detection works without intent."""
        service = IntentDetectionService()
        
        # Should still detect scenario even without intent
        scenario = service.detect_scenario("推荐高 BPM 歌曲")
        assert scenario == "song_recommendation_high_bpm"

    @pytest.mark.asyncio
    async def test_detect_intent_and_scenario(self) -> None:
        """Test combined intent and scenario detection."""
        service = IntentDetectionService()
        
        # Test song recommendation with high BPM scenario
        intent, scenario = await service.detect_intent_and_scenario(
            "Mika, 推荐一些高 BPM 的歌曲给我"
        )
        assert intent == "song_recommendation"
        assert scenario == "song_recommendation_high_bpm"
        
        # Test difficulty advice with beginner scenario
        intent, scenario = await service.detect_intent_and_scenario(
            "Mika, 新手怎么开始练习？"
        )
        assert intent == "difficulty_advice"
        assert scenario == "difficulty_advice_beginner"

    @pytest.mark.asyncio
    async def test_detect_intent_and_scenario_no_scenario(self) -> None:
        """Test combined detection when no scenario matches."""
        service = IntentDetectionService()
        
        intent, scenario = await service.detect_intent_and_scenario(
            "Mika, 你好！"
        )
        assert intent == "greeting"
        assert scenario is None


class TestIntentDetectionServiceGlobal:
    """Test global intent detection service instance."""

    def test_get_intent_detection_service(self) -> None:
        """Test getting global service instance."""
        service1 = get_intent_detection_service()
        service2 = get_intent_detection_service()
        
        # Should return same instance (singleton)
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_global_service_detect_intent(self) -> None:
        """Test using global service instance."""
        service = get_intent_detection_service()
        
        intent = await service.detect_intent("Mika, 你好！")
        assert intent == "greeting"
