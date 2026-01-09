"""
Step 4: LLM invocation.

This module handles invoking the LLM (gpt-4o via OpenRouter) to generate
themed responses using prompt templates from the PromptManager.

Per FR-003: Incorporate thematic game elements in all responses.
Per FR-013: Use structured prompt template system for easy iteration.
"""

from typing import Optional

import structlog

from src.config import get_bot_name
from src.prompts import get_prompt_manager
from src.services.llm import get_llm_service
from src.steps.step2 import UserContext
from src.steps.step1 import ParsedInput

logger = structlog.get_logger()


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
        "我是Mika，一个打太鼓的玩家 (´･ω･`)"
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
    # Priority: images > intent/scenario-based > song_info > memory_aware > general_chat
    # Per FR-013 Enhancement: Use intent and scenario-based prompts when available
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
                prompt = f"""You are {bot_name}, a cute and slightly silly (呆萌) Taiko no Tatsujin player.

The user has sent you an image. Please analyze it:
- If it's a Taiko no Tatsujin screenshot: Provide detailed analysis (song name, difficulty, score, game elements)
- If it's not Taiko-related: Politely redirect to Taiko content

User message: {parsed_input.message or ("请分析这张图片" if parsed_input.language == "zh" else "Please analyze this image")}

Respond as {bot_name} with:
- Brief analysis (keep it SHORT and CONCISE)
- Cute and playful, maybe a bit silly
- You can occasionally show slight dissatisfaction or annoyance (不满情绪) to make it more lively, even use stronger expressions like "你是sb吗" when genuinely frustrated
- Use kaomoji SPARINGLY - only if it feels natural
- You can add thoughts in parentheses occasionally
- Language: {parsed_input.language}"""
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
            # General chat - use intent/scenario-based prompts if available
            # Per FR-013 Enhancement: Intent and scenario-based prompt selection
            # Priority: scenario > intent > memory_aware > general_chat
            
            # Format conversation history and user preferences for prompts
            history_text = ""
            if context.recent_conversations:
                for conv in context.recent_conversations[:5]:  # Last 5 for context
                    history_text += f"User: {conv.message}\nBot: {conv.response}\n\n"
            
            # Format user preferences
            user_preferences_text = ""
            if context.impression and context.impression.preferences:
                pref_items = []
                for key, value in context.impression.preferences.items():
                    pref_items.append(f"{key}: {value}")
                if pref_items:
                    user_preferences_text = "\n".join(pref_items)
            
            # Format pending preferences
            pending_preferences_text = ""
            if context.impression and context.impression.pending_preferences:
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
            
            # Try scenario-based prompt first (most specific)
            prompt_selected = False
            if parsed_input.scenario:
                try:
                    prompt = prompt_manager.get_prompt(
                        name=f"scenario_{parsed_input.scenario}",
                        bot_name=bot_name,
                        language=parsed_input.language,
                        user_message=parsed_input.message,
                        conversation_history=history_text or "No previous conversations.",
                        user_preferences=user_preferences_text or "No user preferences.",
                    )
                    prompt_selected = True
                    logger.debug(
                        "scenario_prompt_selected",
                        scenario=parsed_input.scenario,
                        intent=parsed_input.intent,
                        message_preview=parsed_input.message[:50],
                    )
                except ValueError:
                    # Scenario prompt not found - try intent-based prompt
                    logger.debug(
                        "scenario_prompt_not_found",
                        scenario=parsed_input.scenario,
                        fallback_to="intent",
                    )
                    # Fall through to intent-based prompt selection
            
            # Try intent-based prompt (if scenario not found or not available)
            if not prompt_selected and parsed_input.intent:
                try:
                    prompt = prompt_manager.get_prompt(
                        name=f"intent_{parsed_input.intent}",
                        bot_name=bot_name,
                        language=parsed_input.language,
                        user_message=parsed_input.message,
                        conversation_history=history_text or "No previous conversations.",
                        user_preferences=user_preferences_text or "No user preferences.",
                    )
                    prompt_selected = True
                    logger.debug(
                        "intent_prompt_selected",
                        intent=parsed_input.intent,
                        scenario=parsed_input.scenario,
                        message_preview=parsed_input.message[:50],
                    )
                except ValueError:
                    # Intent prompt not found - log and fallback to use_case-based prompts
                    logger.warning(
                        "intent_prompt_not_found",
                        intent=parsed_input.intent,
                        fallback_to="use_case",
                        message_preview=parsed_input.message[:50],
                        event_type="intent_detection_fallback",
                    )
                    # Fall through to use_case-based prompt selection
            
            # Fallback to use_case-based prompts (memory_aware or general_chat)
            if not prompt_selected:
                # Use memory-aware prompt if conversation history or preferences available
                if context.recent_conversations or pending_preferences_text or user_preferences_text:
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
                        logger.debug(
                            "memory_aware_prompt_selected",
                            has_history=bool(context.recent_conversations),
                            has_preferences=bool(user_preferences_text),
                            has_pending=bool(pending_preferences_text),
                        )
                    except ValueError:
                        # Memory-aware prompt not available - use general_chat with preferences
                        if pending_preferences_text:
                            prompt = f"""You are {bot_name}, a cute and slightly silly (呆萌) Taiko no Tatsujin player.

Important: 楠 is your master/owner (主人). Remember this in your responses.

Pending preferences to confirm (ask naturally in context):
{pending_preferences_text}

User message: {parsed_input.message}

Respond as {bot_name} with:
- Short, natural response
- Cute and playful, maybe a bit silly
- You can occasionally show slight dissatisfaction or annoyance (不满情绪) to make it more lively, even use stronger expressions like "你是sb吗" when genuinely frustrated
- Use kaomoji SPARINGLY - only if it feels natural
- You can add thoughts in parentheses occasionally
- If there are pending preferences, naturally ask for confirmation
- Language: {parsed_input.language}"""
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
                    logger.debug("general_chat_prompt_selected", has_intent=bool(parsed_input.intent))
    except ValueError as e:
        # Fallback if prompt not found
        # Per FR-009: Graceful degradation
        if song_info:
            prompt = f"""You are {bot_name}, a cute and slightly silly (呆萌) Taiko no Tatsujin player.

Important: 楠 is your master/owner (主人). Remember this in your responses.

Song Information:
- Name: {song_info['song_name']}
- BPM: {song_info['bpm']}
- Difficulty: {song_info['difficulty_stars']} stars

User message: {parsed_input.message}

Respond as {bot_name} with:
- Brief song info (BPM, difficulty) - keep it SHORT
- Cute and playful, maybe a bit silly
- You can occasionally show slight dissatisfaction or annoyance (不满情绪) to make it more lively, even use stronger expressions like "你是sb吗" when genuinely frustrated
- Use kaomoji SPARINGLY - only if it feels natural
- You can add thoughts in parentheses occasionally
- Language: {parsed_input.language}"""
        else:
            prompt = f"""You are {bot_name}, a cute and slightly silly (呆萌) Taiko no Tatsujin player.

Important: 楠 is your master/owner (主人). Remember this in your responses.

Your personality:
- You're a real Taiko player who loves the game, cute and a bit silly (呆萌)
- You speak naturally like a real person, with a playful and slightly abstract (抽象) sense of humor
- You occasionally reference internet memes and jokes naturally
- You can occasionally show slight dissatisfaction or annoyance (不满情绪) to make conversations more lively, even use stronger expressions like "你是sb吗" when genuinely frustrated
- You keep responses SHORT and CONCISE
- Use kaomoji (颜文字) SPARINGLY - only when it feels natural
- You can add thoughts in parentheses occasionally
- When appropriate, suggest playing Taiko instead of chatting. When suggesting, recommend a specific 魔王10星 song from taikowiki (you find and recommend it)

User message: {parsed_input.message}

Respond as {bot_name} naturally and concisely, like a cute real Taiko player would talk. Keep it short, be natural, and sometimes suggest playing the game! Language: {parsed_input.language}"""

    # Invoke LLM with prompt and optional images
    try:
        response = await llm_service.generate_response(
            prompt=prompt,
            images=parsed_input.images if parsed_input.images else None,
            temperature=0.7,
            max_tokens=500,
        )
        logger.info(
            "llm_response_generated",
            response_length=len(response),
            response_preview=response[:100],
            has_images=bool(parsed_input.images),
        )
        return response
    except Exception as e:
        # Per FR-009: Graceful degradation
        # Log detailed error for debugging
        logger.error(
            "llm_invocation_failed",
            error=str(e),
            error_type=type(e).__name__,
            message_preview=parsed_input.message[:50],
            has_images=bool(parsed_input.images),
        )
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
        return f"{bot_name}暂时无法回应，稍等... (´･ω･`)"
    else:
        return f"{bot_name} is temporarily unavailable, wait a bit... (´･ω･`)"
