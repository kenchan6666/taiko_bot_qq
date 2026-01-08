"""
Step 5: Update impression and conversation history.

This module handles updating user impression and saving conversation
history to MongoDB.

Per FR-005: Store conversation history (auto-deleted after 90 days).
Per FR-010: Inform users when bot learns or remembers information.
Per FR-010 Enhancement: Handle unconfirmed preferences (retain in pending state,
do not re-ask, re-confirm naturally in context).
"""

import re
from datetime import datetime
from typing import Optional

from src.models.conversation import Conversation
from src.models.impression import Impression
from src.models.user import User
from src.services.llm import get_llm_service
from src.steps.step1 import ParsedInput
from src.steps.step2 import UserContext


async def update_impression(
    parsed_input: ParsedInput,
    context: UserContext,
    response: str,
) -> tuple[User, Impression, Conversation]:
    """
    Update user impression and save conversation.

    This function:
    1. Creates or updates User record
    2. Creates or updates Impression record (increments interaction count)
    3. Creates Conversation record (auto-expires after 90 days)

    Per FR-005: Store conversation history with 90-day auto-deletion.
    Per FR-010: Update impression when bot learns new information.

    Args:
        parsed_input: Parsed input from step1.
        context: User context from step2.
        response: Generated response from step4.

    Returns:
        Tuple of (User, Impression, Conversation) documents.

    Example:
        >>> parsed = ParsedInput(...)
        >>> context = UserContext(...)
        >>> response = "Don! Hello! 🥁"
        >>> user, impression, conversation = await update_impression(
        ...     parsed, context, response
        ... )
        >>> print(f"Interactions: {impression.interaction_count}")
    """
    # Step 1: Create or update User
    if context.user is None:
        # New user - create User record
        user = User(
            hashed_user_id=parsed_input.hashed_user_id,
            preferred_language=None,  # Will be set based on usage
        )
        await user.insert()
    else:
        # Existing user - update timestamp
        user = context.user
        user.update_timestamp()
        await user.save()

    # Step 2: Create or update Impression
    if context.impression is None:
        # New impression - create Impression record
        impression = Impression(
            user_id=parsed_input.hashed_user_id,
            relationship_status="new",
            interaction_count=0,
        )
        await impression.insert()
    else:
        # Existing impression - increment interaction count
        impression = context.impression

    # Increment interaction count (updates relationship_status automatically)
    impression.increment_interaction()
    
    # Step 2.5: Preference learning and confirmation
    # Per FR-010 Enhancement: Extract preferences, handle confirmation, manage pending state
    await _handle_preference_learning(
        impression=impression,
        parsed_input=parsed_input,
        response=response,
        context=context,
    )
    
    await impression.save()

    # Step 3: Create Conversation record
    # Per FR-005: Store conversation history (auto-deleted after 90 days)
    conversation = Conversation.create(
        user_id=parsed_input.hashed_user_id,
        group_id=parsed_input.group_id,
        message=parsed_input.message,
        response=response,
        images=parsed_input.images if parsed_input.images else None,
        timestamp=datetime.utcnow(),
    )
    await conversation.insert()

    return user, impression, conversation
