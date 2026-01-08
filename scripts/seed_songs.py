"""
Song data seeding script.

This script fetches and caches taikowiki song data at application startup.
It should be run before starting the FastAPI server to ensure song cache
is populated for fast queries.

Per FR-002: Cache songs at startup for fast response times.

Usage:
    python scripts/seed_songs.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.song_query import get_song_service, initialize_song_cache


async def main() -> None:
    """
    Main function to seed song cache.

    Fetches songs from taikowiki and populates in-memory cache.
    """
    print("Fetching songs from taikowiki...")

    try:
        # Initialize song cache
        await initialize_song_cache()

        # Get service to check cache status
        service = get_song_service()
        songs = service.get_all_songs()

        if songs:
            print(f"✅ Successfully cached {len(songs)} songs!")
            print("\nSample songs:")
            for song in songs[:5]:  # Show first 5 songs
                print(f"  - {song['name']}: {song['bpm']} BPM, {song['difficulty_stars']} stars")
            if len(songs) > 5:
                print(f"  ... and {len(songs) - 5} more songs")
        else:
            print("⚠️  Warning: No songs cached. Check taikowiki endpoint and network connection.")

    except Exception as e:
        print(f"❌ Failed to seed song cache: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run async main function
    asyncio.run(main())
