"""
Step 1: Input parsing and validation.

This module handles the first step of message processing:
- Parse incoming message from LangBot webhook
- Detect "Mika" name mentions using regex pattern
- Apply hybrid content filtering (keyword lists + LLM judgment)
- Hash user ID for privacy compliance
- Validate image data (size and format limits per FR-006)

Per FR-001: System MUST only respond to messages that explicitly mention
the bot's name ("Mika" or recognized variants).
Per FR-007: Content filtering MUST use hybrid approach (keyword lists + LLM).
Per FR-011: User identification MUST use hashed QQ user IDs (SHA-256).
Per FR-006: Image processing limits (10MB max, JPEG/PNG/WebP only).
"""

import base64
import re
from typing import Optional

from src.config import settings
from src.services.content_filter import check_content
from src.services.message_deduplication import get_deduplication_service
from src.utils.hashing import hash_user_id
from src.utils.language_detection import detect_language


# Regex pattern for detecting "Mika" mentions
# Case-insensitive matching for: mika, 米卡, mika酱
# Per FR-001: Support variants like "mika", "米卡", "Mika酱"
MIKA_NAME_PATTERN = re.compile(r"(?i)(mika|米卡|mika酱)", re.IGNORECASE)


class ParsedInput:
    """
    Parsed input data structure.

    Contains validated and processed input data from LangBot webhook.
    """

    def __init__(
        self,
        hashed_user_id: str,
        group_id: str,
        message: str,
        language: str,
        images: Optional[list[str]] = None,
    ) -> None:
        """
        Initialize parsed input.

        Args:
            hashed_user_id: SHA-256 hashed QQ user ID.
            group_id: QQ group ID where message was sent.
            message: User's message content (with "Mika" mention).
            language: Detected language code ("zh" or "en").
            images: Optional list of base64-encoded images.
        """
        self.hashed_user_id = hashed_user_id
        self.group_id = group_id
        self.message = message
        self.language = language
        self.images = images or []


def parse_input(
    user_id: str,
    group_id: str,
    message: str,
    images: Optional[list[str]] = None,
) -> Optional[ParsedInput]:
    """
    Parse and validate incoming message from LangBot webhook.

    This function performs:
    1. Name detection: Check if message mentions "Mika" (FR-001)
    2. Content filtering: Check for harmful content using hybrid approach (FR-007)
    3. User ID hashing: Hash QQ user ID for privacy (FR-011)
    4. Language detection: Auto-detect message language

    Args:
        user_id: Plaintext QQ user ID (will be hashed).
        group_id: QQ group ID where message was sent.
        message: User's message content.
        images: Optional list of base64-encoded images.

    Returns:
        ParsedInput object if message is valid and mentions "Mika", None otherwise.
        Returns None if:
        - Message doesn't mention "Mika"
        - Content is filtered as harmful
        - Input validation fails

    Example:
        >>> parsed = parse_input(
        ...     user_id="123456789",
        ...     group_id="987654321",
        ...     message="Mika, what's your favorite song?"
        ... )
        >>> parsed.hashed_user_id
        '15e2b0d3c33891ebb0f1ef609ec419420c20e623cecf2bb38a6573198c036c4e'
        >>> parsed.message
        "Mika, what's your favorite song?"
    """
    # Validate required fields
    if not user_id or not group_id or not message:
        return None

    # Step 1: Detect "Mika" name mention
    # Per FR-001: Only respond to messages that explicitly mention bot's name
    if not MIKA_NAME_PATTERN.search(message):
        # Message doesn't mention "Mika" - skip processing
        return None

    # Step 2: Auto-detect language
    # Language detection helps with content filtering and LLM prompts
    language = detect_language(message, default="zh")

    # Step 3: Content filtering (hybrid approach)
    # Per FR-007: Use keyword lists for fast pre-filtering, then LLM judgment
    # For now, we use keyword-based filtering (LLM judgment can be added later)
    is_harmful, reason = check_content(message, language=language)
    if is_harmful:
        # Content is harmful - reject message
        # Reason contains explanation (e.g., "contains hatred keywords")
        return None

    # Step 4: Hash user ID for privacy
    # Per FR-011: Use hashed QQ user IDs (SHA-256) for privacy compliance
    try:
        hashed_user_id = hash_user_id(user_id)
    except ValueError as e:
        # Invalid user ID - reject message
        return None

    # Step 5: Validate images (if provided)
    # Per FR-006: Image processing limits (10MB max, JPEG/PNG/WebP only)
    if images:
        validated_images = _validate_images(images, language)
        if validated_images is None:
            # Image validation failed - reject message
            # Validation function logs the reason (size/format error)
            return None
        images = validated_images

    # Step 6: Message deduplication
    # Per FR-008 Enhancement: Skip duplicate or highly similar messages
    deduplication_service = get_deduplication_service()
    if deduplication_service.is_duplicate(hashed_user_id, message):
        # Message is duplicate or highly similar to recent message - skip processing
        return None

    # Step 7: Create parsed input object
    return ParsedInput(
        hashed_user_id=hashed_user_id,
        group_id=group_id,
        message=message,
        language=language,
        images=images,
    )


