"""
Step 3: Song query with fuzzy matching.

This module handles querying song information from taikowiki with
fuzzy matching support for partial or misspelled song names.

Per FR-002: System MUST provide accurate information about Taiko no Tatsujin
songs when queried, including difficulty ratings and BPM.
Per FR-004: System MUST support fuzzy matching for song name queries to handle
partial or misspelled names.
"""

import re
from typing import Optional

from src.services.song_query import get_song_service


def extract_song_query(message: str) -> Optional[str]:
    """
    Extract song name from user message.

    Attempts to identify song queries in user messages using heuristics:
    - Questions about songs ("What's the BPM of X?", "Tell me about X")
    - Direct song name mentions
    - Song-related keywords

    Args:
        message: User's message.

    Returns:
        Extracted song name, or None if no song query detected.

    Example:
        >>> extract_song_query("What's the BPM of 千本桜?")
        "千本桜"
        >>> extract_song_query("Tell me about 千本桜")
        "千本桜"
    """
    if not message:
        return None

    # Common song query patterns
    patterns = [
        r"(?:BPM|bpm|速度|节奏).*?[：:]\s*([^\?。！!?]+)",  # "BPM: 千本桜"
        r"(?:难度|difficulty|stars).*?[：:]\s*([^\?。！!?]+)",  # "难度: 千本桜"
        r"(?:关于|about|tell me about|what.*?about)\s+([^\?。！!?]+)",  # "关于 千本桜"
        r"(?:的|of|'s)\s+([^\?。！!?]+)\s+(?:BPM|bpm|难度|difficulty)",  # "千本桜的BPM"
        r"([^\?。！!?]+)\s*(?:的|of)\s*(?:BPM|bpm|难度|difficulty)",  # "千本桜的BPM"
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            song_name = match.group(1).strip()
            if song_name:
                return song_name

    # If no pattern matches, check if message is a simple song name
    # (heuristic: short message without question words)
    message_clean = message.strip()
    if len(message_clean) < 50 and not any(
        word in message_clean.lower()
        for word in ["what", "how", "tell", "about", "的", "关于", "什么"]
    ):
        # Might be a direct song name
        return message_clean

    return None


async def query_song(message: str) -> Optional[dict]:
    """
    Query song information from taikowiki API (PRIMARY) with fuzzy matching.

    This function:
    1. Extracts song name from user message
    2. Queries song cache with fuzzy matching
    3. Returns song information with difficulty and BPM
    4. Indicates if fallback data source was used

    Per FR-002: Provide accurate song information including difficulty and BPM.
    Per FR-002 Enhancement: taikowiki API is PRIMARY data source, local JSON is fallback.
    Per FR-004: Support fuzzy matching for partial or misspelled names.
    Per FR-009 Enhancement: Notify user when using cached/fallback data.

    Args:
        message: User's message (may contain song query).

    Returns:
        Song dict with structure:
        - song_name: str
        - difficulty_stars: int (1-10)
        - bpm: int
        - metadata: dict
        - used_fallback: bool (True if local JSON was used instead of API)
        Or None if no song found or query not detected.

    Example:
        >>> result = query_song("What's the BPM of 千本桜?")
        >>> if result:
        ...     print(f"{result['song_name']}: {result['bpm']} BPM")
        "千本桜: 200 BPM"
    """
    # Extract song query from message
    song_query = extract_song_query(message)

    if not song_query:
        # No song query detected
        return None

    # Get song service and ensure cache is fresh
    # Per FR-002: Automatic background refresh to maintain data freshness
    service = get_song_service()
    
    # Ensure cache is fresh (returns success and fallback status)
    cache_success, used_fallback = await service.ensure_cache_fresh()
    
    # If cache refresh failed, try fallback directly
    if not cache_success:
        try:
            songs, used_fallback = await service.fetch_songs(use_fallback=True)
            # Update cache with fallback data
            from datetime import datetime
            import src.services.song_query as sq_module
            sq_module._songs_cache = songs
            sq_module._cache_timestamp = datetime.utcnow()
        except Exception:
            # Fallback also failed - try to use existing cache if available
            if not service.is_cache_stale():
                used_fallback = True  # Using stale cache is similar to fallback
            else:
                # No cache available - return None
                return None

    # Query with fuzzy matching
    # Per FR-004: Fuzzy matching for partial/misspelled names
    song = service.query_song(song_query, threshold=0.7)

    if song is None:
        # No match found
        return None

    # Return song information with fallback indicator
    return {
        "song_name": song["name"],
        "difficulty_stars": song["difficulty_stars"],
        "bpm": song["bpm"],
        "metadata": song.get("metadata", {}),
        "used_fallback": used_fallback,  # Indicate if fallback was used
    }
