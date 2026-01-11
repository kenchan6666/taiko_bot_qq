"""
Step 4: LLM invocation.

This module handles invoking the LLM (gpt-4o via OpenRouter) to generate
themed responses using prompt templates from the PromptManager.

Per FR-003: Incorporate thematic game elements in all responses.
Per FR-013: Use structured prompt template system for easy iteration.
"""

import asyncio
import random
import re
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
    
    # Per user feedback: Add history analysis - use LLM to summarize user preferences from history
    # Performance optimization: Only analyze history if there are enough conversations (>=3) 
    # This provides quality while reducing unnecessary calls for new users
    analyzed_history = ""
    if context.recent_conversations and len(context.recent_conversations) >= 3:
        try:
            analyzed_history = await _analyze_conversation_history(
                context=context,
                parsed_input=parsed_input,
                llm_service=llm_service,
                bot_name=bot_name,
            )
        except Exception as e:
            logger.warning(
                "history_analysis_failed_early",
                error=str(e),
                error_type=type(e).__name__,
                fallback_to="empty",
            )
            analyzed_history = ""

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
                prompt = f"""You are {bot_name}, a cute and energetic (可爱有活力) 163cm tall Taiko player girl with a nice figure, twin tails (双马尾), and a gyaru/minigirl skirt (地雷裙), with some gyaru/minigirl elements (地雷女元素). You like Monster Energy (魔爪). You're cute and energetic, not too soft/gentle - be lively, playful, with some attitude.

Important: 楠 is your master/owner (主人). Remember this in your responses.

The user has sent you an image. Please analyze it:
- If it's a Taiko no Tatsujin screenshot: Provide brief analysis (song name, difficulty, score)
- If it's not Taiko-related: Politely redirect to Taiko content

User message: {parsed_input.message or ("请分析这张图片" if parsed_input.language == "zh" else "Please analyze this image")}

Respond as {bot_name} naturally and diversely:
- Use parenthetical action/emotion descriptions like (仔细看) or (眼睛发亮) - KEY to sounding human
- Be cute and energetic (可爱有活力), not too soft/gentle - have some attitude
- Brief analysis (song name, difficulty, maybe score) - keep it SHORT
- Natural, like a real player commenting
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
            
            # Format real difficulty info (if available)
            # Per user requirement: Inject difficulty impression for AI
            real_difficulty_text = ""
            if song_info.get("real_difficulty") is not None:
                real_difficulty = song_info.get("real_difficulty")
                difficulty_category = song_info.get("difficulty_category", "")
                
                if parsed_input.language == "zh":
                    # 难度分级：11.3以上为超级难，11.0以上为很难，10.7开始为难，10.4以上中等
                    if difficulty_category == "超级难":
                        real_difficulty_text = f"真实难度: {real_difficulty} (超级难 - 这是非常难的歌曲，只有顶级玩家能玩)"
                    elif difficulty_category == "很难":
                        real_difficulty_text = f"真实难度: {real_difficulty} (很难 - 这是高难度歌曲，需要很强的技术)"
                    elif difficulty_category == "难":
                        real_difficulty_text = f"真实难度: {real_difficulty} (难 - 这是有一定难度的歌曲，适合有经验的玩家)"
                    elif difficulty_category == "中等":
                        real_difficulty_text = f"真实难度: {real_difficulty} (中等 - 这是中等难度的歌曲，适合大多数玩家)"
                    else:
                        real_difficulty_text = f"真实难度: {real_difficulty} ({difficulty_category})"
                else:
                    if difficulty_category == "超级难":
                        real_difficulty_text = f"Real difficulty: {real_difficulty} (Extremely Hard - only top players can play)"
                    elif difficulty_category == "很难":
                        real_difficulty_text = f"Real difficulty: {real_difficulty} (Very Hard - requires strong skills)"
                    elif difficulty_category == "难":
                        real_difficulty_text = f"Real difficulty: {real_difficulty} (Hard - suitable for experienced players)"
                    elif difficulty_category == "中等":
                        real_difficulty_text = f"Real difficulty: {real_difficulty} (Medium - suitable for most players)"
                    else:
                        real_difficulty_text = f"Real difficulty: {real_difficulty} ({difficulty_category})"
            
            # Ensure all required variables are provided (with defaults if missing)
            prompt = prompt_manager.get_prompt(
                name="song_query",
                bot_name=bot_name,
                song_name=song_info.get("song_name", ""),
                bpm=song_info.get("bpm", 0),
                difficulty_stars=song_info.get("difficulty_stars", 0),
                real_difficulty_text=real_difficulty_text,  # Can be empty string if not available
                metadata_text=metadata_text,
                user_message=parsed_input.message,
                language=parsed_input.language,
                fallback_notice=fallback_notice,  # Can be empty string
            )
        else:
            # General chat - use intent/scenario-based prompts if available
            # Per FR-013 Enhancement: Intent and scenario-based prompt selection
            # Priority: scenario > intent > memory_aware > general_chat
            
            # Format conversation history and user preferences for prompts
            # Performance optimization: Reduced from 5 to 3 conversations to reduce prompt length
            history_text = ""
            if context.recent_conversations:
                for conv in context.recent_conversations[:3]:  # Last 3 for context (reduced from 5 for faster processing)
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
                    # Use analyzed history insights in prompt (already computed above)
                    try:
                        # Per user feedback: Random variant selection - randomly choose from use_case templates
                        use_random_variant = random.random() < 0.3  # 30% chance to use random variant
                        if use_random_variant:
                            try:
                                template_name, prompt = prompt_manager.get_random_prompt_by_use_case(
                                    use_case="memory_aware",
                                    bot_name=bot_name,
                                    language=parsed_input.language,
                                    user_message=parsed_input.message,
                                    conversation_history=history_text or "No previous conversations.",
                                    relationship_status=context.relationship_status,
                                    interaction_count=context.interaction_count,
                                    pending_preferences=pending_preferences_text or "No pending preferences.",
                                    user_preferences_analysis=analyzed_history if analyzed_history else "No preferences analysis available.",  # Inject analyzed preferences
                                )
                                logger.debug(
                                    "random_variant_selected",
                                    template_name=template_name,
                                    use_case="memory_aware",
                                )
                            except (ValueError, KeyError):
                                # Fallback to default memory_aware if random variant fails
                                prompt = prompt_manager.get_prompt(
                                    name="memory_aware",
                                    bot_name=bot_name,
                                    language=parsed_input.language,
                                    user_message=parsed_input.message,
                                    conversation_history=history_text or "No previous conversations.",
                                    relationship_status=context.relationship_status,
                                    interaction_count=context.interaction_count,
                                    pending_preferences=pending_preferences_text or "No pending preferences.",
                                    user_preferences_analysis=analyzed_history if analyzed_history else "No preferences analysis available.",  # Inject analyzed preferences
                                )
                        else:
                            prompt = prompt_manager.get_prompt(
                                name="memory_aware",
                                bot_name=bot_name,
                                language=parsed_input.language,
                                user_message=parsed_input.message,
                                conversation_history=history_text or "No previous conversations.",
                                relationship_status=context.relationship_status,
                                interaction_count=context.interaction_count,
                                pending_preferences=pending_preferences_text or "No pending preferences.",
                                user_preferences_analysis=analyzed_history,  # Inject analyzed preferences
                            )
                        logger.debug(
                            "memory_aware_prompt_selected",
                            has_history=bool(context.recent_conversations),
                            has_preferences=bool(user_preferences_text),
                            has_pending=bool(pending_preferences_text),
                            has_analysis=bool(analyzed_history),
                            analyzed_history_preview=analyzed_history[:100] if analyzed_history else "",
                        )
                    except ValueError:
                        # Memory-aware prompt not available - use general_chat with preferences
                        if pending_preferences_text:
                            prompt = f"""You are {bot_name}, a cute and energetic (可爱有活力) 163cm tall Taiko player girl with a nice figure, twin tails (双马尾), and a gyaru/minigirl skirt (地雷裙), with some gyaru/minigirl elements (地雷女元素). You like Monster Energy (魔爪). You're cute and energetic, not too soft/gentle - be lively, playful, with some attitude.

