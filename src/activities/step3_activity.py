"""
Temporal Activity for Step 3: Song query.

This activity wraps the step3.py query_song function as a Temporal Activity,
enabling retry logic and fault tolerance for song queries.

Per T044: Create src/activities/step3_activity.py wrapping step3.py as Temporal Activity.
"""

from typing import Optional

from temporalio import activity

from src.steps.step3 import query_song


@activity.defn(name="step3_query_song")
async def step3_query_song_activity(message: str) -> Optional[dict]:
    """
    Temporal Activity for querying song information.

    Wraps step3.query_song() as a Temporal Activity to enable:
    - Automatic retries on taikowiki API failures
    - Fault tolerance for network errors
    - Workflow orchestration

    Args:
        message: User's message (may contain song query).

    Returns:
        Dictionary representation of song information, or None if no song found.
        Dictionary format:
        {
            "song_name": str,
            "difficulty_stars": int,
            "bpm": int,
            "metadata": dict
        }

    Example:
        >>> song_info = await step3_query_song_activity("What's the BPM of 千本桜?")
        >>> if song_info:
        ...     print(f"{song_info['song_name']}: {song_info['bpm']} BPM")
    """
    # Call step3.query_song() function
    song_info = await query_song(message)

    # Return as-is (already a dict or None)
    return song_info
