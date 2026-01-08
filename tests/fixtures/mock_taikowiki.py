"""
Mock taikowiki API responses for testing.

Provides mock HTTP responses that mimic taikowiki JSON endpoint
for use in unit and integration tests.
"""

from typing import Any
import json

from tests.fixtures.mock_songs import SAMPLE_SONGS


def get_mock_taikowiki_response() -> dict[str, Any]:
    """
    Get mock taikowiki JSON response.

    Returns:
        Mock JSON response matching taikowiki format.
    """
    # taikowiki format: list of songs
    return SAMPLE_SONGS.copy()


def get_mock_taikowiki_response_dict() -> dict[str, Any]:
    """
    Get mock taikowiki JSON response as dict (with "songs" key).

    Some taikowiki endpoints return {"songs": [...]} format.

    Returns:
        Mock JSON response with "songs" key.
    """
    return {"songs": SAMPLE_SONGS.copy()}


def get_mock_taikowiki_json_string() -> str:
    """
    Get mock taikowiki JSON response as string.

    Returns:
        JSON string representation of mock songs.
    """
    return json.dumps(SAMPLE_SONGS, ensure_ascii=False)


def get_mock_taikowiki_error_response() -> dict[str, Any]:
    """
    Get mock error response from taikowiki.

    Returns:
        Error response dict.
    """
    return {"error": "Service unavailable", "message": "taikowiki is temporarily down"}