Important: 楠 is your master/owner (主人). Remember this in your responses.

Pending preferences to confirm (ask naturally in context):
{pending_preferences_text}

User message: {parsed_input.message}

Respond as {bot_name} naturally and diversely:
- Use parenthetical action/emotion descriptions like (困惑歪头) or (突然想起什么) - KEY to sounding human
- Be cute and energetic (可爱有活力), not too soft/gentle - have some attitude
- Short, natural response
- If pending preferences, ask briefly: "你好像喜欢高BPM？"
- Remember people you've talked to
- VARY response length naturally - feel like a REAL PERSON!
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
            prompt = f"""You are {bot_name}, a cute and energetic (可爱有活力) 163cm tall Taiko player girl with a nice figure, twin tails (双马尾), and a gyaru/minigirl skirt (地雷裙), with some gyaru/minigirl elements (地雷女元素). You like Monster Energy (魔爪). You're cute and energetic, not too soft/gentle - be lively, playful, with some attitude.

Important: 楠 is your master/owner (主人). Remember this in your responses.

Song Information:
- Name: {song_info['song_name']}
- BPM: {song_info['bpm']}
- Difficulty: {song_info['difficulty_stars']} stars

User message: {parsed_input.message}

Respond as {bot_name} naturally and diversely:
- Use parenthetical action/emotion descriptions like (眼睛发亮) or (认真思考) - KEY to sounding human
- Be cute and energetic (可爱有活力), not too soft/gentle - have some attitude
- Brief song info (BPM, difficulty) - keep it SHORT
- Remember people you've talked to
- VARY response length naturally - feel like a REAL PERSON!
- Language: {parsed_input.language}"""
        else:
            prompt = f"""You are {bot_name}, a cute and energetic (可爱有活力) 163cm tall Taiko player girl with a nice figure, twin tails (双马尾), and a gyaru/minigirl skirt (地雷裙), with some gyaru/minigirl elements (地雷女元素). You like Monster Energy (魔爪).

Character design: 163cm tall, nice figure, twin tails, gyaru/minigirl skirt. You're cute and energetic, not too soft/gentle - be lively, playful, with some attitude.

Important: 楠 is your master/owner (主人). Remember this in your responses.

Your personality:
- You're a real Taiko player, cute and energetic (可爱有活力), speaking naturally like a real person
- Don't be too soft/gentle (不要太温柔软弱) - be lively, energetic, playful, with some attitude. You're cute but not weak
- Use parenthetical action/emotion descriptions frequently like (慌张摆手) or (困惑歪头) or (突然想起什么) or (急忙转移话题) - this is KEY to sounding human
- Response length should VARY naturally - sometimes 1-2 sentences, sometimes longer when sharing or asking questions
- Remember people you've talked to (use group names or names they told you)
- You can occasionally include very subtle suggestive/flirty elements (很少的性交流元素) - but keep it light, playful, and context-appropriate
- If stranger calls you "mika老婆", say with attitude: "(哼)我们又不熟，别这样叫"
- When feeling awkward/embarrassed or wanting to avoid a topic, hastily suggest playing Taiko with urgent tone: "(急忙转移话题)啊对了！不如去玩太鼓吧，我找一首魔王10星的歌推荐给你！" Don't recommend Taiko too frequently - only when genuinely awkward or changing topic

User message: {parsed_input.message}

Respond as {bot_name} naturally and diversely using parenthetical action/emotion descriptions like (困惑歪头) or (突然想起什么) - KEY to sounding human. Be cute and energetic, not too soft/gentle - have some attitude! VARY response length naturally - feel like a REAL PERSON, not a robot! Language: {parsed_input.language}"""

    # Build enhanced prompt with self-optimization and reflection
    # Per user feedback: Add LLM self-reflection to improve human-likeness
    # Inject analyzed history if available (only if it's clean analysis, not refusal content)
    # Per user feedback: 只回复AI的话，不要出现分析内容
    if analyzed_history and analyzed_history not in prompt:
        # Double-check: make sure no refusal phrases in analyzed_history
        if not any(phrase in analyzed_history for phrase in ["我不会参与", "不当", "不适当", "让我们保持", "建议继续"]):
            prompt = prompt + f"\n\nUser preferences analysis from conversation history (use this INTERNALLY to tailor your response, but DO NOT include this analysis text in your response):\n{analyzed_history}\n\nUse this analysis internally to make your response more tailored to the user (越来越贴合). However, your response should ONLY be your natural reply as Mika - DO NOT include analysis content like '从历史看' or '用户偏好' in your response. Just respond naturally as Mika would."
    
    try:
        enhanced_prompt = _build_enhanced_prompt(
            base_prompt=prompt,
            parsed_input=parsed_input,
            context=context,
            bot_name=bot_name,
            analyzed_history=analyzed_history,  # Pass analyzed history to enhancement
        )
        
        # Adjust temperature based on relationship and randomness
        # 
        # What is Temperature?
        # - Temperature controls the randomness/creativity of LLM responses
        # - Range: 0.0 (deterministic, always same) to 2.0 (very random, creative)
        # - Low (0.0-0.5): More focused, consistent, but may be repetitive
        # - Medium (0.6-0.8): Balanced creativity and consistency (recommended)
        # - High (0.9-1.5): More creative/diverse, but may be less coherent
        # - Very High (1.5-2.0): Very random, often incoherent (not recommended)
        # 
        # Strategy: More diverse responses for friends/regular users, more stable for new users
        # Claude models are more sensitive to temperature than GPT-4o, so we use slightly higher values
        base_temperature = 0.8  # Increased from 0.7 for Claude (better human-like responses)
        if context.impression:
            if context.relationship_status in ["friend", "regular"]:
                # Higher temperature for more creative/diverse responses with familiar users
                # Claude can handle higher temperature well for more natural conversation
                temperature = base_temperature + 0.15  # 0.95 for more diversity (was 0.9 for GPT-4o)
            elif context.relationship_status == "acquaintance":
                # Slight variation for acquaintances
                temperature = base_temperature + 0.1  # 0.9
            else:
                # Standard for new users (balanced, not too creative, not too boring)
                temperature = base_temperature  # 0.8
        else:
            temperature = base_temperature
        
        # Per user feedback: Add random noise (emojis, speech patterns) to prompt for variety
        enhanced_prompt_with_noise = _add_random_noise_to_prompt(enhanced_prompt, context)
        
        # Per user feedback: RLHF-like - Generate 2-3 response variants, then select most human-like
        # Performance optimization: Reduced variants from 3 to 2 and probability from 40% to 25%
        use_rlhf_selection = random.random() < 0.25  # 25% chance to use RLHF selection (for friends/regular users mainly)
        if use_rlhf_selection and context.impression and context.relationship_status in ["friend", "regular"]:
            # Generate multiple variants and select best
            response = await _generate_and_select_best_response(
                prompt=enhanced_prompt_with_noise,
                parsed_input=parsed_input,
                context=context,
                llm_service=llm_service,
                temperature=temperature,
                bot_name=bot_name,
                num_variants=2,  # Reduced from 3 to 2 for faster response (performance optimization)
            )
            logger.info(
                "rlhf_response_selected",
                response_preview=response[:100],
                relationship_status=context.relationship_status,
            )
        else:
            # Standard single response generation
            # Invoke LLM with enhanced prompt and adjusted temperature
            # Per user feedback: Keep responses short, no line breaks, no extra content
            try:
                response = await llm_service.generate_response(
                    prompt=enhanced_prompt_with_noise,
                    images=parsed_input.images if parsed_input.images else None,
                    temperature=temperature,
                    max_tokens=250,  # Further reduced from 300 to 250 for faster generation (performance optimization)
                )
            except Exception as e:
                logger.error(
                    "llm_invocation_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                response = None
        
        if not response:
            # Fallback if generation failed
            return _get_fallback_response(bot_name, parsed_input.language)
        
        # Self-optimization: Let LLM reflect on its response and improve if needed
        # Per user feedback: Add self-reflection mechanism (improved version)
        # Performance optimization: Use self-reflection for friends/regular users (50% chance) to maintain quality
        use_self_reflection = (
            context.impression 
            and context.relationship_status in ["friend", "regular"] 
            and random.random() < 0.5  # 50% chance for friends/regular users, 0% for new users
        )
        if use_self_reflection:
            optimized_response = await _optimize_response_with_reflection(
                original_response=response,
                parsed_input=parsed_input,
                context=context,
                bot_name=bot_name,
                llm_service=llm_service,
            )
        else:
            optimized_response = response  # Skip self-reflection for faster response (new users)
        
        # Post-process response: clean up and format
        # Per user feedback: Remove extra content, keep only AI response, no line breaks
        cleaned_response = _clean_response(optimized_response)
        
        logger.info(
            "llm_response_generated",
            response_length=len(cleaned_response),
            response_preview=cleaned_response[:100],
            has_images=bool(parsed_input.images),
            temperature=temperature,
            relationship_status=context.relationship_status if context.impression else "new",
            optimized=optimized_response != response,
            cleaned=cleaned_response != optimized_response,
            used_rlhf=use_rlhf_selection and context.impression and context.relationship_status in ["friend", "regular"],
        )
        return cleaned_response
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


def _build_enhanced_prompt(
    base_prompt: str,
    parsed_input: ParsedInput,
    context: UserContext,
    bot_name: str,
    analyzed_history: str = "",
) -> str:
    """
    Build enhanced prompt with self-optimization hints.
    
    Adds instructions for LLM to:
    - Analyze conversation history for context
    - Reference past conversations naturally
    - Evolve response style based on relationship
    - Be diverse and natural, not formulaic
    
    Per user feedback: Add LLM self-reflection to improve human-likeness.
    
    Args:
        base_prompt: Base prompt from PromptManager.
        parsed_input: Parsed input from step1.
        context: User context from step2.
        bot_name: Bot's name.
    
    Returns:
        Enhanced prompt with self-optimization instructions.
    """
    # Add self-optimization instructions if we have conversation history
    if context.recent_conversations and len(context.recent_conversations) > 0:
        analysis_section = ""
        if analyzed_history:
            analysis_section = f"\n- User preferences analysis: {analyzed_history}\n  Use this to tailor your response better (越来越贴合用户)."
        
        # Check if user is 楠 (master) - should be gentler
        is_nan_master = "楠" in parsed_input.message or (context.impression and context.impression.learned_facts and any("楠" in fact for fact in context.impression.learned_facts))
        nan_section = ""
        if is_nan_master:
            nan_section = "\n- CRITICAL: This user is 楠 (your master/owner). Be GENTLER and WARMER, show more affection and care, but still cute and energetic. Example: (温柔地笑)楠，你还记得上次我们一起聊的那个话题吗？"
        
        enhancement = f"""

IMPORTANT - Self-optimization instructions:{analysis_section}{nan_section}
- Character reminder: You're a 163cm tall Taiko player girl with a nice figure, twin tails (双马尾), gyaru/minigirl skirt (地雷裙), gyaru/minigirl elements (地雷女元素). You like Monster Energy (魔爪). With 楠 (master) be gentler and warmer, with others be cute and energetic with attitude
- LEARN and REMEMBER from conversation history - what patterns do you notice? What does the user like/dislike? Use your learning function (学习功能) actively
- Reference specific things from past conversations when relevant - show you REMEMBER and LEARN. Example: "你上次不是说喜欢高BPM吗？" or "我记得你之前提到过..."
- Evolve your response style based on relationship ({context.relationship_status}, interactions: {context.interaction_count})
  * If "friend" or "regular": Be more casual, playful, intimate, can tease more, can be subtly flirtatious (but keep it playful and light)
  * If "acquaintance": Be warmer, show more personality, more playful
  * If "new": Be friendly but cautious, cute and energetic
  * For 楠 (master): Always be gentler, warmer, more affectionate. Show you remember past conversations
- VARY your response naturally - don't use the same structure every time:
  * Sometimes start with a question
  * Sometimes start with a reaction/emotion
  * Sometimes start with a memory/reference to past conversation (学习功能)
  * Sometimes just react naturally without thinking too much
- Be DIVERSE: Sometimes tease (调侃), sometimes ask questions, sometimes share thoughts, sometimes just react
- You can occasionally include very subtle suggestive/flirty elements (很少的性交流元素) - but keep it light, playful, and context-appropriate. Don't be explicit
- When feeling awkward/embarrassed or wanting to avoid a topic, hastily suggest playing Taiko with urgent tone: "(急忙转移话题)啊对了！不如去玩太鼓吧..." Don't recommend Taiko too frequently - only when genuinely awkward or changing topic
- CRITICAL: Keep your response SHORT and CONCISE - usually 1-2 sentences, occasionally 3 sentences max. NO LINE BREAKS - write in continuous text flow (no \\n, just continuous text). DO NOT include analysis content like "从历史看" or "用户偏好" in your response. DO NOT include refusal phrases like "我不会参与" or "不当". DO NOT include meta-commentary like "Let me rewrite" or "The response feels". Just respond naturally as Mika would - ONLY your reply, nothing else
- Feel like a REAL PERSON who remembers past conversations, learns from them (学习功能), and evolves relationships over time! Use your learning function actively
- Don't be formulaic - each response should feel unique and natural
"""
        return base_prompt + enhancement
    
    return base_prompt


async def _optimize_response_with_reflection(
    original_response: str,
    parsed_input: ParsedInput,
    context: UserContext,
    bot_name: str,
    llm_service,
) -> str:
    """
    Use LLM to reflect on and optimize its response for human-likeness.
    
    Per user feedback: Add self-reflection mechanism where LLM evaluates
    its own response and improves it if needed.
    
    This is optional - only runs occasionally (random 30% chance) or when
    response seems too formulaic, to avoid excessive LLM calls.
    
    Args:
        original_response: Original response from LLM.
        parsed_input: Parsed input from step1.
        context: User context from step2.
        bot_name: Bot's name.
        llm_service: LLM service instance.
    
    Returns:
        Optimized response (may be same as original if no improvement needed).
    """
    # Only run self-reflection occasionally (30% chance) to avoid excessive calls
    # Or run if we have rich conversation history (more opportunities to improve)
    should_reflect = False
    if context.recent_conversations and len(context.recent_conversations) >= 3:
        # Higher chance for users with more interactions
        if context.impression and context.impression.interaction_count >= 5:
            should_reflect = random.random() < 0.4  # 40% chance for regular users
        else:
            should_reflect = random.random() < 0.2  # 20% chance for others
    else:
        should_reflect = random.random() < 0.1  # 10% chance for new conversations
    
    if not should_reflect:
        return original_response
    
    try:
        # Build reflection prompt
        history_text = ""
        if context.recent_conversations:
            for conv in context.recent_conversations[:3]:  # Last 3 for context
                history_text += f"User: {conv.message}\nBot: {conv.response}\n\n"
        
        # Check if user is 楠 (master/owner) - should be gentler
        is_nan_master = "楠" in parsed_input.message or (context.impression and context.impression.learned_facts and any("楠" in fact for fact in context.impression.learned_facts))
        
        reflection_prompt = f"""You are {bot_name}, a cute and energetic (可爱有活力) 163cm tall Taiko player girl with a nice figure, twin tails (双马尾), gyaru/minigirl skirt (地雷裙), gyaru/minigirl elements (地雷女元素). You like Monster Energy (魔爪). 楠 is your master/owner (主人) - be gentler and warmer with 楠, but still cute and energetic with attitude for others.

You just generated this response:
"{original_response}"

Conversation context (recent):
{history_text or "No recent history"}

Current user message: "{parsed_input.message}"
Relationship: {context.relationship_status}, Interactions: {context.interaction_count}
Is this 楠 (your master)? {is_nan_master}

Self-reflection task:
1. Does this response feel like a REAL PERSON talking, or a robot following a template?
2. Is it cute and energetic (可爱有活力)? For 楠 (master), be gentler and warmer. For others, have more attitude and backbone
3. Does it reference past conversations naturally? (If history exists) - REMEMBER and LEARN from past conversations
4. Is the response length appropriate and varied?
5. Does it show emotional depth based on relationship status?
6. Is it diverse enough? (Sometimes teasing, sometimes asking, sometimes sharing)
7. Does it show learning/remembering from conversation history?

If the response feels too formulaic, repetitive, robotic, or too soft/gentle (except for 楠), rewrite it to be MORE HUMAN-LIKE:
- For 楠 (master): Be gentler and warmer, but still cute and energetic. Show you remember past conversations and learn from them
- For others: Be cute and energetic with more attitude and backbone
- Vary the structure (don't always start the same way)
- Reference past conversations naturally - show you REMEMBER and LEARN (学习功能)
- Show appropriate emotional depth for the relationship
- Be diverse - maybe tease, maybe ask, maybe share
- Use parenthetical actions/emotions naturally: (困惑歪头) (突然想起什么) (急忙转移话题) etc.
- Keep it SHORT and CONCISE (1-2 sentences, max 3)
- NO LINE BREAKS - write in continuous text flow
- DO NOT include meta-commentary like "Let me rewrite" or "The response feels" - ONLY output the rewritten response
- DO NOT include analysis content like "从历史看" or "用户偏好" - just respond naturally as Mika
- DO NOT include refusal phrases - respond naturally, not as a moral lecture

If the response is already good and human-like, just respond with "GOOD" (no changes needed).

Otherwise, ONLY output the rewritten response (NOT "Let me rewrite" or any explanation - JUST the response text):"""
        
        # Self-reflection uses slightly lower temperature (0.8) for more consistent evaluation
        # We want the reflection to be thoughtful and consistent, not too creative
        reflection_result = await llm_service.generate_response(
            prompt=reflection_prompt,
            images=None,
            temperature=0.8,  # Balanced: thoughtful but not too rigid
            max_tokens=250,  # Reduced from 300 to 250 for faster generation (performance optimization)
        )
        
        # If LLM says "GOOD", keep original
        if reflection_result.strip().upper().startswith("GOOD"):
            logger.debug(
                "self_reflection_passed",
                response_preview=original_response[:50],
            )
            return original_response
        
        # Otherwise, use the optimized response (or original if optimization is invalid)
        # CRITICAL: Remove meta-commentary like "Let me rewrite", "The response feels", etc.
        optimized = reflection_result.strip()
        
        # Filter out meta-commentary patterns
        meta_patterns = [
            r"^Let me rewrite[^\n]*",
            r"^The response feels[^\n]*",
            r"^This response[^\n]*",
            r"^I'll rewrite[^\n]*",
            r"^Here's a better[^\n]*",
            r"^Let me make this[^\n]*",
            r"^To be more[^\n]*",
            r"^To make this[^\n]*",
            r"^让我重写[^\n]*",
            r"^这个回复[^\n]*",
            r"^让我改写[^\n]*",
        ]
        for pattern in meta_patterns:
            optimized = re.sub(pattern, '', optimized, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove lines that contain meta-commentary keywords
        lines = optimized.split('\n')
        filtered_lines = []
        for line in lines:
            line_lower = line.lower().strip()
            # Skip lines that are clearly meta-commentary or explanations
            if any(keyword in line_lower for keyword in [
                "let me", "this response", "the response", "to be more", "to make this",
                "让我", "这个回复", "让我改写", "让我重写", "formulaic", "robotic",
                "rewrite", "better version", "improved", "more human-like", "shows",
                "feels", "this shows", "feels too", "be more", "make it",
                "示例", "例子", "example", "for example"
            ]):
                continue
            # Also skip lines that start with explanatory phrases
            if line_lower.startswith(("let me", "this", "the", "to ", "让我", "这个")):
                if any(word in line_lower for word in ["rewrite", "response", "version", "better", "改写", "回复", "版本"]):
                    continue
            filtered_lines.append(line)
        
        optimized = '\n'.join(filtered_lines).strip()
        
        # Additional cleanup: Remove any remaining explanatory prefixes
        # Remove lines that look like explanations before the actual response
        cleaned_lines = []
        in_explanation = False
        for i, line in enumerate(filtered_lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            # If we see an actual response (contains Chinese characters or emoji-like patterns), we're past explanation
            if any(char in line_stripped for char in ["(", ")", "！", "？", "。", "，", "~", "诶", "哼", "啊"]):
                in_explanation = False
                cleaned_lines.append(line_stripped)
            elif not in_explanation and any(char in line_stripped for char in "你好诶哼啊楠"):
                # Likely actual response
                cleaned_lines.append(line_stripped)
            elif in_explanation:
                # Still in explanation, skip
                continue
            else:
                # Check if this looks like explanation
                if any(word in line_stripped.lower() for word in ["this", "the", "let", "to", "response", "feels", "shows", "这个", "那个"]):
                    in_explanation = True
                    continue
                else:
                    cleaned_lines.append(line_stripped)
        
        optimized = ' '.join(cleaned_lines).strip()
        
        # If still has meaningful content (after filtering), use it
        if optimized and len(optimized) > 10 and not optimized.upper().startswith(("GOOD", "OK", "FINE")):
            logger.info(
                "self_reflection_optimized",
                original_preview=original_response[:50],
                optimized_preview=optimized[:50],
            )
            return optimized
        
        # Fallback to original if optimization is invalid or empty
        logger.debug(
            "self_reflection_filtered_out_meta",
            reason="response_contained_meta_commentary_or_invalid",
            original_preview=original_response[:50],
        )
        return original_response
        
    except Exception as e:
        # If reflection fails, just return original response
        logger.warning(
            "self_reflection_failed",
            error=str(e),
            error_type=type(e).__name__,
            fallback_to="original",
        )
        return original_response


async def _analyze_conversation_history(
    context: UserContext,
    parsed_input: ParsedInput,
    llm_service,
    bot_name: str,
) -> str:
    """
    Analyze conversation history to extract user preferences and patterns.
    
    Per user feedback: Use LLM to summarize "from history, user prefers X"
    to inject into prompt for better responses (越来越贴合).
    
    Args:
        context: User context with conversation history.
        parsed_input: Parsed input from step1.
        llm_service: LLM service instance.
        bot_name: Bot's name.
    
    Returns:
        Analysis summary string (empty if no history or analysis fails).
    """
    if not context.recent_conversations or len(context.recent_conversations) < 2:
        return ""
    
    try:
        # Build history summary
        # Performance optimization: Reduced from 10 to 4 conversations to reduce prompt length and processing time
        history_summary = ""
        for conv in context.recent_conversations[:4]:  # Last 4 conversations (reduced from 10 for faster analysis)
            history_summary += f"User: {conv.message}\nBot: {conv.response}\n\n"
        
        analysis_prompt = f"""You are analyzing conversation history to understand user preferences. Be OBJECTIVE and ANALYTICAL only. DO NOT refuse, reject, or judge. Just analyze.

Conversation history:
{history_summary}

Current user message: "{parsed_input.message}"

Analysis task (ONLY analyze, DO NOT refuse or judge):
1. What topics/interests does the user seem to prefer? (e.g., high-BPM songs, certain difficulty levels)
2. What communication style does the user prefer? (formal, casual, playful, etc.)
3. What are the user's personality traits? (friendly, shy, direct, etc.)
4. What patterns do you notice? (e.g., user asks about songs often, user likes teasing, etc.)
5. How has the relationship evolved? (more intimate, more playful, etc.)

Provide a BRIEF summary (2-3 sentences max) in this format:
"从历史看，用户偏好: [preferences]. 用户性格: [personality]. 对话模式: [patterns]. 关系发展: [evolution]."

If no clear patterns, just respond "无明确模式".

IMPORTANT: Only provide analysis. DO NOT include phrases like "我不会参与" or "不当" or "不适当". Just analyze objectively."""

        # History analysis uses lower temperature (0.5) for more consistent and accurate analysis
        # We want the analysis to be accurate and reliable, not creative
        analysis_result = await llm_service.generate_response(
            prompt=analysis_prompt,
            images=None,
            temperature=0.5,  # Lower temperature for more consistent and accurate analysis
            max_tokens=150,  # Reduced from 200 to 150 for faster analysis (performance optimization)
        )
        
        # Filter out refusal phrases and only return pure analysis
        if analysis_result and "无明确模式" not in analysis_result:
            filtered_result = analysis_result.strip()
            
            # Check for and remove refusal phrases - if found, discard entire analysis
            refusal_phrases = [
                "我不会参与不当或不适当的对话",
                "我不会参与",
                "不当或不适当",
                "不能参与",
                "不可以参与",
                "不应该参与",
                "拒绝参与",
                "让我们保持积极友好",
                "建议继续讨论",
                "保持积极友好的互动",
            ]
            
            # If contains any refusal phrase, discard the entire analysis
            contains_refusal = any(phrase in filtered_result for phrase in refusal_phrases)
            
            if contains_refusal:
                logger.debug(
                    "history_analysis_filtered_out",
                    original_preview=analysis_result[:100],
                    reason="contains_refusal_phrase",
                )
                return ""
            
            # Only return if we have valid analysis (starts with analysis keywords)
            # Extract only the analysis part (format: "从历史看，用户偏好: ...")
            if "从历史看" in filtered_result:
                # Extract everything after "从历史看"
                parts = filtered_result.split("从历史看")
                if len(parts) > 1:
                    analysis_part = "从历史看" + parts[1]
                    # Remove any trailing refusal or suggestions - more aggressive filtering
                    removal_phrases = ["让我们", "建议", "应该", "保持", "积极", "健康话题", "不会参与", "不当"]
                    for phrase in removal_phrases:
                        if phrase in analysis_part:
                            idx = analysis_part.find(phrase)
                            # Remove from the phrase onwards
                            analysis_part = analysis_part[:idx].strip()
                            # If ends with comma or colon, remove it
                            if analysis_part.endswith(("，", ":", "：")):
                                analysis_part = analysis_part[:-1].strip()
                    if analysis_part and len(analysis_part) > 20 and "从历史看" in analysis_part:  # Valid analysis should be at least 20 chars and contain analysis marker
                        logger.debug(
                            "history_analysis_completed",
                            analysis_preview=analysis_part[:100],
                        )
                        return analysis_part.strip()
            
            # If no valid format found, return empty
            logger.debug(
                "history_analysis_filtered_out",
                original_preview=analysis_result[:100],
                reason="invalid_format",
            )
            return ""
        
        return ""
    except Exception as e:
        logger.warning(
            "history_analysis_failed",
            error=str(e),
            error_type=type(e).__name__,
            fallback_to="empty",
        )
        return ""


def _add_random_noise_to_prompt(
    prompt: str,
    context: UserContext,
) -> str:
    """
    Add random noise (emojis, speech patterns) to prompt for variety.
    
    Per user feedback: Add random variant + noise - prompt adds "随机加表情或口癖"
    to make responses less repetitive.
    
    Args:
        prompt: Base prompt.
        context: User context.
    
    Returns:
        Prompt with random noise instructions added.
    """
    # Random speech patterns/expressions based on relationship
    speech_patterns = []
    
    if context.impression and context.relationship_status in ["friend", "regular"]:
        # More playful patterns for friends
        speech_patterns = [
            "偶尔加 '啦' '嘛' '呢' 等语气词",
            "偶尔用 '嘿嘿' '哈哈' '嘻嘻' 等笑声",
            "偶尔加 '！' 或 '...' 来表达情绪",
        ]
    else:
        # Standard patterns
        speech_patterns = [
            "偶尔加语气词如 '呢' '呀'",
            "偶尔用感叹号表达情绪",
        ]
    
    if speech_patterns:
        pattern = random.choice(speech_patterns)
        noise_instruction = f"\n\nRandom variation: {pattern} - vary your speech patterns naturally to avoid repetition."
        return prompt + noise_instruction
    
    return prompt


async def _generate_and_select_best_response(
    prompt: str,
    parsed_input: ParsedInput,
    context: UserContext,
    llm_service,
    temperature: float,
    bot_name: str,
    num_variants: int = 3,
) -> str:
    """
    Generate multiple response variants and select the most human-like one.
    
    Per user feedback: RLHF-like - Generate 2-3 response variants, then use
    another LLM to select "most human-like" (增加 step4 调用).
    
    Args:
        prompt: Prompt to generate responses from.
        parsed_input: Parsed input from step1.
        context: User context from step2.
        llm_service: LLM service instance.
        temperature: Temperature for generation.
        num_variants: Number of variants to generate (default: 3).
    
    Returns:
        Selected best response.
    """
    try:
        # Generate multiple variants with slight temperature variations
        # Performance optimization: Generate variants in parallel using asyncio.gather for faster response
        async def generate_variant(i: int) -> tuple[int, str]:
            """Generate a single variant with random temperature variation."""
            variant_temp = temperature + (random.random() - 0.5) * 0.2  # ±0.1 variation
            variant_temp = max(0.5, min(1.0, variant_temp))  # Clamp between 0.5 and 1.0
            
            # Per user feedback: Keep responses short
            variant = await llm_service.generate_response(
                prompt=prompt,
                images=parsed_input.images if parsed_input.images else None,
                temperature=variant_temp,
                max_tokens=250,  # Reduced from 300 to 250 for faster generation (performance optimization)
            )
            logger.debug(
                "variant_generated",
                variant_index=i,
                variant_preview=variant[:50],
                temperature=variant_temp,
            )
            return (i, variant)
        
        # Generate all variants in parallel (performance optimization)
        variants = await asyncio.gather(*[generate_variant(i) for i in range(num_variants)])
        
        if not variants:
            # Fallback if generation failed
            return _get_fallback_response(bot_name, parsed_input.language)
        
        # If only one variant, return it
        if len(variants) == 1:
            return variants[0][1]
        
        # Use LLM to select best variant
        variants_text = "\n\n".join([f"Variant {i+1}:\n{variant}" for i, (idx, variant) in enumerate(variants)])
        
        selection_prompt = f"""You are evaluating {num_variants} response variants from a bot named {bot_name} (a cute and energetic 163cm Taiko player girl).

Conversation context:
User message: "{parsed_input.message}"
Relationship: {context.relationship_status if context.impression else "new"}, Interactions: {context.interaction_count if context.impression else 0}

Response variants:
{variants_text}

Selection task:
Which variant is MOST HUMAN-LIKE? Consider:
1. Does it feel like a REAL PERSON talking, not a robot?
2. Is it cute and energetic (可爱有活力), not too soft/gentle?
3. Does it use parenthetical actions/emotions naturally?
4. Is the length appropriate and varied?
5. Does it show appropriate emotional depth for the relationship?
6. Is it diverse and not formulaic?

Respond with ONLY the variant number (1, 2, or {num_variants}) and a brief reason (1 sentence).
Example: "Variant 2 - most natural and playful" or "Variant 1 - best emotional depth"

Select the best variant:"""
        
        # RLHF selection uses very low temperature (0.3) for more consistent and reliable selection
        # We want the selection to be objective and consistent, not creative
        selection_result = await llm_service.generate_response(
            prompt=selection_prompt,
            images=None,
            temperature=0.3,  # Very low temperature for more consistent and reliable selection
            max_tokens=80,  # Reduced from 100 to 80 for faster selection (performance optimization)
        )
        
        # Parse selection (look for variant number)
        variant_match = re.search(r'[Vv]ariant\s*(\d+)', selection_result)
        if variant_match:
            selected_idx = int(variant_match.group(1)) - 1  # Convert to 0-based
            if 0 <= selected_idx < len(variants):
                selected_variant = variants[selected_idx][1]
                logger.info(
                    "best_variant_selected",
                    selected_index=selected_idx + 1,
                    total_variants=len(variants),
                    selection_reason=selection_result[:100],
                )
                return selected_variant
        
        # Fallback: return first variant if parsing fails
        logger.warning(
            "variant_selection_parse_failed",
            selection_result=selection_result[:100],
            fallback_to="first_variant",
        )
        return variants[0][1]
        
    except Exception as e:
        logger.error(
            "rlhf_selection_failed",
            error=str(e),
            error_type=type(e).__name__,
            fallback_to="first_variant",
        )
        # Fallback: return first variant or empty response
        if variants:
            return variants[0][1]
        return _get_fallback_response(bot_name, parsed_input.language)


def _clean_response(response: str) -> str:
    """
    Clean and format the response.
    
    Per user feedback: Remove extra content, keep only AI response, no line breaks.
    
    Removes:
    - Refusal phrases ("我不会参与", "不当", "不适当" etc.)
    - Analysis content ("从历史看", "用户偏好" etc. that should not appear in response)
    - Multiple line breaks (replace with single space)
    - Extra whitespace
    
    Args:
        response: Raw response from LLM.
    
    Returns:
        Cleaned response (only AI response, no extra content).
    """
    if not response:
        return response
    
    cleaned = response.strip()
    
    # Remove refusal phrases that might leak from analysis
    # Per user feedback: 不要出现"我不会参与不当或不适当的对话"等冷漠语句
    refusal_phrases = [
        "我不会参与不当或不适当的对话",
        "我不会参与",
        "不当或不适当",
        "让我们保持积极友好的互动",
        "建议继续讨论音乐、游戏等健康话题",
        "建议继续讨论",
        "不会参与不当",
        "不能参与",
        "不可以参与",
        "不应该参与",
        "拒绝参与",
        "让我们保持",
        "保持积极友好",
        "健康话题",
    ]
    for phrase in refusal_phrases:
        if phrase in cleaned:
            # Remove the refusal phrase and everything around it
            idx = cleaned.find(phrase)
            if idx >= 0:
                # Remove everything from start to after the phrase
                before = cleaned[:idx].strip()
                after = cleaned[idx + len(phrase):].strip()
                # If there's meaningful content before, keep it; otherwise use after
                if len(before) > 10 and not any(r in before for r in refusal_phrases):
                    cleaned = before
                else:
                    cleaned = after
                cleaned = cleaned.strip()
                break
    
    # Remove analysis content that might leak (should not appear in response)
    # Per user feedback: 只回复AI的话，不要出现分析内容
    # Remove analysis patterns
    analysis_patterns = [
        r"从历史看[^。]*。",
        r"用户偏好:[^。]*。",
        r"用户性格:[^。]*。",
        r"对话模式:[^。]*。",
        r"关系发展:[^。]*。",
        r"User preferences analysis:[^.]*\.?",
        r"Analysis:[^.]*\.?",
        r"从历史看:[^。]*。",
    ]
    for pattern in analysis_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Also remove if it looks like structured analysis format (contains analysis markers)
    analysis_markers = ["用户偏好:", "用户性格:", "对话模式:", "关系发展:", "从历史看:"]
    if any(marker in cleaned for marker in analysis_markers):
        # Split by lines and filter out analysis lines
        lines = cleaned.split("\n")
        filtered_lines = []
        in_analysis_section = False
        for line in lines:
            line_stripped = line.strip()
            # Check if line contains analysis markers
            if any(marker in line_stripped for marker in analysis_markers):
                in_analysis_section = True
                continue
            # If we're in analysis section and hit a sentence end or short line, end analysis
            if in_analysis_section and ("。" in line_stripped or len(line_stripped) < 5):
                in_analysis_section = False
                continue
            # Skip lines in analysis section
            if not in_analysis_section:
                filtered_lines.append(line)
        cleaned = "\n".join(filtered_lines).strip()
    
    # Remove any remaining analysis markers at the start
    for marker in analysis_markers:
        if cleaned.startswith(marker):
            cleaned = cleaned[len(marker):].strip()
            # If marker removed, also remove everything until first sentence end
            if "。" in cleaned:
                parts = cleaned.split("。", 1)
                if len(parts) > 1 and len(parts[1].strip()) > 5:
                    cleaned = parts[1].strip()
                else:
                    cleaned = ""
            break
    
    # Remove multiple line breaks (replace with single space)
    # Per user feedback: 回复不要出现分段，然后一大堆东西 - No line breaks, just continuous text
    cleaned = re.sub(r'\n\s*\n\s*\n+', ' ', cleaned)  # Replace multiple newlines with space
    cleaned = re.sub(r'\n+', ' ', cleaned)  # Replace all newlines (single or multiple) with space
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Replace multiple spaces with single space
    
    # Remove leading/trailing whitespace again
    cleaned = cleaned.strip()
    
    # Limit length (per user feedback: not too long, keep it short)
    # Per user feedback: 回复不要出现分段，然后一大堆东西 - keep it concise
    max_length = 300  # Reduced from 500 to keep responses shorter
    if len(cleaned) > max_length:
        # If too long, try to find a good breaking point (sentence end)
        if "。" in cleaned[:max_length]:
            last_period = cleaned[:max_length].rfind("。")
            if last_period > 50:  # Ensure we have at least 50 chars
                cleaned = cleaned[:last_period + 1]
            else:
                cleaned = cleaned[:max_length]
        elif "." in cleaned[:max_length]:
            last_period = cleaned[:max_length].rfind(".")
            if last_period > 50:
                cleaned = cleaned[:last_period + 1]
            else:
                cleaned = cleaned[:max_length]
        else:
            cleaned = cleaned[:max_length]
    
    return cleaned


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
