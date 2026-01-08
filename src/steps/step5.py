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


async def _handle_preference_learning(
    impression: Impression,
    parsed_input: ParsedInput,
    response: str,
    context: UserContext,
) -> None:
    """
    Handle preference learning and confirmation flow.
    
    Per FR-010 Enhancement:
    - Extract preferences from conversation using LLM
    - Check for explicit/implicit confirmation in user message
    - Confirm pending preferences if user confirms
    - Add new preferences to pending state if not confirmed
    - Do not actively re-ask, wait for natural context
    
    Args:
        impression: Impression document to update.
        parsed_input: Parsed input from step1.
        response: Generated response from step4.
        context: User context from step2.
    """
    # Step 1: Check for explicit confirmation in user message
    # Per FR-010: Prioritize explicit confirmation ("是", "对", "yes", "correct", etc.)
    confirmation_patterns = {
        "zh": [r"是", r"对", r"没错", r"对的", r"正确", r"是的"],
        "en": [r"\byes\b", r"\bcorrect\b", r"\bright\b", r"\byeah\b"],
    }
    
    is_confirmation = False
    is_rejection = False
    
    language = parsed_input.language
    patterns = confirmation_patterns.get(language, [])
    for pattern in patterns:
        if re.search(pattern, parsed_input.message, re.IGNORECASE):
            is_confirmation = True
            break
    
    # Check for rejection
    rejection_patterns = {
        "zh": [r"不是", r"不对", r"错误", r"不"],
        "en": [r"\bno\b", r"\bincorrect\b", r"\bwrong\b"],
    }
    patterns = rejection_patterns.get(language, [])
    for pattern in patterns:
        if re.search(pattern, parsed_input.message, re.IGNORECASE):
            is_rejection = True
            break
    
    # Step 2: Check if there are pending preferences that match current context
    # Per FR-010 Enhancement: Re-confirm naturally when users mention related topics
    if impression.pending_preferences:
        for key, pending in list(impression.pending_preferences.items()):
            # Check if current message is related to pending preference context
            if _is_related_to_preference(parsed_input.message, pending["context"]):
                if is_confirmation:
                    # User confirmed - move to confirmed preferences
                    impression.confirm_pending_preference(key)
                elif is_rejection:
                    # User rejected - remove from pending
                    del impression.pending_preferences[key]
                # If neither confirmation nor rejection, keep in pending (don't re-ask)
    
    # Step 3: Extract new preferences from conversation using LLM
    # Per FR-010: Use LLM to automatically analyze conversation content
    try:
        llm_service = get_llm_service()
        
        # Build context for preference extraction
        conversation_context = f"User: {parsed_input.message}\nBot: {response}"
        if context.recent_conversations:
            history = "\n".join([
                f"User: {c.message}\nBot: {c.response}"
                for c in context.recent_conversations[:3]
            ])
            conversation_context = f"{history}\n{conversation_context}"
        
        extraction_prompt = f"""Analyze the following conversation and extract user preferences about Taiko no Tatsujin.

Conversation:
{conversation_context}

Extract preferences such as:
- favorite_bpm_range: "high", "medium", "low", or None
- favorite_difficulty: "extreme", "hard", "normal", "easy", or None
- favorite_genre: genre name or None
- other preferences: any other relevant preferences

Respond in JSON format:
{{"favorite_bpm_range": "...", "favorite_difficulty": "...", "favorite_genre": "...", "other": [...]}}

If no clear preferences found, return {{}}."""

        extraction_response = await llm_service.generate_response(
            prompt=extraction_prompt,
            temperature=0.3,
            max_tokens=200,
        )
        
        # Parse extracted preferences (simple JSON extraction)
        import json
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', extraction_response)
            if json_match:
                extracted = json.loads(json_match.group())
                
                # Add new preferences to pending state
                # Per FR-010 Enhancement: Add to pending, don't confirm immediately
                for key, value in extracted.items():
                    if value and value != "None" and key not in impression.preferences:
                        # Check if already in pending
                        if key not in impression.pending_preferences:
                            impression.add_pending_preference(
                                key=key,
                                value=value,
                                context=conversation_context,
                            )
        except (json.JSONDecodeError, KeyError):
            # Failed to parse - skip preference extraction
            pass
            
    except Exception:
        # LLM extraction failed - skip (graceful degradation)
        pass


def _is_related_to_preference(message: str, context: str) -> bool:
    """
    Check if message is related to a preference context.
    
    Per FR-010 Enhancement: Re-confirm naturally when users mention related topics.
    
    Args:
        message: Current user message.
        context: Preference extraction context.
        
    Returns:
        True if message is related to context, False otherwise.
    """
    # Simple keyword-based relevance check
    # Extract keywords from context
    context_lower = context.lower()
    message_lower = message.lower()
    
    # Check for common preference-related keywords
    preference_keywords = [
        "bpm", "速度", "节奏", "tempo",
        "难度", "difficulty", "level", "stars",
        "genre", "类型", "风格",
        "喜欢", "like", "prefer", "favorite",
    ]
    
    context_has_keywords = any(kw in context_lower for kw in preference_keywords)
    message_has_keywords = any(kw in message_lower for kw in preference_keywords)
    
    # If both have preference-related keywords, consider related
    if context_has_keywords and message_has_keywords:
        return True
    
    return False
