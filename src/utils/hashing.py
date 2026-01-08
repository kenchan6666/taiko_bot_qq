"""
User ID hashing utilities.

This module provides functions for hashing QQ user IDs using SHA-256
to ensure privacy compliance while enabling cross-group user recognition.

Per FR-011: User identification MUST use hashed QQ user IDs (SHA-256)
to enable cross-group memory while protecting user privacy.
"""

import hashlib
from typing import Optional


def hash_user_id(user_id: str) -> str:
    """
    Hash a QQ user ID using SHA-256.

    This function converts a plaintext QQ user ID into a 64-character
    hexadecimal hash string. This enables:
    - Privacy protection: Never store plaintext user IDs
    - Cross-group recognition: Same user across different QQ groups
    - GDPR compliance: No personally identifiable information stored

    Args:
        user_id: Plaintext QQ user ID as string.

    Returns:
        64-character hexadecimal SHA-256 hash string.

    Example:
        >>> hash_user_id("123456789")
        '15e2b0d3c33891ebb0f1ef609ec419420c20e623cecf2bb38a6573198c036c4e'
    """
    if not user_id:
        raise ValueError("User ID cannot be empty or None")

    # Encode user ID to bytes for hashing
    user_id_bytes = user_id.encode("utf-8")

    # Create SHA-256 hash
    hash_object = hashlib.sha256(user_id_bytes)

    # Return hexadecimal representation (64 characters)
    return hash_object.hexdigest()


def validate_hashed_user_id(hashed_id: str) -> bool:
    """
    Validate that a string is a valid SHA-256 hash.

    SHA-256 hashes are always 64 hexadecimal characters.

    Args:
        hashed_id: String to validate.

    Returns:
        True if valid SHA-256 hash format, False otherwise.
    """
    if not hashed_id:
        return False

    # SHA-256 produces 64-character hex strings
    if len(hashed_id) != 64:
        return False

    # Check that all characters are valid hexadecimal
    try:
        int(hashed_id, 16)
        return True
    except ValueError:
        return False


def hash_user_id_safe(user_id: Optional[str]) -> Optional[str]:
    """
    Safely hash a user ID, returning None if input is None or empty.

    This is useful for optional user ID fields where None is acceptable.

    Args:
        user_id: Plaintext QQ user ID, or None.

    Returns:
        Hashed user ID string, or None if input was None/empty.
    """
    if not user_id:
        return None
    return hash_user_id(user_id)
