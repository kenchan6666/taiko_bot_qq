"""
Step 4: LLM invocation.

This module handles invoking the LLM (gpt-4o via OpenRouter) to generate
themed responses using prompt templates from the PromptManager.

Per FR-003: Incorporate thematic game elements in all responses.
Per FR-013: Use structured prompt template system for easy iteration.
"""

from typing import Optional

from src.config import get_bot_name
from src.prompts import get_prompt_manager
from src.services.llm import get_llm_service
from src.steps.step2 import UserContext
from src.steps.step1 import ParsedInput


async def invoke_llm(
    parsed_input: ParsedInput,
    context: UserContext,
    song_info: Optional[dict] = None,
) -> str:
    """
    Invoke LLM to generate themed response.

    Uses PromptManager to get appropriate prompt template, then calls
    OpenRouter gpt-4o API to generate response.

    Per FR-003: Incorporate thematic game elements ("Don!", "Katsu!", emojis).
    Per FR-013: Use structured prompt template system.

    Args:
        parsed_input: Parsed input from step1.
        context: User context from step2.
        song_info: Optional song information from step3 (None for now).

    Returns:
        Generated response text from LLM.

    Raises:
        RuntimeError: If LLM service fails (per FR-009: graceful degradation).

    Example:
        >>> parsed = ParsedInput(...)
        >>> context = UserContext(...)
        >>> response = await invoke_llm(parsed, context)
        >>> print(response)
        "Don! Hello! I'm Mika, the Taiko drum spirit! 🥁"
    """
    # Get prompt manager and LLM service
    prompt_manager = get_prompt_manager()
    llm_service = get_llm_service()

    # Get bot name from config
    bot_name = get_bot_name()

    # Check if images are provided (multi-modal request)
    # Per FR-006: Use image analysis prompts when images are present
    has_images = bool(parsed_input.images and len(parsed_input.images) > 0)

    # Build prompt using PromptManager
    # Priority: images > song_info > memory_aware > general_chat
    try:
        if has_images:
            # Multi-modal request: Use image analysis prompt
            # Per FR-006: Provide detailed analysis for Taiko images,
            # themed response for non-Taiko images
            # The LLM will analyze the image and determine if it's Taiko-related
            try:
                # Use image analysis prompt (LLM will determine Taiko vs non-Taiko)
                # We use image_analysis_taiko as the primary prompt, which instructs
                # the LLM to provide detailed analysis for Taiko images
                prompt = prompt_manager.get_prompt(
                    name="image_analysis_taiko",
                    bot_name=bot_name,
                    language=parsed_input.language,
                    user_message=parsed_input.message or (
                        "请分析这张图片" if parsed_input.language == "zh" else "Please analyze this image"
                    ),
                )
            except ValueError:
                # Image analysis prompt not found - use fallback
                # Per FR-009: Graceful degradation
                prompt = f"""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

The user has sent you an image. Please analyze it:
- If it's a Taiko no Tatsujin screenshot: Provide detailed analysis (song name, difficulty, score, game elements)
- If it's not Taiko-related: Politely indicate you focus on Taiko content, but still be friendly

User message: {parsed_input.message or ("请分析这张图片" if parsed_input.language == "zh" else "Please analyze this image")}

Respond with themed content using game terminology ("Don!", "Katsu!", emojis 🥁🎶)."""
        elif song_info:
            # Song query detected - use song_query prompt
            # Format metadata for prompt
            metadata_text = ""
            if song_info.get("metadata"):
                metadata_items = []
                for key, value in song_info["metadata"].items():
                    metadata_items.append(f"{key}: {value}")
                if metadata_items:
                    metadata_text = "\n".join(metadata_items)
            else:
                metadata_text = "No additional metadata available."

            # Check if fallback data source was used
            # Per FR-009 Enhancement: Notify user when using cached/fallback data
            fallback_notice = ""
            if song_info.get("used_fallback", False):
                if parsed_input.language == "zh":
                    fallback_notice = "注意：使用缓存数据，可能不是最新的。"
                else:
                    fallback_notice = "Note: Using cached data, may not be latest."
            
            prompt = prompt_manager.get_prompt(
                name="song_query",
                bot_name=bot_name,
                song_name=song_info["song_name"],
                bpm=song_info["bpm"],
                difficulty_stars=song_info["difficulty_stars"],
                metadata_text=metadata_text,
                user_message=parsed_input.message,
                language=parsed_input.language,
                fallback_notice=fallback_notice,
            )
        else:
            # General chat - check if we should use memory-aware prompt
            # Per Phase 6: Use memory-aware prompt if conversation history available
            # Also check for pending preferences to include confirmation requests
            pending_preferences_text = ""
            if context.impression and context.impression.pending_preferences:
                # Per FR-010 Enhancement: Re-confirm naturally when relevant
                # Format pending preferences for prompt
                pending_items = []
                for key, pending in context.impression.pending_preferences.items():
                    value = pending.get("value", "")
                    if value:
                        if parsed_input.language == "zh":
                            pending_items.append(f"用户可能喜欢: {key} = {value}")
                        else:
                            pending_items.append(f"User might prefer: {key} = {value}")
                if pending_items:
                    pending_preferences_text = "\n".join(pending_items)
            
            # Format conversation history
            history_text = ""
            if context.recent_conversations:
                for conv in context.recent_conversations[:5]:  # Last 5 for context
                    history_text += f"User: {conv.message}\nBot: {conv.response}\n\n"
            
            if context.recent_conversations or pending_preferences_text:
                # Format conversation history for prompt
                history_text = ""
                for conv in context.recent_conversations[:5]:  # Last 5 for context
                    history_text += f"User: {conv.message}\nBot: {conv.response}\n\n"
                
                # Use memory-aware prompt if available, otherwise general_chat
                try:
                    prompt = prompt_manager.get_prompt(
                        name="memory_aware",
                        bot_name=bot_name,
                        language=parsed_input.language,
                        user_message=parsed_input.message,
                        conversation_history=history_text or "No previous conversations.",
                        relationship_status=context.relationship_status,
                        interaction_count=context.interaction_count,
                        pending_preferences=pending_preferences_text or "No pending preferences.",
                    )
                except ValueError:
                    # Memory-aware prompt not available yet - use general_chat
                    # But still include pending preferences if available
                    if pending_preferences_text:
                        prompt = f"""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

Pending preferences to confirm (ask naturally in context):
{pending_preferences_text}

User message: {parsed_input.message}

Respond as {bot_name} with themed content, incorporating game elements and emojis.
If there are pending preferences, naturally ask for confirmation in your response."""
                    else:
                        prompt = prompt_manager.get_prompt(
                            name="general_chat",
                            bot_name=bot_name,
                            language=parsed_input.language,
                            user_message=parsed_input.message,
                        )
            else:
                # No conversation history - use general_chat prompt
                prompt = prompt_manager.get_prompt(
                    name="general_chat",
                    bot_name=bot_name,
                    language=parsed_input.language,
                    user_message=parsed_input.message,
                )
    except ValueError as e:
        # Fallback if prompt not found
        # Per FR-009: Graceful degradation
        if song_info:
            prompt = f"""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

Song Information:
- Name: {song_info['song_name']}
- BPM: {song_info['bpm']}
- Difficulty: {song_info['difficulty_stars']} stars

User message: {parsed_input.message}

Respond as {bot_name} with themed content, incorporating game elements and emojis."""
        else:
            prompt = f"""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

User message: {parsed_input.message}

Respond as {bot_name} with themed content, incorporating game elements and emojis."""

    # Invoke LLM with prompt and optional images
    try:
        response = await llm_service.generate_response(
            prompt=prompt,
            images=parsed_input.images if parsed_input.images else None,
            temperature=0.7,
            max_tokens=500,
        )
        return response
    except RuntimeError as e:
        # Per FR-009: Graceful degradation
        # Return default themed response if LLM fails
        return _get_fallback_response(bot_name, parsed_input.language)


def _get_fallback_response(bot_name: str, language: str) -> str:
    """
    Get fallback response when LLM service is unavailable.

    Per FR-009: Gracefully degrade when external services are unavailable.

    Args:
        bot_name: Bot's name.
        language: User's language.

    Returns:
        Default themed response.
    """
    if language == "zh":
        return f"Don! {bot_name}暂时无法回应，但我会尽快回来的！🥁"
    else:
        return f"Don! {bot_name} is temporarily unavailable, but I'll be back soon! 🥁"
