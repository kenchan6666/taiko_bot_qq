# Data Model: Mika Taiko Chatbot

**Feature**: `1-mika-bot`  
**Date**: 2026-01-08  
**Status**: Complete

This document defines the data models for the Mika Taiko Chatbot system using Beanie ODM.

## Entity Overview

The system uses four main entities:
1. **User**: Represents a QQ user (identified by hashed QQ user ID)
2. **Conversation**: Represents a single interaction (auto-deleted after 90 days)
3. **Impression**: Represents the bot's memory/understanding of a user
4. **Song**: Represents a Taiko no Tatsujin song (cached from taikowiki)

## Entity Definitions

### 1. User

**Purpose**: Store user identity, preferences, and language settings.

**Attributes**:
- `hashed_user_id` (str, required, unique): SHA-256 hash of QQ user ID
- `preferred_language` (Optional[str]): User's preferred language ("zh", "en", or None for auto-detect)
- `created_at` (datetime): Account creation timestamp
- `updated_at` (datetime): Last update timestamp

**Indexes**:
- Unique index on `hashed_user_id` for fast lookups

**Validation Rules**:
- `hashed_user_id` must be 64-character hex string (SHA-256)
- `preferred_language` must be "zh", "en", or None

**Relationships**:
- 1:1 with Impression
- 1:N with Conversation (conversations auto-deleted after 90 days)

**Beanie Model**:
```python
from beanie import Document, Indexed
from datetime import datetime
from typing import Optional

class User(Document):
    hashed_user_id: Indexed(str, unique=True)
    preferred_language: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    
    class Settings:
        name = "users"
        indexes = [
            [("hashed_user_id", 1)],  # Unique index
        ]
```

---

### 2. Conversation

**Purpose**: Store individual message interactions for context retrieval.

**Attributes**:
- `user_id` (str, required): Reference to User.hashed_user_id
- `group_id` (str, required): QQ group ID where message was sent
- `message` (str, required): User's message content
- `response` (str, required): Bot's response
- `images` (Optional[List[str]]): Base64-encoded images if any
- `timestamp` (datetime): Message timestamp
- `expires_at` (datetime): Auto-deletion date (90 days from timestamp)

**Indexes**:
- Index on `user_id` for fast user history retrieval
- Index on `expires_at` for cleanup job efficiency
- Compound index on `(user_id, timestamp)` for chronological queries

**Validation Rules**:
- `message` and `response` must be non-empty strings
- `expires_at` must be exactly 90 days after `timestamp`

**Relationships**:
- N:1 with User (many conversations per user)

**Auto-Deletion**:
- Conversations are automatically deleted after 90 days via cleanup job
- Cleanup job runs daily, deletes conversations where `expires_at < now()`

**Beanie Model**:
```python
from beanie import Document, Indexed
from datetime import datetime, timedelta
from typing import Optional, List

class Conversation(Document):
    user_id: Indexed(str)  # References User.hashed_user_id
    group_id: str
    message: str
    response: str
    images: Optional[List[str]] = None
    timestamp: datetime = datetime.utcnow()
    expires_at: datetime  # Auto-set to timestamp + 90 days
    
    class Settings:
        name = "conversations"
        indexes = [
            [("user_id", 1)],
            [("expires_at", 1)],
            [("user_id", 1), ("timestamp", -1)],  # Compound index
        ]
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.expires_at:
            self.expires_at = self.timestamp + timedelta(days=90)
```

---

### 3. Impression

**Purpose**: Store the bot's "memory" or understanding of a user for personalized responses.

**Attributes**:
- `user_id` (str, required, unique): Reference to User.hashed_user_id (1:1 relationship)
- `preferences` (dict): Learned preferences (e.g., `{"favorite_bpm_range": "high", "favorite_difficulty": "extreme"}`)
- `relationship_status` (str): Relationship level ("new", "acquaintance", "friend", "regular")
- `interaction_count` (int): Total number of interactions
- `last_interaction` (datetime): Timestamp of last interaction
- `learned_facts` (List[str]): List of facts learned about user (e.g., "likes high-BPM songs")

**Indexes**:
- Unique index on `user_id` (enforces 1:1 with User)

**Validation Rules**:
- `relationship_status` must be one of: "new", "acquaintance", "friend", "regular"
- `interaction_count` must be >= 0
- `preferences` must be a valid JSON-serializable dict

