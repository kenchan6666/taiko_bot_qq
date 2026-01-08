"""
Temporal Activity for Step 1: Input parsing and validation.

This activity wraps the step1.py parse_input function as a Temporal Activity,
enabling retry logic and fault tolerance for input parsing operations.

Per T042: Create src/activities/step1_activity.py wrapping step1.py as Temporal Activity.
"""

from typing import Optional

from temporalio import activity

from src.steps.step1 import ParsedInput, parse_input


@activity.defn(name="step1_parse_input")
async def step1_parse_input_activity(
    user_id: str,
    group_id: str,
    message: str,
    images: Optional[list[str]] = None,
) -> Optional[dict]:
    """
    Temporal Activity for parsing and validating input.

    Wraps step1.parse_input() as a Temporal Activity to enable:
    - Automatic retries on transient failures
    - Fault tolerance and error handling
    - Workflow orchestration

    Args:
        user_id: Plaintext QQ user ID (will be hashed).
        group_id: QQ group ID where message was sent.
        message: User's message content.
        images: Optional list of base64-encoded images.

    Returns:
        Dictionary representation of ParsedInput, or None if invalid.
        Dictionary format:
        {
            "hashed_user_id": str,
            "group_id": str,
            "message": str,
            "language": str,
            "images": list[str] | None
        }

    Example:
        >>> result = await step1_parse_input_activity(
        ...     user_id="123456789",
        ...     group_id="987654321",
        ...     message="Mika, hello!"
        ... )
        >>> if result:
        ...     print(result["hashed_user_id"])
    """
    # Call step1.parse_input() function
    parsed_input = parse_input(
        user_id=user_id,
        group_id=group_id,
        message=message,
        images=images,
    )

    # Convert ParsedInput to dict for Temporal serialization
    if parsed_input is None:
        return None

    return {
        "hashed_user_id": parsed_input.hashed_user_id,
        "group_id": parsed_input.group_id,
        "message": parsed_input.message,
        "language": parsed_input.language,
        "images": parsed_input.images or [],
    }
