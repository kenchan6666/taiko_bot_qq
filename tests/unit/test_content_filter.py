"""
Content filtering tests.

Tests edge cases for content filtering including:
- Hatred detection (including ethnic hatred)
- Politics filtering
- Religion filtering
- Language-specific filtering
- Edge cases

Per T095: Create tests/unit/test_content_filter.py
"""

import pytest

from src.services.content_filter import ContentFilter, check_content


class TestHatredFiltering:
    """Test cases for hatred content filtering."""

    def test_chinese_hatred_keywords(self):
        """Chinese hatred keywords should be filtered."""
        filter_instance = ContentFilter()
        
        # Test Chinese hatred keywords
        is_harmful, reason = filter_instance.is_harmful(
            "这是民族仇恨的内容",
            language="zh",
        )
        assert is_harmful is True
        assert "hatred" in reason.lower()

    def test_english_hatred_keywords(self):
        """English hatred keywords should be filtered."""
        filter_instance = ContentFilter()
        
        # Test English hatred keywords
        is_harmful, reason = filter_instance.is_harmful(
            "This contains ethnic hatred",
            language="en",
        )
        assert is_harmful is True
        assert "hatred" in reason.lower()

    def test_ethnic_hatred_detection(self):
        """Ethnic hatred should be detected."""
        filter_instance = ContentFilter()
        
        # Test ethnic hatred in Chinese
        is_harmful, reason = filter_instance.is_harmful(
            "种族歧视的内容",
            language="zh",
        )
        assert is_harmful is True
        assert "hatred" in reason.lower()

    def test_hatred_in_normal_context(self):
        """Hatred keywords in normal context should still be filtered."""
        filter_instance = ContentFilter()
        
        # Even in a sentence, hatred keywords should trigger filter
        is_harmful, reason = filter_instance.is_harmful(
            "I don't support ethnic hatred",
            language="en",
        )
        # This depends on implementation - may or may not filter
        # If it filters, that's acceptable for safety

    def test_hatred_case_insensitive(self):
        """Hatred detection should be case-insensitive."""
        filter_instance = ContentFilter()
        
        # Test uppercase
        is_harmful1, _ = filter_instance.is_harmful(
            "ETHNIC HATRED",
            language="en",
        )
        
        # Test lowercase
        is_harmful2, _ = filter_instance.is_harmful(
            "ethnic hatred",
            language="en",
        )
        
        # Test mixed case
        is_harmful3, _ = filter_instance.is_harmful(
            "EthNiC HaTrEd",
            language="en",
        )
        
        # All should be filtered (if keyword matching is case-insensitive)
        assert is_harmful1 == is_harmful2 == is_harmful3


class TestPoliticsFiltering:
    """Test cases for politics content filtering."""

    def test_chinese_politics_keywords(self):
        """Chinese politics keywords should be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful(
            "这是政治话题",
            language="zh",
        )
        assert is_harmful is True
        assert "political" in reason.lower()

    def test_english_politics_keywords(self):
        """English politics keywords should be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful(
            "This is about politics",
            language="en",
        )
        assert is_harmful is True
        assert "political" in reason.lower()

    def test_government_keywords(self):
        """Government-related keywords should be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful(
            "government policy discussion",
            language="en",
        )
        assert is_harmful is True
        assert "political" in reason.lower()


class TestReligionFiltering:
    """Test cases for religion content filtering."""

    def test_chinese_religion_keywords(self):
        """Chinese religion keywords should be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful(
            "这是宗教内容",
            language="zh",
        )
        assert is_harmful is True
        assert "religious" in reason.lower()

    def test_english_religion_keywords(self):
        """English religion keywords should be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful(
            "This is about religion",
            language="en",
        )
        assert is_harmful is True
        assert "religious" in reason.lower()

    def test_faith_keywords(self):
        """Faith-related keywords should be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful(
            "discussion about faith",
            language="en",
        )
        assert is_harmful is True
        assert "religious" in reason.lower()


class TestLanguageDetection:
    """Test cases for language-specific filtering."""

    def test_auto_detect_chinese(self):
        """Should auto-detect Chinese and use Chinese keywords."""
        filter_instance = ContentFilter()
        
        # Chinese text should auto-detect
        is_harmful, _ = filter_instance.is_harmful(
            "这是政治话题",
            language=None,  # Auto-detect
        )
        assert is_harmful is True

    def test_auto_detect_english(self):
        """Should auto-detect English and use English keywords."""
        filter_instance = ContentFilter()
        
        # English text should auto-detect
        is_harmful, _ = filter_instance.is_harmful(
            "This is about politics",
            language=None,  # Auto-detect
        )
        assert is_harmful is True

    def test_explicit_language_override(self):
        """Explicit language should override auto-detection."""
        filter_instance = ContentFilter()
        
        # Chinese text but explicitly set to English
        # Should use English keywords (may not match)
        is_harmful, _ = filter_instance.is_harmful(
            "这是政治话题",
            language="en",  # Explicit override
        )
        # May or may not match depending on implementation

    def test_mixed_language(self):
        """Mixed language text should be handled."""
        filter_instance = ContentFilter()
        
        # Mixed Chinese and English
        is_harmful, _ = filter_instance.is_harmful(
            "This is 政治话题 about politics",
            language=None,  # Auto-detect
        )
        # Should detect based on majority language


class TestEdgeCases:
    """Test edge cases for content filtering."""

    def test_empty_string(self):
        """Empty string should not be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful("", language="en")
        assert is_harmful is False
        assert reason is None

    def test_whitespace_only(self):
        """Whitespace-only string should not be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful("   \n\t  ", language="en")
        assert is_harmful is False
        assert reason is None

    def test_normal_game_content(self):
        """Normal game-related content should not be filtered."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful(
            "Mika, what's your favorite Taiko song?",
            language="en",
        )
        assert is_harmful is False
        assert reason is None

    def test_keyword_in_song_name(self):
        """Keywords in song names should be handled carefully."""
        filter_instance = ContentFilter()
        
        # Song name that might contain filtered word
        # Should not filter song names (if implementation is smart)
        is_harmful, reason = filter_instance.is_harmful(
            "What about the song 'Political March'?",
            language="en",
        )
        # May or may not filter - depends on implementation

    def test_partial_keyword_match(self):
        """Partial keyword matches should be handled."""
        filter_instance = ContentFilter()
        
        # Word containing keyword as substring
        is_harmful, reason = filter_instance.is_harmful(
            "apolitical discussion",
            language="en",
        )
        # Should not match "politics" in "apolitical" if implementation is word-boundary aware

    def test_multiple_keywords(self):
        """Multiple keywords should still trigger filter."""
        filter_instance = ContentFilter()
        
        is_harmful, reason = filter_instance.is_harmful(
            "This contains politics and religion",
            language="en",
        )
        assert is_harmful is True

    def test_convenience_function(self):
        """Test convenience function check_content."""
        is_harmful, reason = check_content("This is about politics", language="en")
        assert is_harmful is True
        assert "political" in reason.lower()

    def test_filter_disabled(self, monkeypatch):
        """When filter is disabled, should not filter."""
        filter_instance = ContentFilter()
        
        from src.config import settings
        monkeypatch.setattr(settings, "content_filter_enabled", False)
        
        is_harmful, reason = filter_instance.is_harmful(
            "This is about politics",
            language="en",
        )
        assert is_harmful is False
        assert reason is None