**State Transitions**:
- `relationship_status` updates based on `interaction_count`:
  - 0-2: "new"
  - 3-10: "acquaintance"
  - 11-50: "friend"
  - 51+: "regular"

**Relationships**:
- 1:1 with User (one impression per user)

**Beanie Model**:
```python
from beanie import Document, Indexed
from datetime import datetime
from typing import List, Dict, Any

class Impression(Document):
    user_id: Indexed(str, unique=True)  # 1:1 with User
    preferences: Dict[str, Any] = {}
    relationship_status: str = "new"  # new, acquaintance, friend, regular
    interaction_count: int = 0
    last_interaction: datetime = datetime.utcnow()
    learned_facts: List[str] = []
    
    class Settings:
        name = "impressions"
        indexes = [
            [("user_id", 1)],  # Unique index
        ]
    
    def update_relationship_status(self):
        """Update relationship status based on interaction count."""
        if self.interaction_count < 3:
            self.relationship_status = "new"
        elif self.interaction_count < 11:
            self.relationship_status = "acquaintance"
        elif self.interaction_count < 51:
            self.relationship_status = "friend"
        else:
            self.relationship_status = "regular"
```

---

### 4. Song

**Purpose**: Cache song data from taikowiki for fast queries.

**Attributes**:
- `name` (str, required): Song name
- `difficulty_stars` (int): Difficulty rating (1-10 stars)
- `bpm` (int): Beats per minute
- `metadata` (dict): Additional metadata (genre, artist, etc.)
- `cached_at` (datetime): When song was cached
- `source` (str): Source identifier ("taikowiki")

**Indexes**:
- Text index on `name` for fuzzy matching
- Index on `difficulty_stars` for filtering
- Index on `bpm` for filtering

**Validation Rules**:
- `difficulty_stars` must be between 1 and 10
- `bpm` must be > 0
- `name` must be non-empty

**Note**: Songs are cached in memory for fast access. MongoDB storage is optional for persistence across restarts.

**Beanie Model** (optional, for persistence):
```python
from beanie import Document, Indexed
from datetime import datetime
from typing import Dict, Any

class Song(Document):
    name: Indexed(str)
    difficulty_stars: int
    bpm: int
    metadata: Dict[str, Any] = {}
    cached_at: datetime = datetime.utcnow()
    source: str = "taikowiki"
    
    class Settings:
        name = "songs"
        indexes = [
            [("name", "text")],  # Text index for fuzzy matching
            [("difficulty_stars", 1)],
            [("bpm", 1)],
        ]
```

**In-Memory Representation** (primary):
```python
# Songs stored as list of dicts in memory for fast access
songs_cache: List[Dict[str, Any]] = []
```

---

## Data Flow

### User Registration Flow
1. User sends message in QQ group
2. System hashes QQ user ID → `hashed_user_id`
3. Check if User exists with `hashed_user_id`
4. If not exists, create User and Impression records
5. Process message and create Conversation record

### Message Processing Flow
1. Receive message → hash user ID
2. Retrieve User and Impression via `hashed_user_id` (step2)
3. Create Conversation record with message/response (step5)
4. Update Impression (interaction_count++, learned_facts, preferences)
5. Conversation auto-expires after 90 days

### Cleanup Flow
1. Daily cleanup job runs
2. Query conversations where `expires_at < now()`
3. Delete expired conversations in bulk
4. Log cleanup statistics

## Privacy Considerations

- **User Identification**: Only hashed QQ user IDs stored (never plaintext)
- **Data Retention**: Conversations auto-deleted after 90 days
- **User Preferences**: Retained permanently until user explicitly requests deletion
- **Cross-Group Recognition**: Enabled via hashed_user_id (same user across groups)
- **GDPR Compliance**: No data sharing without consent; user can request data deletion

## Migration Strategy

1. **Initial Setup**: Create indexes on existing collections
2. **Data Migration**: N/A (new system, no existing data)
3. **Backward Compatibility**: N/A (new feature)

## Performance Considerations

- **Indexes**: All foreign keys and frequently queried fields indexed
- **Query Optimization**: Use compound indexes for common query patterns
- **Bulk Operations**: Use `delete_many()` for cleanup job efficiency
- **Connection Pooling**: Beanie uses Motor's connection pooling automatically

---

**Next Steps**: See `contracts/` for API definitions and `quickstart.md` for setup instructions.
