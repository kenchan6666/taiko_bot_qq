"""
Mock song data fixtures for testing.

Provides sample song data that mimics taikowiki JSON format
for use in unit and integration tests.
"""

from typing import Any

# Sample song data matching taikowiki JSON structure
SAMPLE_SONGS: list[dict[str, Any]] = [
    {
        "name": "千本桜",
        "difficulty_stars": 9,
        "bpm": 200,
        "metadata": {
            "genre": "Vocaloid",
            "artist": "Kurousa-P",
            "category": "Anime",
        },
    },
    {
        "name": "紅蓮華",
        "difficulty_stars": 8,
        "bpm": 180,
        "metadata": {
            "genre": "Anime",
            "artist": "LiSA",
            "category": "Anime",
        },
    },
    {
        "name": "Bad Apple!!",
        "difficulty_stars": 7,
        "bpm": 150,
        "metadata": {
            "genre": "Touhou",
            "artist": "Alstroemeria Records",
            "category": "Game",
        },
    },
    {
        "name": "ドラムガン狂騒曲",
        "difficulty_stars": 10,
        "bpm": 220,
        "metadata": {
            "genre": "Original",
            "artist": "Taiko Team",
            "category": "Original",
        },
    },
    {
        "name": "Butterfly",
        "difficulty_stars": 6,
        "bpm": 140,
        "metadata": {
            "genre": "Anime",
            "artist": "Kouji Wada",
            "category": "Anime",
        },
    },
]


def get_mock_song(name: str) -> dict[str, Any] | None:
    """
    Get a mock song by name.

    Args:
        name: Song name to find.

    Returns:
        Song dict if found, None otherwise.
    """
    for song in SAMPLE_SONGS:
        if song["name"] == name:
            return song.copy()
    return None


def get_all_mock_songs() -> list[dict[str, Any]]:
    """
    Get all mock songs.

    Returns:
        List of all mock song dictionaries.
    """
    return [song.copy() for song in SAMPLE_SONGS]