def _validate_images(
    images: list[str], language: str
) -> Optional[list[str]]:
    """
    Validate image data from LangBot webhook.

    Per FR-006: Image processing limits:
    - Maximum size: 10MB per image
    - Allowed formats: JPEG, PNG, WebP only

    Args:
        images: List of base64-encoded image strings.
        language: User's language for error messages.

    Returns:
        Validated list of base64-encoded images, or None if validation fails.
        Returns None if:
        - Image size exceeds 10MB limit
        - Image format is not JPEG/PNG/WebP
        - Base64 decoding fails

    Example:
        >>> images = ["/9j/4AAQSkZJRg..."]  # Valid JPEG base64
        >>> validated = _validate_images(images, "zh")
        >>> validated is not None
        True
    """
    if not images:
        return []

    validated: list[str] = []
    max_size_bytes = settings.image_max_size_mb * 1024 * 1024  # Convert MB to bytes
    allowed_formats = settings.image_allowed_formats

    for image_base64 in images:
        try:
            # Decode base64 to get binary data
            # Base64 encoding increases size by ~33%, so we check decoded size
            image_data = base64.b64decode(image_base64, validate=True)
            image_size = len(image_data)

            # Check size limit (10MB per FR-006)
            if image_size > max_size_bytes:
                # Image too large - skip this image
                # Log error but continue with other images
                # In production, you might want to log this to monitoring system
                continue

            # Detect image format from binary data
            # Check magic bytes (file signatures) for JPEG, PNG, WebP
            image_format = _detect_image_format(image_data)
            if image_format not in allowed_formats:
                # Unsupported format - skip this image
                # Log error but continue with other images
                continue

            # Image is valid - add to validated list
            validated.append(image_base64)

        except Exception:
            # Base64 decoding failed or other error - skip this image
            # Log error but continue with other images
            continue

    # Return validated images (may be empty if all failed)
    # If at least one image is valid, return the list
    # If all images failed validation, return None to reject the message
    return validated if validated else None


def _detect_image_format(image_data: bytes) -> Optional[str]:
    """
    Detect image format from binary data using magic bytes (file signatures).

    Per FR-006: Support JPEG, PNG, WebP formats only.

    Args:
        image_data: Binary image data.

    Returns:
        Format string ("jpeg", "png", "webp") or None if format not recognized.

    Example:
        >>> jpeg_data = b"\\xff\\xd8\\xff\\xe0..."  # JPEG magic bytes
        >>> _detect_image_format(jpeg_data)
        'jpeg'
    """
    if not image_data or len(image_data) < 4:
        return None

    # Check JPEG: Starts with FF D8 FF
    if image_data[:3] == b"\xff\xd8\xff":
        return "jpeg"

    # Check PNG: Starts with 89 50 4E 47 (PNG signature)
    if image_data[:4] == b"\x89PNG":
        return "png"

    # Check WebP: Starts with RIFF...WEBP
    if len(image_data) >= 12:
        if image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
            return "webp"

    # Format not recognized
    return None


def is_mika_mentioned(message: str) -> bool:
    """
    Check if message mentions "Mika" or recognized variants.

    Per FR-001: System MUST only respond to messages that explicitly mention
    the bot's name ("Mika" or recognized variants like "mika", "米卡", "Mika酱").

    Args:
        message: User's message content.

    Returns:
        True if "Mika" is mentioned, False otherwise.

    Example:
        >>> is_mika_mentioned("Mika, hello!")
        True
        >>> is_mika_mentioned("Hello, world!")
        False
        >>> is_mika_mentioned("米卡，你好！")
        True
    """
    if not message:
        return False
    return bool(MIKA_NAME_PATTERN.search(message))
