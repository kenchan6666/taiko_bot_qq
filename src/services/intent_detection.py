"""
Intent detection service.

This module provides intent classification functionality to detect user intents
from messages for more accurate and contextually appropriate prompt selection.

Per FR-013 Enhancement: System MUST support fine-grained intent classification.
Intent detection uses rule-based keyword matching initially, with optional
LLM-based classification for complex cases. When intent detection fails or is
uncertain, system MUST fallback to use_case-based prompt selection.
"""

import re
from typing import Optional

from src.services.llm import get_llm_service


class IntentDetectionService:
    """
    Intent detection service.
    
    Detects user intents from messages using rule-based keyword matching
    and optional LLM-based classification for complex cases.
    """

    def __init__(self) -> None:
        """Initialize intent detection service."""
        # Rule-based keyword patterns for common intents
        self._intent_patterns = {
            # Conversational intents
            "greeting": [
                r"(?:你好|hello|hi|hey|早上好|下午好|晚上好|こんにちは)",
                r"(?:mika.*?你好|hello.*?mika)",
            ],
            "help": [
                r"(?:帮助|help|怎么|如何|what.*?can.*?you.*?do|你能做什么)",
                r"(?:功能|features|capabilities)",
            ],
            "goodbye": [
                r"(?:再见|bye|goodbye|see.*?you|拜拜|さようなら)",
            ],
            "preference_confirmation": [
                r"(?:是|对|yes|correct|right|没错|对的|正确)",
                r"(?:不是|不对|no|incorrect|wrong|不对)",
            ],
            "clarification_request": [
                r"(?:什么|what|哪个|which|什么意思|what.*?mean)",
            ],
            # Song-related intents
            "song_query": [
                r"(?:歌曲|song|BPM|bpm|难度|difficulty|节奏|tempo)",
                r"(?:的.*?BPM|的.*?难度|.*?song.*?info)",
            ],
            "song_recommendation": [
                r"(?:推荐|recommend|suggest|介绍|introduce)",
                r"(?:有什么.*?歌|what.*?song|哪些.*?歌)",
            ],
            "difficulty_advice": [
                r"(?:建议|advice|怎么.*?练|how.*?practice|如何.*?提高)",
                r"(?:新手|beginner|入门|advanced|高级)",
            ],
            "bpm_analysis": [
                r"(?:BPM.*?分析|bpm.*?analysis|速度.*?分析)",
            ],
            # Game-related intents
            "game_tips": [
                r"(?:技巧|tips|tricks|怎么.*?打|how.*?play)",
                r"(?:提高|improve|提升|better)",
            ],
            "achievement_celebration": [
                r"(?:完成|complete|达成|achieve|通关|clear)",
                r"(?:恭喜|congrat|庆祝|celebrate)",
            ],
            "practice_advice": [
                r"(?:练习|practice|训练|training|怎么.*?练)",
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
            best_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
            # Only return if score is high enough (at least 1 match)
            if intent_scores[best_intent] >= 1:
                return best_intent
        
        # Rule-based detection failed or uncertain
        if use_llm:
            # Optional LLM-based classification for complex cases
            return self._detect_intent_with_llm(message)
        
        # Return None if uncertain (will fallback to use_case-based selection)
        return None

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
