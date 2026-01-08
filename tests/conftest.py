"""
Pytest configuration and fixtures for Mika Taiko Chatbot tests.

This module provides shared fixtures and test configuration,
including Beanie database initialization for testing.
"""

import pytest
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.models.conversation import Conversation
from src.models.impression import Impression
from src.models.user import User


@pytest.fixture(scope="function")
async def test_database():
    """
    Initialize Beanie with a test MongoDB database.
    
    Uses a separate test database to avoid interfering with
    development/production data. The database is cleaned up
    after each test.
    
    Yields:
        Database instance for testing.
    """
    # Use test database (different from production)
    # For testing, you can use:
    # 1. A real MongoDB instance with a test database name
    # 2. mongomock (in-memory MongoDB mock) - requires mongomock package
    # 3. A test container (via docker-compose)
    
    # Option 1: Use real MongoDB with test database
    # This requires MongoDB to be running (e.g., via docker-compose)
    test_mongodb_url = "mongodb://localhost:27017/"
    test_database_name = "mika_bot_test"
    
    # Create MongoDB client for testing
    client = AsyncIOMotorClient(test_mongodb_url)
    database = client[test_database_name]
    
    # Initialize Beanie with test database
    await init_beanie(
        database=database,
        document_models=[
            User,
            Conversation,
            Impression,
        ],
    )
    
    yield database
    
    # Cleanup: Drop test database after test
    await client.drop_database(test_database_name)
    client.close()


@pytest.fixture
async def cleanup_test_data(test_database):
    """
    Clean up test data before each test.
    
    This fixture should be used explicitly in integration tests
    that need a clean database state. It clears all collections
    in the test database.
    
    Args:
        test_database: Test database instance from test_database fixture.
    """
    # Clear all collections before each test
    await User.delete_all()
    await Conversation.delete_all()
    await Impression.delete_all()
    
    yield
    
    # Optional: Clean up after test as well
    # (Usually not needed since we clean before each test)


@pytest.fixture
def mock_beanie_init(monkeypatch):
    """
    Mock Beanie initialization for tests that don't need real database.
    
    This fixture patches Beanie's internal methods to avoid
    CollectionWasNotInitialized errors when creating document instances
    without full database initialization.
    
    Use this fixture for unit tests that only test model methods
    without database operations.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    from bson import ObjectId
    from unittest.mock import AsyncMock, MagicMock
    
    # Create a valid ObjectId for mocking
    mock_object_id = ObjectId()
    
    # Create a mock collection with async methods
    mock_collection = MagicMock()
    # insert_one should return a result with inserted_id as ObjectId
    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = mock_object_id
    mock_collection.insert_one = AsyncMock(return_value=mock_insert_result)
    mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    # find_one_and_update should return a document dict (not None) for save() to merge
    # Beanie's save() calls update() which calls find_one_and_update, then merges the result
    # We need to return a dict that can be parsed into the model
    # The dict should contain all required fields to avoid validation errors
    # 
    # Note: Beanie's update() method calls find_one_and_update with the find query as first arg
    # The find query is typically {"_id": document_id} for updates
    # We can't infer model type from just {"_id": ...}, so we return ALL possible fields
    # Beanie will merge this with the actual document, and Pydantic will ignore extra fields
    from datetime import datetime
    
    def mock_find_one_and_update(*args, **kwargs):
        # Extract the find query - first argument is the query dict
        find_query = args[0] if args else {}
        
        # Extract _id from query, ensuring it's a valid ObjectId
        # Beanie may process the _id through bson_encoders, which might return MagicMock
        # We always use a valid ObjectId to avoid validation errors
        query_id = find_query.get("_id")
        # Always use mock_object_id to ensure it's a valid ObjectId
        # Even if query has an _id, it might be a MagicMock from Beanie's processing
        result_id = mock_object_id
        
        # Return dict with ALL possible fields from all models
        # This ensures all required fields are present for any model
        # Pydantic will ignore extra fields that don't belong to the model
        result = {
            "_id": result_id,  # Always use a valid ObjectId
            # User required fields
            "hashed_user_id": "mock_user_hash",
            "preferred_language": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            # Impression required fields
            "user_id": "mock_user_hash",
            "relationship_status": "new",
            "interaction_count": 0,
            "preferences": {},
            "pending_preferences": {},
            "last_interaction": datetime.utcnow(),
            "learned_facts": [],
            # Conversation required fields
            "group_id": "mock_group",
            "message": "",
            "response": "",
            "timestamp": datetime.utcnow(),
            "expires_at": None,
        }
        
        return result
    
    mock_collection.find_one_and_update = AsyncMock(side_effect=mock_find_one_and_update)
    mock_collection.find_one = AsyncMock(return_value=None)
    mock_collection.find = MagicMock()
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=0))
    
    # Create a mock settings object
    mock_settings = MagicMock()
    mock_settings.motor_collection = mock_collection
    mock_settings.use_revision = False
    mock_settings.keep_nulls = False
    
    # Mock get_settings to return our mock settings
    def mock_get_settings(cls):
        return mock_settings
    
    # Patch all document models' get_settings class method
    # This prevents Beanie from trying to access the real database
    monkeypatch.setattr("src.models.user.User.get_settings", classmethod(mock_get_settings))
    monkeypatch.setattr("src.models.conversation.Conversation.get_settings", classmethod(mock_get_settings))
    monkeypatch.setattr("src.models.impression.Impression.get_settings", classmethod(mock_get_settings))
    
    # Mock get_motor_collection as a classmethod
    # Beanie calls it as a class method: DocumentModel.get_motor_collection()
    def mock_get_motor_collection(cls):
        return mock_collection
    
    # Patch as classmethod
    monkeypatch.setattr("src.models.user.User.get_motor_collection", classmethod(mock_get_motor_collection))
    monkeypatch.setattr("src.models.conversation.Conversation.get_motor_collection", classmethod(mock_get_motor_collection))
    monkeypatch.setattr("src.models.impression.Impression.get_motor_collection", classmethod(mock_get_motor_collection))
    
    yield
    
    # Cleanup is automatic with monkeypatch
