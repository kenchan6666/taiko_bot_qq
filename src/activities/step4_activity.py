"""
Temporal Activity for Step 4: LLM invocation.

This activity wraps the step4.py invoke_llm function as a Temporal Activity,
enabling retry logic and fault tolerance for LLM API calls.

Per T045: Create src/activities/step4_activity.py wrapping step4.py as Temporal Activity.
"""

from typing import Optional

from temporalio import activity

from src.steps.step4 import invoke_llm


@activity.defn(name="step4_invoke_llm")
async def step4_invoke_llm_activity(
    parsed_input_dict: dict,
    context_dict: dict,
    song_info: Optional[dict] = None,
) -> str:
    """
    Temporal Activity for invoking LLM to generate response.

    Wraps step4.invoke_llm() as a Temporal Activity to enable:
    - Automatic retries on OpenRouter API failures
    - Fault tolerance for network errors and rate limits
    - Workflow orchestration

    Args:
        parsed_input_dict: Dictionary representation of ParsedInput from step1.
        context_dict: Dictionary representation of UserContext from step2.
        song_info: Optional song information dictionary from step3.

    Returns:
        Generated response text from LLM.

    Example:
        >>> parsed = {"hashed_user_id": "...", "message": "Hello!", ...}
        >>> context = {"is_new_user": True, ...}
        >>> response = await step4_invoke_llm_activity(parsed, context)
        >>> print(response)
        "Don! Hello! I'm Mika! 🥁"
    """
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
        conv = Conversation(
            user_id=conv_data["user_id"],
            group_id=conv_data["group_id"],
            message=conv_data["message"],
            response=conv_data["response"],
        )
        if conv_data.get("timestamp"):
            conv.timestamp = datetime.fromisoformat(conv_data["timestamp"])
        recent_conversations.append(conv)

    context = UserContext(
        user=user,
        impression=impression,
        recent_conversations=recent_conversations,
    )

    # Call step4.invoke_llm() function
    response = await invoke_llm(
        parsed_input=parsed_input,
        context=context,
        song_info=song_info,
    )

    return response
