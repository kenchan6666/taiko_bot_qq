"""
Meme Search and Knowledge Service.

This module provides functionality for searching the web for internet
memes, slang, and cultural references, and storing their definitions
in the knowledge base.

Per user request: Mika should be able to search the web for internet
memes (e.g., "董卓", "吕布", "114514") and remember their definitions.
"""

import re
from typing import Optional

import structlog

from src.models.meme_knowledge import MemeKnowledge

logger = structlog.get_logger()


# Common internet meme patterns to detect
MEME_PATTERNS = [
    r"114514",  # 数字梗
    r"1919810",  # 数字梗
    r"董卓",  # 历史人物梗
    r"吕布",  # 历史人物梗
    r"抽象",  # 抽象文化
    r"典",  # 网络用语
    r"绷",  # 网络用语
    r"乐",  # 网络用语
]


def detect_meme_keywords(message: str) -> list[str]:
    """
    Detect potential meme keywords in a message.
    
    Args:
        message: User's message text.
        
    Returns:
        List of detected meme keywords.
    """
    detected = []
    message_lower = message.lower()
    
    # Check against known patterns
    for pattern in MEME_PATTERNS:
        matches = re.findall(pattern, message, re.IGNORECASE)
        if matches:
            detected.extend(matches)
    
    # Also check for standalone numbers that might be memes
    # (e.g., "114514", "1919810")
    number_memes = re.findall(r"\b(114514|1919810)\b", message)
    if number_memes:
        detected.extend(number_memes)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_detected = []
    for keyword in detected:
        if keyword not in seen:
            seen.add(keyword)
            unique_detected.append(keyword)
    
    return unique_detected


async def get_meme_definition(keyword: str) -> Optional[MemeKnowledge]:
    """
    Get meme definition from knowledge base.
    
    Args:
        keyword: Meme keyword to look up.
        
    Returns:
        MemeKnowledge document if found, None otherwise.
    """
    try:
        meme = await MemeKnowledge.find_one(MemeKnowledge.keyword == keyword)
        if meme:
            meme.increment_usage()
            await meme.save()
        return meme
    except Exception as e:
        logger.warning(
            "meme_lookup_failed",
            keyword=keyword,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


async def search_and_store_meme(keyword: str, search_results: str) -> Optional[MemeKnowledge]:
    """
    Search for meme definition and store it in knowledge base.
    
    This function should be called with web search results. It extracts
    a definition from the search results and stores it.
    
    Args:
        keyword: Meme keyword.
        search_results: Web search results text.
        
    Returns:
        MemeKnowledge document if successfully stored, None otherwise.
    """
    try:
        # Check if already exists
        existing = await get_meme_definition(keyword)
        if existing:
            return existing
        
        # Extract definition from search results (simplified - in practice,
        # you might want to use LLM to extract a concise definition)
        # For now, we'll store a summary of the search results
        definition = search_results[:500]  # Limit to 500 chars
        
        # Create new meme knowledge entry
        meme = MemeKnowledge(
            keyword=keyword,
            definition=definition,
            source="web_search",
            search_query=keyword,
        )
        
        await meme.save()
        
        logger.info(
            "meme_knowledge_stored",
            keyword=keyword,
            definition_length=len(definition),
        )
        
        return meme
    except Exception as e:
        logger.error(
            "meme_storage_failed",
            keyword=keyword,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


async def get_all_known_memes() -> list[str]:
    """
    Get all known meme keywords from knowledge base.
    
    Returns:
        List of all known meme keywords.
    """
    try:
        memes = await MemeKnowledge.find_all().to_list()
        return [meme.keyword for meme in memes]
    except Exception as e:
        logger.warning(
            "meme_list_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return []
