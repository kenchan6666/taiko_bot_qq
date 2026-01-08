"""
Song query service with taikowiki integration.

This module provides song query functionality with:
- taikowiki JSON fetching
- In-memory caching with periodic refresh (hourly)
- Fuzzy matching using rapidfuzz library

Per FR-002: System MUST provide accurate information about Taiko no Tatsujin
songs when queried, including difficulty ratings and BPM. System MUST implement
in-memory caching with periodic refresh (e.g., hourly) for song data from
taikowiki JSON. Queries MUST prioritize cached data for fast response times,
with automatic background refresh to maintain data freshness.
Per FR-004: System MUST support fuzzy matching for song name queries to handle
partial or misspelled names.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from rapidfuzz import process

# In-memory song cache
# Structure: list of dicts with keys: name, difficulty_stars, bpm, metadata
_songs_cache: list[dict] = []
_cache_timestamp: Optional[datetime] = None
_cache_refresh_interval = timedelta(hours=1)  # Hourly refresh per FR-002


class SongQueryService:
    """
    Song query service with caching and fuzzy matching.

    Provides fast song queries using in-memory cache with automatic
    background refresh. Supports fuzzy matching for partial/misspelled names.
    """

    def __init__(self, json_url: Optional[str] = None) -> None:
        """
        Initialize song query service.

        Args:
            json_url: taiko.wiki JSON endpoint URL. If None, uses config value.
        """
        if json_url is None:
            # Import here to avoid circular dependency and Temporal sandbox issues
            from src.config import settings
            json_url = settings.taikowiki_json_url
        self.json_url = json_url
        self._refresh_task: Optional[asyncio.Task] = None

    async def fetch_songs(self, use_fallback: bool = False) -> tuple[list[dict], bool]:
        """
        Fetch songs from taikowiki API (PRIMARY data source) or local JSON fallback.

        Per FR-002 Enhancement: taikowiki API is PRIMARY data source.
        Local JSON file (data/database.json) is used ONLY as fallback when API unavailable.
        When updating local file, system SHOULD replace existing data for consistency.

        Args:
            use_fallback: If True, skip API and use local file directly.

        Returns:
            Tuple of (list of song dictionaries, used_fallback: bool).
            Song dict structure:
            - name: str (song name)
            - difficulty_stars: int (1-10)
            - bpm: int (beats per minute)
            - metadata: dict (additional info like genre, artist)

        Raises:
            RuntimeError: If all fetch methods fail.
            ValueError: If JSON response is invalid.
        """
        # Local JSON fallback file path (from config or default)
        from src.config import settings
        fallback_path = Path(settings.taikowiki_local_json_path)
        if not fallback_path.is_absolute():
            # Make relative to project root
            fallback_path = Path(__file__).parent.parent.parent / fallback_path

        used_fallback = False
        
        # If use_fallback is True, skip API and use local file directly
        if use_fallback:
            if not fallback_path.exists():
                raise RuntimeError(
                    f"Fallback file not found: {fallback_path}"
                )
            try:
                data = json.loads(fallback_path.read_text(encoding="utf-8"))
                used_fallback = True
            except Exception as e:
                raise RuntimeError(
                    f"Failed to read fallback file: {e}"
                ) from e
        else:
            # PRIMARY: Try taikowiki API first
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.json_url)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Update local JSON file with fresh data from API
                    # Per FR-002 Enhancement: Replace existing data for consistency
                    try:
                        fallback_path.parent.mkdir(parents=True, exist_ok=True)
                        fallback_path.write_text(
                            json.dumps(data, ensure_ascii=False, indent=2),
                            encoding="utf-8"
                        )
                    except Exception as write_error:
                        # Log but don't fail - API data is still available
                        print(f"Warning: Failed to update local JSON file: {write_error}")
                        
            except (httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError) as e:
                # API failed - use local JSON file as fallback
                print(f"Warning: Failed to fetch from taikowiki API ({self.json_url}): {e}")
                print(f"Falling back to local file: {fallback_path}")
                
                if not fallback_path.exists():
                    raise RuntimeError(
                        f"Failed to fetch songs from API and fallback file not found: {fallback_path}"
                    ) from e
                
                try:
                    data = json.loads(fallback_path.read_text(encoding="utf-8"))
                    used_fallback = True
                    print(f"Successfully loaded {len(data) if isinstance(data, list) else 'data'} songs from fallback file")
                except Exception as file_error:
                    raise RuntimeError(
                        f"Failed to fetch from API and failed to read fallback file: {file_error}"
                    ) from file_error
            except ValueError as e:
                raise ValueError(f"Invalid JSON response from taikowiki: {e}") from e

        # Normalize song data structure
        songs: list[dict] = []
        if isinstance(data, list):
            # If JSON is a list of songs
            for song in data:
                normalized = self._normalize_song(song)
                if normalized:
                    songs.append(normalized)
        elif isinstance(data, dict) and "songs" in data:
            # If JSON has a "songs" key
            for song in data["songs"]:
                normalized = self._normalize_song(song)
                if normalized:
                    songs.append(normalized)

        return songs, used_fallback

    def _normalize_song(self, song: dict) -> Optional[dict]:
        """
        Normalize song data structure.

        Converts taiko.wiki API format to our standard format.
        
        taiko.wiki API format:
        - title: str (song name)
        - bpm: {min: int, max: int} (BPM range)
        - courses: {oni: {level: int}, ...} (difficulty levels)
        - artists: list[str]
        - genre: list[str]

        Args:
            song: Raw song data from taiko.wiki API.

        Returns:
            Normalized song dict, or None if invalid.
        """
        try:
            # Extract song name (taiko.wiki API uses "title")
            name = song.get("title") or song.get("name") or song.get("song_name")
            if not name:
                return None

            # Extract BPM (taiko.wiki API uses {min, max} object)
            bpm_obj = song.get("bpm")
            if isinstance(bpm_obj, dict):
                # Use max BPM if available, otherwise min, otherwise 0
                bpm = bpm_obj.get("max") or bpm_obj.get("min") or 0
            elif isinstance(bpm_obj, (int, float)):
                bpm = int(bpm_obj)
            elif isinstance(bpm_obj, str):
                try:
                    bpm = int(bpm_obj)
                except ValueError:
                    bpm = 0
            else:
                bpm = 0

            # Extract difficulty (taiko.wiki API stores in courses.oni.level)
            # Prefer oni (hardest) difficulty, fallback to other difficulties
            courses = song.get("courses", {})
            difficulty = 0
            
            # Try to get oni (hardest) difficulty first
            if isinstance(courses, dict) and "oni" in courses:
                oni_course = courses["oni"]
                if isinstance(oni_course, dict) and "level" in oni_course:
                    level = oni_course["level"]
                    if isinstance(level, (int, float)):
                        difficulty = int(level)
                    elif isinstance(level, str):
                        try:
                            difficulty = int(level)
                        except ValueError:
                            difficulty = 0
            
            # Fallback: try other difficulty fields if oni not available
            if difficulty == 0:
                difficulty = (
                    song.get("difficulty_stars")
                    or song.get("difficulty")
                    or song.get("stars")
                    or 0
                )
                if isinstance(difficulty, str):
                    try:
                        difficulty = int(difficulty)
                    except ValueError:
                        difficulty = 0

            # Extract metadata
            metadata = {}
            
            # Add genre (taiko.wiki API uses list)
            if "genre" in song:
                genre = song["genre"]
                if isinstance(genre, list):
                    metadata["genre"] = genre
                elif isinstance(genre, str):
                    metadata["genre"] = [genre]
            
            # Add artists (taiko.wiki API uses list)
            if "artists" in song:
                artists = song["artists"]
                if isinstance(artists, list):
                    metadata["artists"] = artists
                elif isinstance(artists, str):
                    metadata["artists"] = [artists]
            
            # Add other fields to metadata
            for key in ["songNo", "romaji", "titleKo", "titleEn", "version"]:
                if key in song:
                    metadata[key] = song[key]

            return {
                "name": str(name),
                "difficulty_stars": int(difficulty),
                "bpm": int(bpm),
                "metadata": metadata,
            }

        except (KeyError, ValueError, TypeError):
            # Invalid song data - skip
            return None

    async def refresh_cache(self) -> tuple[bool, bool]:
        """
        Refresh song cache from taikowiki API (PRIMARY) or local JSON fallback.

        Per FR-002: Periodic refresh (hourly) to maintain data freshness.
        Per FR-002 Enhancement: taikowiki API is PRIMARY data source.

        This function updates the global cache and timestamp.

        Returns:
            Tuple of (success: bool, used_fallback: bool).
        """
        global _songs_cache, _cache_timestamp

        try:
            songs, used_fallback = await self.fetch_songs(use_fallback=False)
            _songs_cache = songs
            _cache_timestamp = datetime.utcnow()
            return True, used_fallback
        except Exception as e:
            # Log error but don't fail - use stale cache
            # Per FR-009: Graceful degradation
            print(f"Warning: Failed to refresh song cache: {e}")
            return False, False

    def is_cache_stale(self) -> bool:
        """
        Check if cache is stale and needs refresh.

        Per FR-002: Cache refresh interval is hourly.

        Returns:
            True if cache is stale or empty, False otherwise.
        """
        global _cache_timestamp

        if not _songs_cache or _cache_timestamp is None:
            return True

        # Check if cache is older than refresh interval
        age = datetime.utcnow() - _cache_timestamp
        return age >= _cache_refresh_interval

    async def ensure_cache_fresh(self) -> tuple[bool, bool]:
        """
        Ensure cache is fresh (refresh if stale).

        Per FR-002: Automatic background refresh to maintain data freshness.

        Returns:
            Tuple of (success: bool, used_fallback: bool).
        """
        if self.is_cache_stale():
            return await self.refresh_cache()
        # Cache is fresh - assume from API (most common case)
        return True, False

    def query_song(
        self,
        query: str,
        threshold: float = 0.7,
    ) -> Optional[dict]:
        """
        Query song by name with fuzzy matching.

        Per FR-002: Provide accurate song information.
        Per FR-004: Support fuzzy matching for partial or misspelled names.

        Args:
            query: Song name query (may be partial or misspelled).
            threshold: Similarity threshold (0.0-1.0, default: 0.7).

        Returns:
            Best matching song dict, or None if no match found.

        Example:
            >>> service = SongQueryService()
            >>> song = service.query_song("千本桜")
            >>> print(song["name"], song["bpm"])
            "千本桜" 200
        """
        global _songs_cache

        if not _songs_cache:
            # Cache is empty - return None
            return None

        # Extract song names for fuzzy matching
        song_names = [song["name"] for song in _songs_cache]

        # Use rapidfuzz for fuzzy matching
        # Per research.md: Use rapidfuzz.process.extractOne() with threshold 0.7
        result = process.extractOne(
            query,
            song_names,
            score_cutoff=int(threshold * 100),  # rapidfuzz uses 0-100 scale
        )

        if result is None:
            # No match found above threshold
            return None

        matched_name, score, index = result

        # Return the matched song
        return _songs_cache[index].copy()

    def get_all_songs(self) -> list[dict]:
        """
        Get all cached songs.

        Returns:
            List of all song dictionaries.
        """
        global _songs_cache
        return _songs_cache.copy()


# Global song query service instance
_song_service: Optional[SongQueryService] = None


def get_song_service() -> SongQueryService:
    """
    Get global song query service instance.

    Returns:
        Global SongQueryService instance.
    """
    global _song_service

    if _song_service is None:
        _song_service = SongQueryService()

    return _song_service


async def initialize_song_cache() -> None:
    """
    Initialize song cache at application startup.

    Per FR-002: Cache songs at startup for fast queries.

    This should be called during application startup.
    """
    service = get_song_service()
    await service.refresh_cache()
