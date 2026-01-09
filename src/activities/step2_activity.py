"""
Temporal Activity for Step 2: Context retrieval.

This activity wraps the step2.py retrieve_context function as a Temporal Activity,
enabling retry logic and fault tolerance for database queries.

Per T043: Create src/activities/step2_activity.py wrapping step2.py as Temporal Activity.
"""

from typing import Optional

from temporalio import activity

from src.services.database import ensure_database_initialized
from src.steps.step2 import UserContext, retrieve_context


@activity.defn(name="step2_retrieve_context")
async def step2_retrieve_context_activity(hashed_user_id: str) -> dict:
    """
    Temporal Activity for retrieving user context from MongoDB.

    Wraps step2.retrieve_context() as a Temporal Activity to enable:
    - Automatic retries on database connection failures
    - Fault tolerance for transient MongoDB errors
    - Workflow orchestration

    Args:
        hashed_user_id: SHA-256 hashed QQ user ID.

    Returns:
        Dictionary representation of UserContext.
        Dictionary format:
        {
            "user": dict | None,  # User document (serialized)
            "impression": dict | None,  # Impression document (serialized)
            "recent_conversations": list[dict],  # List of conversation dicts
            "is_new_user": bool,
            "preferred_language": str | None,
            "relationship_status": str,
            "interaction_count": int
        }

    Example:
        >>> context_dict = await step2_retrieve_context_activity("abc123...")
        >>> print(context_dict["is_new_user"])
        >>> print(context_dict["relationship_status"])
    """
    # Ensure database is initialized (required for Worker processes)
    await ensure_database_initialized()

    # Call step2.retrieve_context() function
    context = await retrieve_context(hashed_user_id)

    # Convert UserContext to dict for Temporal serialization
    # Serialize User document
    user_dict: Optional[dict] = None
    if context.user:
        user_dict = {
            "hashed_user_id": context.user.hashed_user_id,
            "preferred_language": context.user.preferred_language,
            "created_at": context.user.created_at.isoformat() if context.user.created_at else None,
            "updated_at": context.user.updated_at.isoformat() if context.user.updated_at else None,
        }

    # Serialize Impression document
    impression_dict: Optional[dict] = None
    if context.impression:
        impression_dict = {
            "user_id": context.impression.user_id,
            "preferences": context.impression.preferences,
            "relationship_status": context.impression.relationship_status,
            "interaction_count": context.impression.interaction_count,
            "last_interaction": (
                context.impression.last_interaction.isoformat()
                if context.impression.last_interaction
                else None
            ),
        }

    # Serialize recent conversations
    conversations_list = []
    for conv in context.recent_conversations:
        conversations_list.append(
            {
                "user_id": conv.user_id,
                "group_id": conv.group_id,
                "message": conv.message,
                "response": conv.response,
                "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
                "expires_at": conv.expires_at.isoformat() if conv.expires_at else None,
            }
        )

    return {
        "user": user_dict,
        "impression": impression_dict,
        "recent_conversations": conversations_list,
        "is_new_user": context.is_new_user,
        "preferred_language": context.preferred_language,
        "relationship_status": context.relationship_status,
        "interaction_count": context.interaction_count,
    }
