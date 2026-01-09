"""
Temporal Activity for Step 5: Update impression and conversation history.

This activity wraps the step5.py update_impression function as a Temporal Activity,
enabling retry logic and fault tolerance for database writes.

Per T046: Create src/activities/step5_activity.py wrapping step5.py as Temporal Activity.
"""

from temporalio import activity

from src.services.database import ensure_database_initialized
from src.steps.step5 import update_impression


@activity.defn(name="step5_update_impression")
async def step5_update_impression_activity(
    parsed_input_dict: dict,
    context_dict: dict,
    response: str,
) -> dict:
    """
    Temporal Activity for updating user impression and saving conversation.

    Wraps step5.update_impression() as a Temporal Activity to enable:
    - Automatic retries on database write failures
    - Fault tolerance for transient MongoDB errors
    - Workflow orchestration

    Args:
        parsed_input_dict: Dictionary representation of ParsedInput from step1.
        context_dict: Dictionary representation of UserContext from step2.
        response: Generated response text from step4.

    Returns:
        Dictionary with updated user, impression, and conversation info.
        Dictionary format:
        {
            "user": dict,  # Updated User document
            "impression": dict,  # Updated Impression document
            "conversation": dict,  # Created Conversation document
            "interaction_count": int,
            "relationship_status": str
        }

    Example:
        >>> parsed = {"hashed_user_id": "...", ...}
        >>> context = {"is_new_user": True, ...}
        >>> result = await step5_update_impression_activity(
        ...     parsed, context, "Don! Hello! 🥁"
        ... )
        >>> print(result["interaction_count"])
    """
    # Ensure database is initialized (required for Worker processes)
    await ensure_database_initialized()

    # Reconstruct ParsedInput from dict
    from src.steps.step1 import ParsedInput

    parsed_input = ParsedInput(
        hashed_user_id=parsed_input_dict["hashed_user_id"],
        group_id=parsed_input_dict["group_id"],
        message=parsed_input_dict["message"],
        language=parsed_input_dict["language"],
        images=parsed_input_dict.get("images") or [],
    )

    # Reconstruct UserContext from dict
    from src.steps.step2 import UserContext
    from src.models.user import User
    from src.models.impression import Impression
    from src.models.conversation import Conversation
    from datetime import datetime

    user = None
    if context_dict.get("user"):
        user_data = context_dict["user"]
        user = User(
            hashed_user_id=user_data["hashed_user_id"],
            preferred_language=user_data.get("preferred_language"),
        )

    impression = None
    if context_dict.get("impression"):
        imp_data = context_dict["impression"]
        impression = Impression(
            user_id=imp_data["user_id"],
            preferences=imp_data.get("preferences", {}),
            relationship_status=imp_data.get("relationship_status", "new"),
            interaction_count=imp_data.get("interaction_count", 0),
        )
        if imp_data.get("last_interaction"):
            impression.last_interaction = datetime.fromisoformat(imp_data["last_interaction"])

    recent_conversations = []
    for conv_data in context_dict.get("recent_conversations", []):
        # Reconstruct Conversation with all required fields
        conv_timestamp = None
        if conv_data.get("timestamp"):
            conv_timestamp = datetime.fromisoformat(conv_data["timestamp"])
        else:
            conv_timestamp = datetime.utcnow()
        
        # Use Conversation.create() to ensure expires_at is set correctly
        conv = Conversation.create(
            user_id=conv_data["user_id"],
            group_id=conv_data["group_id"],
            message=conv_data["message"],
            response=conv_data["response"],
            timestamp=conv_timestamp,
        )
        recent_conversations.append(conv)

    context = UserContext(
        user=user,
        impression=impression,
        recent_conversations=recent_conversations,
    )

    # Call step5.update_impression() function
    user, impression, conversation = await update_impression(
        parsed_input=parsed_input,
        context=context,
        response=response,
    )

    # Convert results to dict for Temporal serialization
    return {
        "user": {
            "hashed_user_id": user.hashed_user_id,
            "preferred_language": user.preferred_language,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
        "impression": {
            "user_id": impression.user_id,
            "preferences": impression.preferences,
            "relationship_status": impression.relationship_status,
            "interaction_count": impression.interaction_count,
            "last_interaction": (
                impression.last_interaction.isoformat()
                if impression.last_interaction
                else None
            ),
        },
        "conversation": {
            "user_id": conversation.user_id,
            "group_id": conversation.group_id,
            "message": conversation.message,
            "response": conversation.response,
            "timestamp": conversation.timestamp.isoformat() if conversation.timestamp else None,
            "expires_at": conversation.expires_at.isoformat() if conversation.expires_at else None,
            "timestamp": conversation.timestamp.isoformat() if conversation.timestamp else None,
        },
        "interaction_count": impression.interaction_count,
        "relationship_status": impression.relationship_status,
    }
