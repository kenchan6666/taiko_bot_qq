"""
Database initialization script.

This script initializes the MongoDB database for the Mika Taiko Chatbot,
creating indexes and verifying the connection.

Usage:
    python scripts/init_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.services.database import close_database, init_database


async def main() -> None:
    """
    Main function to initialize the database.

    Creates indexes and verifies connection.
    """
    print("Initializing MongoDB database...")
    print(f"Database URL: {settings.mongodb_url}")
    print(f"Database Name: {settings.mongodb_database}")

    try:
        # Initialize Beanie (creates indexes automatically)
        await init_database()
        print("✅ Database initialized successfully!")
        print("✅ Indexes created for all collections.")
        print("\nCollections initialized:")
        print("  - users (with unique index on hashed_user_id)")
        print("  - conversations (with indexes on user_id, expires_at)")
        print("  - impressions (with unique index on user_id)")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

    finally:
        # Close connection
        await close_database()
        print("\n✅ Database connection closed.")


if __name__ == "__main__":
    # Run async main function
    asyncio.run(main())
