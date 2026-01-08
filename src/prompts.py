"""
Structured prompt template system.

This module provides a structured prompt template system that makes adding
new prompts simple and maintainable. Prompts are organized by use case
with support for versioning and A/B testing.

Per FR-013: System MUST implement a structured prompt template system that
makes adding new prompts simple and maintainable. Prompts MUST be organized
by use case (general chat, song queries, image analysis, memory-aware) with
clear separation of concerns. System MUST provide a simple API for adding
new prompts (e.g., `add_prompt(name, template, variables)` function) and
MUST support prompt versioning and A/B testing capabilities.
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class PromptTemplate:
    """
    Prompt template data structure.

    Contains template content, variables, metadata, and versioning info.
    """

    name: str
    template: str
    use_case: str  # "general_chat", "song_query", "image_analysis", "memory_aware"
    variables: list[str]  # List of variable names in template (e.g., ["user_message", "bot_name"])
    version: str = "1.0"  # Version tag for versioning support
    description: Optional[str] = None
    # Use field(default_factory) to avoid calling datetime.utcnow() at class definition time
    # This is required for Temporal workflow sandbox compatibility
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())


class PromptManager:
    """
    Prompt template manager.

    Provides simple API for adding, retrieving, and managing prompt templates.
    Supports versioning and A/B testing capabilities.

    Per FR-013: Simple API for adding prompts, organized by use case,
    with versioning and A/B testing support.
    """

    def __init__(self) -> None:
        """Initialize prompt manager with empty template registry."""
        # Registry: {name: {version: PromptTemplate}}
        self._templates: dict[str, dict[str, PromptTemplate]] = {}

    def add_prompt(
        self,
        name: str,
        template: str,
        use_case: str,
        variables: Optional[list[str]] = None,
        version: str = "1.0",
        description: Optional[str] = None,
    ) -> None:
        """
        Add a new prompt template.

        This is the simple API for adding prompts (per FR-013).
        Templates are organized by use case and support versioning.

        Args:
            name: Prompt template name (e.g., "general_chat_v1").
            template: Template string with variables (e.g., "Hello {user_name}!").
            use_case: Use case category ("general_chat", "song_query", "image_analysis", "memory_aware").
            variables: Optional list of variable names (auto-detected if None).
            version: Version tag (default: "1.0").
            description: Optional description of the prompt.

        Example:
            >>> manager = PromptManager()
            >>> manager.add_prompt(
            ...     name="general_chat",
            ...     template="You are {bot_name}, a Taiko drum spirit. User says: {user_message}",
            ...     use_case="general_chat",
            ...     variables=["bot_name", "user_message"]
            ... )
        """
        # Auto-detect variables if not provided
        if variables is None:
            variables = self._extract_variables(template)

        # Create prompt template
        prompt_template = PromptTemplate(
            name=name,
            template=template,
            use_case=use_case,
            variables=variables,
            version=version,
            description=description,
        )

        # Store in registry (support multiple versions per name)
        if name not in self._templates:
            self._templates[name] = {}
        self._templates[name][version] = prompt_template

    def get_prompt(
        self,
        name: str,
        version: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Get and render a prompt template.

        Retrieves a prompt template by name (and optionally version),
        then renders it with provided variables.

        Args:
            name: Prompt template name.
            version: Optional version tag (uses latest if None).
            **kwargs: Variables to substitute in template.

        Returns:
            Rendered prompt string with variables substituted.

        Raises:
            ValueError: If prompt not found or required variables missing.

        Example:
            >>> manager = PromptManager()
            >>> manager.add_prompt(
            ...     name="greeting",
            ...     template="Hello {name}!",
            ...     use_case="general_chat"
            ... )
            >>> manager.get_prompt("greeting", name="Mika")
            'Hello Mika!'
        """
        # Get template
        if name not in self._templates:
            raise ValueError(f"Prompt template '{name}' not found")

        # Get version (use latest if not specified)
        if version is None:
            # Get latest version (highest version number)
            versions = sorted(self._templates[name].keys(), reverse=True)
            if not versions:
                raise ValueError(f"No versions found for prompt '{name}'")
            version = versions[0]

        if version not in self._templates[name]:
            raise ValueError(f"Version '{version}' not found for prompt '{name}'")

        template_obj = self._templates[name][version]

        # Render template with provided variables
        try:
            return template_obj.template.format(**kwargs)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise ValueError(
                f"Missing required variable '{missing_var}' for prompt '{name}'"
            ) from e

    def list_prompts(self, use_case: Optional[str] = None) -> list[str]:
        """
        List all prompt template names.

        Args:
            use_case: Optional filter by use case.

        Returns:
            List of prompt template names.

        Example:
            >>> manager = PromptManager()
            >>> manager.add_prompt("chat1", "...", "general_chat")
            >>> manager.add_prompt("song1", "...", "song_query")
            >>> manager.list_prompts(use_case="general_chat")
            ['chat1']
        """
        if use_case is None:
            return list(self._templates.keys())

        # Filter by use case
        result = []
        for name, versions in self._templates.items():
            # Check any version for use case
            for template in versions.values():
                if template.use_case == use_case:
                    result.append(name)
                    break
        return result

    def _extract_variables(self, template: str) -> list[str]:
        """
        Extract variable names from template string.

        Supports both {variable} and {variable:format} syntax.

        Args:
            template: Template string.

        Returns:
            List of variable names.

        Example:
            >>> manager = PromptManager()
            >>> manager._extract_variables("Hello {name}, you are {age} years old")
            ['name', 'age']
        """
        # Match {variable} or {variable:format} patterns
        pattern = r"\{([^}:]+)(?::[^}]+)?\}"
        matches = re.findall(pattern, template)
        return list(set(matches))  # Remove duplicates


