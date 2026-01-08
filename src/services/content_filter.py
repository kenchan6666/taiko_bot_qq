"""
Content filtering service.

This module implements hybrid content filtering using keyword/phrase lists
for fast pre-filtering, followed by LLM judgment for ambiguous cases.

Per FR-007: System MUST filter out harmful or inappropriate content.
Content filtering MUST use a hybrid approach: keyword/phrase lists for
fast pre-filtering of obviously inappropriate content, then use LLM
judgment for ambiguous cases.
"""

from typing import Optional

from src.config import settings


class ContentFilter:
    """
    Content filter for detecting harmful or inappropriate content.

    Uses hybrid approach:
    1. Keyword/phrase lists for fast pre-filtering
    2. LLM judgment for ambiguous cases (future implementation)

    Per FR-007: Filter excessive hatred (including ethnic hatred),
    political topics, and religious content. Allow normal game-related
    discussions while blocking divisive or inflammatory content.
    """

    def __init__(self) -> None:
        """Initialize content filter with keyword lists."""
        # Chinese keyword lists for fast filtering
        self._chinese_keywords_hatred: set[str] = {
            # Ethnic hatred keywords (examples - should be comprehensive)
            "民族仇恨",
            "种族歧视",
            # Add more as needed
        }

        self._chinese_keywords_politics: set[str] = {
            # Political keywords (examples - should be comprehensive)
            "政治",
            "政府",
            "政党",
            # Add more as needed
        }

        self._chinese_keywords_religion: set[str] = {
            # Religious keywords (examples - should be comprehensive)
            "宗教",
            "信仰",
            # Add more as needed
        }

        # English keyword lists
        self._english_keywords_hatred: set[str] = {
            # Ethnic hatred keywords
            "ethnic hatred",
            "racial discrimination",
            # Add more as needed
        }

        self._english_keywords_politics: set[str] = {
            # Political keywords
            "politics",
            "government",
            "political party",
            # Add more as needed
        }

        self._english_keywords_religion: set[str] = {
            # Religious keywords
            "religion",
            "faith",
            # Add more as needed
        }

    def is_harmful(self, text: str, language: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Check if text contains harmful or inappropriate content.

        Uses keyword-based filtering for fast detection. Returns tuple
        of (is_harmful, reason) where reason explains why content is harmful.

        Args:
            text: Text to check.
            language: Language code ("zh", "en", or None for auto-detect).

        Returns:
            Tuple of (is_harmful: bool, reason: Optional[str]).
            If harmful, reason contains explanation (e.g., "contains hatred keywords").
        """
        if not settings.content_filter_enabled:
            return False, None

        if not text or not text.strip():
            return False, None

        text_lower = text.lower()

        # Determine which keyword sets to use
        if language == "zh" or (language is None and self._is_chinese_text(text)):
            # Check Chinese keywords
            if self._contains_keywords(text_lower, self._chinese_keywords_hatred):
                return True, "contains hatred keywords"
            if self._contains_keywords(text_lower, self._chinese_keywords_politics):
                return True, "contains political keywords"
            if self._contains_keywords(text_lower, self._chinese_keywords_religion):
                return True, "contains religious keywords"
        else:
            # Check English keywords
            if self._contains_keywords(text_lower, self._english_keywords_hatred):
                return True, "contains hatred keywords"
            if self._contains_keywords(text_lower, self._english_keywords_politics):
                return True, "contains political keywords"
            if self._contains_keywords(text_lower, self._english_keywords_religion):
                return True, "contains religious keywords"

        # No harmful content detected
        return False, None

    def _contains_keywords(self, text: str, keywords: set[str]) -> bool:
        """
        Check if text contains any of the given keywords.

        Args:
            text: Text to search (should be lowercase).
            keywords: Set of keywords to search for.

        Returns:
            True if any keyword found, False otherwise.
        """
        for keyword in keywords:
            if keyword.lower() in text:
                return True
        return False

    def _is_chinese_text(self, text: str) -> bool:
        """
        Heuristic to detect if text is primarily Chinese.

        Args:
            text: Text to analyze.

        Returns:
            True if text appears to be Chinese, False otherwise.
        """
        # Simple heuristic: check for Chinese characters
        chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        return chinese_chars > len(text) * 0.3  # More than 30% Chinese characters


# Global content filter instance
content_filter = ContentFilter()


def check_content(text: str, language: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """
    Convenience function to check if content is harmful.

    Args:
        text: Text to check.
        language: Language code ("zh", "en", or None).

    Returns:
        Tuple of (is_harmful: bool, reason: Optional[str]).
    """
    return content_filter.is_harmful(text, language)
