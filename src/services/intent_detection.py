"""
Intent detection service.

This module provides intent classification functionality to detect user intents
from messages for more accurate and contextually appropriate prompt selection.

Per FR-013 Enhancement: System MUST support fine-grained intent classification.
Intent detection uses rule-based keyword matching initially, with optional
LLM-based classification for complex cases. When intent detection fails or is
uncertain, system MUST fallback to use_case-based prompt selection.

This service also supports scenario detection for context-specific prompts,
such as high BPM recommendations, beginner-friendly advice, etc.
"""

import re
from typing import Optional, Tuple

import structlog

from src.services.llm import get_llm_service

logger = structlog.get_logger()


class IntentDetectionService:
    """
    Intent detection service.
    
    Detects user intents from messages using rule-based keyword matching
    and optional LLM-based classification for complex cases.
    """

    def __init__(self) -> None:
        """Initialize intent detection service."""
        # Rule-based keyword patterns for common intents
        # Order matters: more specific patterns should be checked first
        # Patterns are checked in order, and the first match wins
        self._intent_patterns = {
            # Song-related intents (check first - more specific)
            "song_query": [
                r"(?:BPM|bpm|难度|difficulty|节奏|tempo).*?(?:的|of|is|是多少|what)",
                r"(?:歌曲|song).*?(?:的|of).*?(?:BPM|bpm|难度|difficulty)",
                r"(?:what.*?is.*?BPM|what.*?is.*?difficulty|BPM.*?of|difficulty.*?of)",
            ],
            "song_recommendation": [
                r"(?:推荐|recommend|suggest|介绍|introduce).*?(?:歌曲|song|歌)",
                r"(?:有什么.*?歌|what.*?song|哪些.*?歌|推荐.*?歌)",
                r"(?:recommend.*?song|suggest.*?song|推荐.*?歌曲)",
            ],
            "bpm_analysis": [
                r"(?:BPM.*?分析|bpm.*?analysis|速度.*?分析|BPM.*?比较)",
            ],
            "difficulty_advice": [
                r"(?:建议|advice|怎么.*?练|how.*?practice|如何.*?提高).*?(?:难度|difficulty)",
                r"(?:新手|beginner|入门|advanced|高级).*?(?:建议|advice)",
                r"(?:新手|beginner).*?(?:怎么|how).*?(?:开始|start|练习|practice)",
                r"(?:怎么|how).*?(?:开始|start).*?(?:练习|practice)",
            ],
            # Game-related intents
            "game_tips": [
                r"(?:技巧|tips|tricks|怎么.*?打|how.*?play|游戏.*?技巧)",
                r"(?:提高|improve|提升|better).*?(?:技巧|tips|skill)",
                r"(?:how.*?to.*?improve|怎么.*?提高|如何.*?提升)",
                r"(?:improve.*?skill|提高.*?技能|提升.*?水平)",
            ],
            "achievement_celebration": [
                r"(?:完成|complete|达成|achieve|通关|clear).*?(?:恭喜|congrat|庆祝|celebrate)",
                r"(?:恭喜|congrat|庆祝|celebrate).*?(?:完成|complete|达成|achieve)",
            ],
            "practice_advice": [
                r"(?:练习|practice|训练|training|怎么.*?练).*?(?:建议|advice)",
            ],
            # Conversational intents (check after specific intents)
            "greeting": [
                r"(?:你好|hello|hi|hey|早上好|下午好|晚上好|こんにちは)",
                r"(?:mika.*?你好|hello.*?mika)",
            ],
            "help": [
                r"(?:帮助|help|你能做什么|what.*?can.*?you.*?do)",
                r"(?:功能|features|capabilities|你能.*?做什么)",
            ],
            "goodbye": [
                r"(?:再见|bye|goodbye|see.*?you|拜拜|さようなら)",
            ],
            "preference_confirmation": [
                r"(?:是|对|yes|correct|right|没错|对的|正确)",
                r"(?:不是|不对|no|incorrect|wrong|不对)",
            ],
            "clarification_request": [
                # More specific patterns to avoid false positives
                r"(?:什么意思|what.*?mean|哪个.*?意思)",
                r"(?:什么.*?是|what.*?is).*?(?:意思|meaning)",
            ],
        }

        # Scenario patterns for context-specific prompts
        # These help select more specific prompt templates based on context
        self._scenario_patterns = {
            # Song recommendation scenarios
            "song_recommendation_high_bpm": [
                r"(?:高.*?BPM|high.*?bpm|快.*?节奏|fast.*?tempo|高.*?速度)",
                r"(?:快.*?歌|fast.*?song|高.*?bpm.*?推荐)",
            ],
            "song_recommendation_beginner_friendly": [
                r"(?:新手|beginner|入门|简单|easy|初级|初级.*?推荐)",
                r"(?:适合.*?新手|适合.*?beginner|简单.*?歌)",
            ],
            # Difficulty advice scenarios
            "difficulty_advice_beginner": [
                r"(?:新手|beginner|入门|怎么.*?开始|how.*?start)",
                r"(?:第一次|first.*?time|刚开始|just.*?started)",
            ],
            "difficulty_advice_expert": [
                r"(?:高级|expert|大师|master|专业|professional)",
                r"(?:挑战|challenge|困难|difficult|极限|extreme)",
            ],
            # Game tips scenarios
            "game_tips_timing": [
                r"(?:节奏|timing|节拍|beat|打点|hit.*?timing)",
                r"(?:怎么.*?打.*?准|how.*?hit.*?accurate|时机|timing.*?advice)",
            ],
            "game_tips_accuracy": [
                r"(?:准确|accuracy|精确|precision|准度|准确率)",
                r"(?:怎么.*?提高.*?准确|how.*?improve.*?accuracy|减少.*?miss)",
            ],
        }

    async def detect_intent(
        self,
        message: str,
        use_llm: bool = False,
    ) -> Optional[str]:
        """
        Detect user intent from message.
        
        Per FR-013 Enhancement: Uses rule-based keyword matching initially,
        with optional LLM-based classification for complex cases.
        
        Args:
            message: User's message.
            use_llm: If True, use LLM for classification when rule-based fails.
            
        Returns:
            Detected intent string, or None if uncertain.
            
        Example:
            >>> service = IntentDetectionService()
            >>> intent = await service.detect_intent("Mika, 你好！")
            >>> print(intent)
            "greeting"
        """
        message_lower = message.lower()
        
        # Rule-based keyword matching
        intent_scores: dict[str, int] = {}
        
        for intent, patterns in self._intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    score += 1
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            # Return intent with highest score
            # If multiple intents have the same score, prefer more specific ones
            # (song-related and game-related intents are more specific than conversational)
            best_intent = max(intent_scores.items(), key=lambda x: (x[1], x[0] not in ["clarification_request", "help"]))[0]
            # Only return if score is high enough (at least 1 match)
            if intent_scores[best_intent] >= 1:
                logger.debug(
                    "intent_detected",
                    intent=best_intent,
                    score=intent_scores[best_intent],
                    message_preview=message[:50],
                )
                return best_intent
        
        # Rule-based detection failed or uncertain
        if use_llm:
            # Optional LLM-based classification for complex cases
            logger.debug("intent_detection_fallback_llm", message_preview=message[:50])
            return await self._detect_intent_with_llm(message)
        
        # Return None if uncertain (will fallback to use_case-based selection)
        logger.debug("intent_detection_uncertain", message_preview=message[:50])
        return None

    def detect_scenario(
        self,
        message: str,
        intent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Detect scenario from message and intent for context-specific prompts.
        
        Scenarios provide additional context for selecting more specific
        prompt templates (e.g., "song_recommendation_high_bpm").
        
        Args:
            message: User's message.
            intent: Detected intent (optional, helps narrow scenario detection).
            
        Returns:
            Detected scenario string, or None if no specific scenario detected.
            
        Example:
            >>> service = IntentDetectionService()
            >>> scenario = service.detect_scenario(
            ...     "推荐一些高 BPM 的歌曲",
            ...     intent="song_recommendation"
            ... )
            >>> print(scenario)
            "song_recommendation_high_bpm"
        """
        message_lower = message.lower()
        
        # Scenario detection based on message content
        scenario_scores: dict[str, int] = {}
        
        for scenario, patterns in self._scenario_patterns.items():
            # If intent is provided, only check scenarios that match the intent
            if intent:
                # Extract base intent from scenario (e.g., "song_recommendation" from "song_recommendation_high_bpm")
                scenario_base = scenario.split("_")[0] + "_" + scenario.split("_")[1] if "_" in scenario else scenario
                if not intent.startswith(scenario_base.split("_")[0]):
                    continue
            
            score = 0
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    score += 1
            if score > 0:
                scenario_scores[scenario] = score
        
        if scenario_scores:
            # Return scenario with highest score
            best_scenario = max(scenario_scores.items(), key=lambda x: x[1])[0]
            logger.debug(
                "scenario_detected",
                scenario=best_scenario,
                score=scenario_scores[best_scenario],
                intent=intent,
                message_preview=message[:50],
            )
            return best_scenario
        
        return None

    async def detect_intent_and_scenario(
        self,
        message: str,
        use_llm: bool = False,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect both intent and scenario from message.
        
        This is a convenience method that detects both intent and scenario
        in a single call, which is more efficient than calling them separately.
        
        Args:
            message: User's message.
            use_llm: If True, use LLM for intent classification when rule-based fails.
            
        Returns:
            Tuple of (intent, scenario), both can be None.
            
        Example:
            >>> service = IntentDetectionService()
            >>> intent, scenario = await service.detect_intent_and_scenario(
            ...     "推荐一些高 BPM 的歌曲"
            ... )
            >>> print(f"Intent: {intent}, Scenario: {scenario}")
            "Intent: song_recommendation, Scenario: song_recommendation_high_bpm"
        """
        intent = await self.detect_intent(message, use_llm=use_llm)
        scenario = self.detect_scenario(message, intent=intent)
        return intent, scenario

    async def _detect_intent_with_llm(self, message: str) -> Optional[str]:
        """
        Detect intent using LLM for complex/ambiguous cases.
        
        Args:
            message: User's message.
            
        Returns:
            Detected intent string, or None if uncertain.
        """
        try:
            llm_service = get_llm_service()
            
            prompt = f"""Analyze the following user message and classify the intent.

Message: {message}

Intent categories:
- Conversational: greeting, help, goodbye, preference_confirmation, clarification_request
- Song-related: song_query, song_recommendation, difficulty_advice, bpm_analysis
- Game-related: game_tips, achievement_celebration, practice_advice

Respond with ONLY the intent name (e.g., "greeting", "song_query"), or "unknown" if uncertain."""

            response = await llm_service.generate_response(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for classification
                max_tokens=50,
            )
            
            intent = response.strip().lower()
            
            # Validate intent is in our list
            all_intents = list(self._intent_patterns.keys())
            
            if intent in all_intents:
                return intent
            
            return None
        except Exception:
            # LLM classification failed - return None for fallback
            return None


# Global intent detection service instance
_intent_detection_service: Optional[IntentDetectionService] = None


def get_intent_detection_service() -> IntentDetectionService:
    """
    Get global intent detection service instance.
    
    Returns:
        Global IntentDetectionService instance.
    """
    global _intent_detection_service
    
    if _intent_detection_service is None:
        _intent_detection_service = IntentDetectionService()
    
    return _intent_detection_service