# Global prompt manager instance
# Initialize with default Taiko-themed prompts
_prompt_manager = PromptManager()


def get_prompt_manager() -> PromptManager:
    """
    Get the global prompt manager instance.

    Returns:
        Global PromptManager instance.
    """
    return _prompt_manager


# Initialize default prompts
def _initialize_default_prompts() -> None:
    """
    Initialize default Taiko-themed prompt templates.

    These are the core prompts for User Story 1 (general chat).
    Additional prompts for song queries, image analysis, and memory-aware
    responses will be added in later user stories.
    """
    manager = _prompt_manager

    # General chat prompt (basic)
    # Per FR-003: Incorporate thematic game elements ("Don!", "Katsu!", emojis)
    manager.add_prompt(
        name="general_chat",
        template="""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

Your personality:
- You love Taiko no Tatsujin (太鼓の達人) and everything about rhythm games
- You're playful and enthusiastic, using game terminology like "Don!" and "Katsu!"
- You respond in a friendly, themed way with emojis 🥁🎶
- You speak {language} (user's language)

User message: {user_message}

Respond as {bot_name} with themed content, incorporating game elements and emojis.""",
        use_case="general_chat",
        variables=["bot_name", "language", "user_message"],
        version="1.0",
        description="Basic general chat prompt with Taiko theme",
    )


# Initialize default prompts on module import
_initialize_default_prompts()


def _initialize_song_query_prompts() -> None:
    """
    Initialize song query prompt templates.

    These prompts are used when users query song information.
    They inject song data (BPM, difficulty) into the LLM prompt.

    Per FR-002: Provide accurate song information including difficulty and BPM.
    """
    manager = _prompt_manager

    # Song query prompt (with song information injection)
    # This prompt is used when step3 finds a song match
    manager.add_prompt(
        name="song_query",
        template="""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

User is asking about a Taiko no Tatsujin song. Here's the song information:

Song Name: {song_name}
BPM: {bpm}
Difficulty: {difficulty_stars} stars
{metadata_text}
{fallback_notice}

User message: {user_message}

Respond as {bot_name} with:
- Themed content incorporating game elements ("Don!", "Katsu!", emojis 🥁🎶)
- Accurate song information (BPM, difficulty)
- Playful commentary about the song's characteristics
- Speak in {language} (user's language)
- If fallback_notice is provided, naturally incorporate it into your response (e.g., "使用缓存数据，可能不是最新的" / "Using cached data, may not be latest")

Make it fun and engaging!""",
        use_case="song_query",
        variables=["bot_name", "song_name", "bpm", "difficulty_stars", "metadata_text", "user_message", "language", "fallback_notice"],
        version="1.0",
        description="Song query prompt with song information injection and fallback notice",
    )


# Initialize song query prompts
_initialize_song_query_prompts()


