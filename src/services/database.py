"""
Database service module.

This module handles MongoDB connection and Beanie ODM initialization
for the Mika Taiko Chatbot application.

Per research.md: Initialize Beanie once at application startup with
async connection management.
"""

from typing import Optional

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import settings
from src.models.conversation import Conversation
from src.models.impression import Impression
from src.models.user import User


# Global MongoDB client instance
_client: Optional[AsyncIOMotorClient] = None


async def init_database() -> None:
    """
    Initialize Beanie ODM with MongoDB connection.

    This function should be called once at application startup.
    It establishes the MongoDB connection and initializes all
    Beanie document models.

    Per research.md: Initialize Beanie with init_beanie() at FastAPI startup.

    Raises:
        Exception: If MongoDB connection fails or initialization fails.
    """
    global _client

    # Create MongoDB client
    # Motor (async MongoDB driver) is used by Beanie
    _client = AsyncIOMotorClient(
        settings.mongodb_url,
        # Connection pool settings for high concurrency
        # Per NFR-002: Handle 100+ concurrent requests
        maxPoolSize=100,
        minPoolSize=10,
    )

    # Get database instance
    database = _client[settings.mongodb_database]

    # Initialize Beanie with all document models
    # This creates indexes and sets up the ODM
    await init_beanie(
        database=database,
        document_models=[
            User,
            Conversation,
            Impression,
        ],
    )


async def close_database() -> None:
    """
    Close MongoDB connection.

    This function should be called at application shutdown
    to properly close the database connection.
    """
    global _client

    if _client:
        _client.close()
        _client = None


def get_database_client() -> Optional[AsyncIOMotorClient]:
    """
    Get the MongoDB client instance.

    Returns:
        AsyncIOMotorClient instance, or None if not initialized.

    Note:
        This is primarily for advanced use cases. Most operations
        should use Beanie document models directly.
    """
    return _client
