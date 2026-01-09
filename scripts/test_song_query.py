#!/usr/bin/env python3
"""
Manual testing script for song query functionality.

This script allows manual testing of song queries with command-line
arguments for song name, testing fuzzy matching and caching.

Per T103: Create scripts/test_song_query.py for manual testing

Usage:
    python scripts/test_song_query.py --song "千本桜"
    python scripts/test_song_query.py --song "senbonzakura"  # Fuzzy match
    python scripts/test_song_query.py --song "千本桜" --no-cache  # Skip cache
"""

import argparse
import asyncio
import sys

from src.services.song_query import SongQueryService
from src.services.database import init_database


async def test_song_query(
    song_name: str,
    use_cache: bool = True,
) -> None:
    """
    Test song query with given song name.

    Args:
        song_name: Song name to search for.
        use_cache: Whether to use cache (default: True).
    """
    print(f"Testing song query: {song_name}")
    print(f"Use cache: {use_cache}")
    print()
    
    try:
        # Initialize database
        await init_database()
        
        # Create service
        service = SongQueryService()
        
        # Ensure cache is fresh (if using cache)
        if use_cache:
            print("Ensuring cache is fresh...")
            cache_success, used_fallback = await service.ensure_cache_fresh()
            print(f"Cache refresh: {'success' if cache_success else 'failed'}")
            if used_fallback:
                print("⚠ Using fallback data (API unavailable)")
            print()
        
        # Query song
        print(f"Searching for: {song_name}")
        start_time = asyncio.get_event_loop().time()
        
        songs, used_fallback = await service.query_song(song_name, use_fallback=use_cache)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        print(f"\nQuery completed in {elapsed:.3f}s")
        print(f"Used fallback: {used_fallback}")
        print()
        
        if songs:
            print(f"✓ Found {len(songs)} matching song(s):\n")
            for i, song in enumerate(songs, 1):
                print(f"{i}. {song.get('name', 'N/A')}")
                print(f"   BPM: {song.get('bpm', 'N/A')}")
                print(f"   Difficulty: {song.get('difficulty_stars', 'N/A')} stars")
                if song.get('metadata'):
                    print(f"   Metadata: {song['metadata']}")
                print()
        else:
            print("✗ No matching songs found")
            print("\nSuggestions:")
            print("- Check spelling")
            print("- Try partial name")
            print("- Try English or Japanese name")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test song query functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic query
  python scripts/test_song_query.py --song "千本桜"
  
  # Fuzzy match
  python scripts/test_song_query.py --song "senbonzakura"
  
  # Skip cache (force API query)
  python scripts/test_song_query.py --song "千本桜" --no-cache
  
  # Partial name
  python scripts/test_song_query.py --song "千本"
        """,
    )
    
    parser.add_argument(
        "--song",
        type=str,
        required=True,
        help="Song name to search for",
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip cache and force API query",
    )
    
    args = parser.parse_args()
    
    # Validate song name
    if not args.song.strip():
        print("Error: Song name cannot be empty")
        sys.exit(1)
    
    # Run test
    asyncio.run(
        test_song_query(
            song_name=args.song,
            use_cache=not args.no_cache,
        )
    )


if __name__ == "__main__":
    main()
