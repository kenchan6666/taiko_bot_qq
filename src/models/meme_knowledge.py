"""
Meme Knowledge Base model.

This module defines the MemeKnowledge model for storing definitions
of internet memes, slang, and cultural references that Mika learns
through web searches.

Per user request: Mika should be able to search the web for internet
memes (e.g., "董卓", "吕布", "114514") and remember their definitions.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class MemeKnowledge(Document):
    """
    Meme Knowledge model representing definitions of internet memes and slang.
    
    Stores definitions of internet memes, cultural references, and slang
    that Mika learns through web searches. This is a global knowledge base
    shared across all users.
    
    Attributes:
        keyword: The meme/slang keyword (e.g., "董卓", "114514", "吕布").
        definition: The definition/explanation of the meme.
        source: Source of the definition (e.g., "web_search", "user_taught").
        search_query: The original search query used to find this definition.
        learned_at: Timestamp when this knowledge was learned.
        usage_count: Number of times this meme has been referenced.
    """
    
    # The meme/slang keyword (unique, indexed)
    keyword: str
    
    # The definition/explanation
    definition: str
    
    # Source of the definition
    source: str = "web_search"  # "web_search" or "user_taught"
    
    # Original search query used to find this definition
    search_query: Optional[str] = None
    
    # Timestamp when this knowledge was learned
    learned_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    
    # Number of times this meme has been referenced
    usage_count: int = 0
    
    class Settings:
        """Beanie document settings."""
        
        # Collection name in MongoDB
        name = "meme_knowledge"
        
        # Indexes for fast queries
        indexes = [
            [("keyword", 1)],  # Unique index on keyword
        ]
    
    def increment_usage(self) -> None:
        """Increment usage count."""
        self.usage_count += 1
        self.learned_at = datetime.utcnow()  # Update timestamp on usage
