"""
Language detection utilities.

This module provides functions for detecting user message language
and managing user language preferences.

Per NFR-008: System MUST automatically detect user message language,
but MUST also allow users to explicitly specify their preferred language.
This balances automation with user control for better UX.
"""

from typing import Optional

from langdetect import detect, DetectorFactory, LangDetectException

# Set seed for consistent results (optional, for reproducibility)
# DetectorFactory.seed = 0


def detect_language(text: str, default: str = "zh") -> str:
    """
    Automatically detect the language of a text message.

    Uses the langdetect library to identify the language. Supports
    Chinese (zh) and English (en) primarily, with fallback to default.

    Args:
        text: Text message to analyze.
        default: Default language code if detection fails (default: "zh").

    Returns:
        Language code string ("zh" for Chinese, "en" for English, or default).

    Example:
        >>> detect_language("你好，Mika！")
        'zh'
        >>> detect_language("Hello, Mika!")
        'en'
    """
    if not text or not text.strip():
        return default

    try:
        # Detect language (returns ISO 639-1 code)
        detected = detect(text)

        # Map common language codes to our supported languages
        # langdetect may return "zh-cn" or "zh-tw" for Chinese
        if detected.startswith("zh"):
            return "zh"
        elif detected == "en":
            return "en"
        else:
            # For other languages, return default
            return default

    except LangDetectException:
        # If detection fails (e.g., too short text), return default
        return default


def get_user_language(
    message: str,
    user_preference: Optional[str] = None,
    default: str = "zh",
) -> str:
    """
    Determine the language to use for a user message.

    Priority order:
    1. User's explicit preference (if set)
    2. Auto-detected language from message
    3. System default

    Per NFR-008: System MUST automatically detect user message language,
    but MUST also allow users to explicitly specify their preferred language.

    Args:
        message: User's message text.
        user_preference: User's preferred language ("zh", "en", or None).
        default: System default language if detection fails (default: "zh").

    Returns:
        Language code string ("zh" or "en").

    Example:
        >>> get_user_language("Hello", user_preference="zh")
        'zh'  # User preference takes priority
        >>> get_user_language("Hello", user_preference=None)
        'en'  # Auto-detected
    """
    # Priority 1: User's explicit preference
    if user_preference in ("zh", "en"):
        return user_preference

    # Priority 2: Auto-detect from message
    detected = detect_language(message, default=default)

    # Priority 3: System default (already handled by detect_language)
    return detected


def is_valid_language_code(lang_code: Optional[str]) -> bool:
    """
    Validate that a language code is supported.

    Supported languages: "zh" (Chinese) and "en" (English).

    Args:
        lang_code: Language code to validate.

    Returns:
        True if valid and supported, False otherwise.
    """
    return lang_code in ("zh", "en")