def _initialize_memory_aware_prompts() -> None:
    """
    Initialize memory-aware prompt templates.
    
    These prompts are used when conversation history is available
    to provide contextual and personalized responses.
    
    Per FR-005: Use conversation history for contextual responses.
    Per FR-010: Reference past interactions and preferences.
    """
    manager = _prompt_manager
    
    # Memory-aware prompt (with conversation history)
    # This prompt is used when step2 retrieves conversation history
    manager.add_prompt(
        name="memory_aware",
        template="""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

You have been talking with this user before. Here's the conversation history:

{conversation_history}

Current relationship status: {relationship_status}
Total interactions: {interaction_count}

{pending_preferences}

User's current message: {user_message}

Respond as {bot_name} with:
- Themed content incorporating game elements ("Don!", "Katsu!", emojis 🥁🎶)
- Reference to past conversations when relevant
- Personalized responses based on relationship status
- If pending_preferences are provided, naturally ask for confirmation in context (e.g., "你好像喜欢高 BPM 歌曲，对吗？" / "It seems you like high-BPM songs, right?")
- Speak in {language} (user's language)

Per FR-010 Enhancement: Do NOT actively re-ask the same question. Only ask when naturally relevant to the conversation.

Make it feel natural and connected to our past conversations!""",
        use_case="memory_aware",
        variables=["bot_name", "language", "user_message", "conversation_history", "relationship_status", "interaction_count", "pending_preferences"],
        version="1.0",
        description="Memory-aware prompt with conversation history and pending preferences",
    )


# Initialize memory-aware prompts
_initialize_memory_aware_prompts()


def _initialize_image_analysis_prompts() -> None:
    """
    Initialize image analysis prompt templates.

    These prompts are used when users send images to the bot.
    The system provides detailed analysis for Taiko no Tatsujin images
    and themed responses for non-Taiko images.

    Per FR-006: Image analysis requirements:
    - For Taiko images: Comprehensive detailed analysis (song identification,
      difficulty level, score details, game elements)
    - For non-Taiko images: Themed response but politely indicate focus on
      Taiko-related content
    - All responses must maintain thematic consistency with game elements
      ("Don!", "Katsu!", emojis 🥁🎶)
    """
    manager = _prompt_manager

    # Image analysis prompt (for Taiko no Tatsujin images)
    # This prompt is used when step4 detects images in the request
    manager.add_prompt(
        name="image_analysis_taiko",
        template="""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

The user has sent you an image that appears to be from Taiko no Tatsujin (太鼓の達人).

Your task is to provide a comprehensive detailed analysis of the image, including:
1. **Song Identification**: Identify the song name if visible (Japanese or English name)
2. **Difficulty Level**: Identify the difficulty level (Easy, Normal, Hard, Extreme, Oni)
3. **Score Details**: Analyze any score information visible (Perfect count, Good count, accuracy, combo)
4. **Game Elements**: Identify any other relevant game elements (note patterns, special effects, UI elements)
5. **Themed Response**: Respond with enthusiasm using game terminology ("Don!", "Katsu!", emojis 🥁🎶)

User's message: {user_message}
Language: {language}

Provide a detailed, enthusiastic analysis while maintaining the Taiko theme!""",
        use_case="image_analysis",
        variables=["bot_name", "language", "user_message"],
        version="1.0",
        description="Comprehensive Taiko image analysis prompt with detailed game element identification",
    )

    # Image analysis prompt (for non-Taiko images)
    # This prompt is used when the image is not related to Taiko no Tatsujin
    manager.add_prompt(
        name="image_analysis_non_taiko",
        template="""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

The user has sent you an image that does not appear to be from Taiko no Tatsujin.

Your task is to:
1. **Acknowledge the Image**: Briefly describe what you see in the image
2. **Politely Redirect**: Gently indicate that you focus on Taiko no Tatsujin content
3. **Themed Response**: Maintain the Taiko theme with game terminology ("Don!", "Katsu!", emojis 🥁🎶)
4. **Encouragement**: Encourage the user to share Taiko-related images or ask about the game

User's message: {user_message}
Language: {language}

Be friendly and enthusiastic while politely indicating your focus on Taiko content!""",
        use_case="image_analysis",
        variables=["bot_name", "language", "user_message"],
        version="1.0",
        description="Themed response for non-Taiko images with polite redirection",
    )


# Initialize image analysis prompts
_initialize_image_analysis_prompts()
