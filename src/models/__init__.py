"""
Data models module.

This module contains Beanie ODM models for:
- User: QQ user with hashed ID and preferences
- Conversation: Message interactions (90-day retention)
- Impression: Bot's memory of users
- Song: Taiko no Tatsujin song data
- MemeKnowledge: Internet meme and slang definitions
"""

from src.models.meme_knowledge import MemeKnowledge

__all__ = ["MemeKnowledge"]
