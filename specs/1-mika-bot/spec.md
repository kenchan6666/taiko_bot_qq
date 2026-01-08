# Feature Specification: Mika Taiko Chatbot

**Feature Branch**: `1-mika-bot`  
**Created**: 2026-01-08  
**Status**: Draft  
**Input**: User description: "Develop a Taiko no Tatsujin themed QQ chatbot named 'Mika', using LangBot for QQ integration and a custom FastAPI backend for advanced logic..."

## Clarifications

### Session 2026-01-08

- Q: How should the system uniquely identify and distinguish different QQ users? This affects data model design, privacy compliance, and cross-group user recognition. → A: Use hashed QQ user ID as unique identifier (balances privacy and functional requirements, enables cross-group memory while protecting user privacy)
- Q: What is the data retention period for user conversation history and preference data? When should old data be automatically deleted or archived? → A: Conversation history retained for 90 days, user preferences retained permanently until user explicitly requests deletion (balances memory functionality with privacy compliance and storage cost control)
- Q: What are the specific rate limiting thresholds? How many requests per user, per group, per minute/hour are allowed? → A: 20 requests per user per minute, 50 requests per group per minute. System MUST implement high-quality concurrent multi-threaded code to handle high concurrency efficiently
- Q: What are the specific standards for "harmful or inappropriate content"? What types of content should be filtered? → A: Filter excessive hatred (including ethnic hatred), political topics, and religious content. Allow normal game-related discussions while blocking divisive or inflammatory content
- Q: How should the system detect or determine user language preferences for multi-language responses? → A: System MUST automatically detect user message language, but MUST also allow users to explicitly specify their preferred language. This balances automation with user control for better UX
- Q: How should API keys and sensitive credentials be managed in configuration? → A: All API keys MUST be loaded from environment variables via config.py using os.getenv(). Configuration files MUST contain placeholder values only (leave API keys empty/blank), with actual secrets provided via environment variables. This ensures no hard-coded secrets in codebase and enables secure deployment
- Q: What logging functionality should the system implement? This is critical for debugging, monitoring, and operational visibility. → A: System MUST implement a structured logging system that records all critical events (errors, warnings, info, debug) with structured fields (user ID, request ID, timestamp, operation type, etc.). Logs MUST support aggregation and querying for debugging, performance monitoring, and audit purposes. Log format MUST be JSON for machine parsing and MUST include contextual information without exposing sensitive user data
- Q: What monitoring and observability capabilities should the system implement beyond logging? This affects operational readiness and production deployment. → A: System MUST implement basic monitoring metrics including request rate, error rate, response time, and system resource usage (CPU, memory). Metrics MUST be accessible via health check endpoints (/health) and metrics export endpoints. This provides essential operational visibility without the complexity of full distributed tracing
- Q: How should content filtering be implemented? This affects system architecture and cost considerations. → A: System MUST implement intelligent content filtering using a hybrid approach: first use keyword/phrase lists for fast filtering of obviously inappropriate content, then use LLM judgment for ambiguous cases. This balances accuracy, cost efficiency, and performance while reducing false positives
- Q: What caching strategy should be used for the song database (taikowiki JSON)? This affects performance and cost. → A: System MUST implement in-memory caching with periodic refresh (e.g., hourly) for song data. Queries MUST prioritize cached data for fast response times, with automatic background refresh to maintain data freshness. This balances performance optimization with data currency requirements
- Q: How should Temporal workflow retry strategies be configured? This affects system reliability and error recovery capabilities. → A: System MUST implement exponential backoff retry strategy for Temporal workflows (e.g., 1s, 2s, 4s, 8s intervals) with a maximum of 5 retry attempts. This provides resilience against transient failures while preventing excessive retry overhead and ensures eventual consistency
- Q: What limitations should be imposed on multi-modal image processing? This affects system performance and resource usage. → A: System MUST implement reasonable image size limits (e.g., maximum 10MB) and format restrictions (JPEG, PNG, WebP). When images exceed limits or use unsupported formats, system MUST return user-friendly, themed error messages (e.g., "图片太大啦！" with thematic elements). Comprehensive prompt engineering will be implemented for detailed image analysis and response generation
- Q: How should prompt templates be organized and managed to make adding new prompts simple and maintainable? This affects development workflow and prompt iteration efficiency. → A: System MUST implement a structured prompt template system using Python string templates or a template engine (e.g., Jinja2) with clear separation of concerns. Prompts MUST be organized by use case (general chat, song queries, image analysis, memory-aware) in a single `src/prompts.py` file or a `src/prompts/` directory with individual template files. System MUST provide a simple API for adding new prompts (e.g., `add_prompt(name, template, variables)` function) and MUST support prompt versioning and A/B testing capabilities. This enables easy prompt iteration without code changes and facilitates prompt engineering best practices
- Q: What testing scripts and utilities should the system provide? This affects development workflow, testing efficiency, and quality assurance capabilities. → A: System MUST implement comprehensive testing infrastructure including: (1) Automated test suite using pytest with unit tests and integration tests covering all user stories and edge cases, (2) Test utilities including pytest fixtures for common test data (mock users, conversations, songs) and mocks for external services (OpenRouter API, taikowiki, MongoDB), (3) Manual testing scripts in `scripts/` directory for quick functional verification (e.g., `scripts/test_webhook.py` for testing LangBot webhook endpoint, `scripts/test_song_query.py` for testing song queries). This provides both automated quality assurance and developer-friendly manual testing tools for rapid iteration
- Q: Which services must run continuously in Docker Compose deployment? This affects deployment architecture, operational requirements, and system availability. → A: System MUST run the following services continuously in Docker Compose: (1) FastAPI backend + Temporal client (must handle webhooks, call gpt-4o, execute 5-step chain), (2) Temporal server + PostgreSQL (workflow engine must be online to schedule tasks and retries), (3) MongoDB (must store user history and impressions; downtime causes memory loss). Nginx is strongly recommended for long-running reverse proxy, HTTPS, and load balancing to provide stable public network entry point. External services that must also run continuously (deployed separately): LangBot (core bot platform must receive QQ messages and manage triggers, connects to FastAPI backend via webhook), Napcat (QQ protocol layer must keep bot account online; downtime prevents message reception, deployed separately or as part of LangBot). All listed services are critical for system functionality and any service downtime will cause functional failures
- Q: How should the system extract and learn user preferences from conversations? This affects User Story 3 memory implementation and user experience. → A: System MUST use LLM to automatically analyze conversation content and extract user preferences (e.g., favorite song types, BPM preferences). However, before updating the user's Impression with learned preferences, the system MUST ask the user for confirmation in the bot's response (e.g., "你好像喜欢高 BPM 歌曲，对吗？" / "It seems you like high-BPM songs, right?"). This balances automation with accuracy and aligns with FR-010 (inform users when bot learns information). The system MUST prioritize explicit confirmation (user replies with "是", "对", "yes", "correct", etc.). If explicit confirmation is not received, the system MAY accept implicit confirmation if the user continues the conversation assuming the preference is correct (e.g., continues discussing high-BPM songs after being asked about the preference). Only after user confirms (explicitly or implicitly) should preferences be permanently stored in the Impression model
- Q: What level of detail should image analysis provide? This affects User Story 4 multi-modal implementation and user experience. → A: System MUST perform detailed analysis of all images. For Taiko no Tatsujin related images (gameplay screenshots, song selection screens, etc.), the system MUST provide comprehensive analysis including song identification, difficulty level, score details, and other relevant game elements. For non-Taiko related images, the system MUST still provide a themed response but politely indicate that the bot focuses on Taiko-related content. All responses MUST maintain thematic consistency with game elements ("Don!", "Katsu!", emojis 🥁🎶) per FR-003. This provides value for both Taiko and non-Taiko images while maintaining the bot's thematic identity
- Q: How should the system handle multiple song matches from fuzzy matching? This affects User Story 2 song query implementation and user experience. → A: When fuzzy matching finds multiple potential song matches, the system MUST return only the single best match (highest similarity score) and ask the user for confirmation in the response (e.g., "你是指《XXX》吗？" / "Did you mean 'XXX'?"). This prevents information overload while ensuring accuracy. The confirmation request MUST be included in the themed response with game elements per FR-003. If the user confirms or continues the conversation assuming the match is correct, the system proceeds with that song. If the user indicates it's not the correct song, the system can offer alternative matches or ask for clarification
- Q: Should the conversation history limit (currently "last 10 conversations") be configurable? This affects User Story 3 memory implementation and future flexibility. → A: System MUST support configuration of conversation history limit via environment variable (e.g., `CONVERSATION_HISTORY_LIMIT`) with a default value of 10. This allows future flexibility to adjust context window size based on performance requirements, LLM token limits, or user needs. The configuration MUST be loaded from config.py using environment variables per NFR-009. This enables future optimization without code changes
- Q: What specific fallback strategies should the system use when external services (LLM, song database) are unavailable? This affects error recovery and user experience. → A: System MUST use cached data or default responses when services are unavailable, and MUST notify users in the response (e.g., "使用缓存数据，可能不是最新的" / "Using cached data, may not be latest"). Song database uses local JSON file (data/database.json) as primary source with periodic refresh from taikowiki. LLM fallback strategy: system may support local LLM models in the future as an alternative to OpenRouter API. This provides graceful degradation while maintaining functionality
- Q: What fallback strategy should the system use when intent detection fails or is uncertain? This affects prompt selection and response quality. → A: When intent detection fails or is uncertain, system MUST fallback to use_case-based prompt selection (infer use_case from message content: general_chat, song_query, image_analysis, memory_aware). System MUST log intent detection failures for analysis and improvement. This ensures functionality while enabling continuous improvement of intent classification accuracy
- Q: How should the system handle rapid consecutive messages from the same user (e.g., 3 messages within 1 second)? This affects message processing order, system load, and user experience. → A: System MUST process messages in order, but MUST skip duplicate or highly similar messages (deduplication). This ensures message order is preserved while avoiding redundant processing of duplicate content, improving efficiency and reducing costs. Similarity threshold and deduplication window (e.g., within 5 seconds) should be configurable
- Q: How should the system handle unconfirmed preference requests when users do not respond for extended periods (e.g., 24+ hours)? This affects User Story 3 memory implementation and data persistence. → A: System MUST retain unconfirmed preferences in pending state but MUST NOT actively re-ask the same question. System MUST wait for users to mention related topics in future conversations, then re-confirm the preference naturally in context. This avoids annoying users with repeated questions while preserving the opportunity for natural confirmation when relevant
- Q: What is the primary data source for song database and how should local JSON file (data/database.json) be used? This affects FR-002 implementation and data freshness. → A: taikowiki API is the PRIMARY data source. System MUST fetch from taikowiki API first and update local JSON file (data/database.json) periodically (e.g., hourly) for caching. Local JSON file is used ONLY as fallback when taikowiki API is unavailable. When updating local file, system SHOULD replace existing data to ensure consistency with API source. This ensures data freshness while providing resilience through local cache

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Interactive Chatbot Conversations (Priority: P1)

Users in QQ groups can interact with a themed chatbot named "Mika" that responds to queries about Taiko no Tatsujin songs, provides game-related information, and engages in playful conversations with thematic elements.

**Why this priority**: This is the core value proposition - enabling users to have engaging, themed conversations with the bot. Without this, the feature has no purpose.

**Independent Test**: Can be fully tested by sending messages to the bot in a QQ group and verifying it responds appropriately with themed content. Delivers immediate value through interactive entertainment.

**Acceptance Scenarios**:

1. **Given** a user sends a message mentioning "Mika" in a QQ group, **When** the message contains a song query, **Then** the bot responds with relevant song information including difficulty and BPM details
2. **Given** a user sends a message mentioning "Mika" in a QQ group, **When** the message is a general conversation, **Then** the bot responds with playful, themed content incorporating game elements like "Don!", "Katsu!", and emojis
3. **Given** a user sends a message without mentioning "Mika", **When** the message is processed, **Then** the bot does not respond to prevent spam

---

### User Story 2 - Song Information Queries (Priority: P1)

Users can query information about Taiko no Tatsujin songs, including difficulty ratings, BPM (beats per minute), and receive contextual comments about song characteristics.

**Why this priority**: Song queries are a primary use case that provides concrete value to users interested in the game. This functionality differentiates the bot from generic chatbots.

**Independent Test**: Can be fully tested by querying specific songs and verifying accurate information is returned with appropriate difficulty and BPM context. Delivers value through accurate game information.

**Acceptance Scenarios**:

1. **Given** a user asks about a specific song name, **When** the song exists in the database, **Then** the bot provides song details including difficulty rating (e.g., "10-star extreme challenge") and BPM (e.g., "300+ super fast")
2. **Given** a user asks about a song with a partial or misspelled name, **When** the query is processed, **Then** the bot uses fuzzy matching to find the best match (highest similarity score) and asks the user for confirmation (e.g., "你是指《XXX》吗？" / "Did you mean 'XXX'?") before providing song details. The confirmation request MUST be included in a themed response with game elements per FR-003
3. **Given** a user asks about a song that doesn't exist, **When** the query is processed, **Then** the bot gracefully handles the error with a helpful, themed response

---

### User Story 3 - Contextual Conversations with Memory (Priority: P2)

The bot remembers previous interactions with users and can reference past conversations, preferences, and relationships to provide more personalized and contextually relevant responses.

**Why this priority**: Memory capabilities enhance user experience by making conversations feel more natural and personalized, but the core functionality (P1 stories) can work without it.

**Independent Test**: Can be fully tested by having multiple conversations with the bot and verifying it references previous interactions appropriately. Delivers value through improved user engagement.

**Acceptance Scenarios**:

1. **Given** a user has previously discussed their preference for high-BPM songs, **When** the user asks for song recommendations, **Then** the bot references this preference in its response
2. **Given** a user has had multiple conversations with the bot, **When** the user asks a follow-up question, **Then** the bot can reference context from previous interactions
3. **Given** the bot detects a potential user preference from conversation (e.g., user mentions liking high-BPM songs), **When** it extracts this preference, **Then** it asks the user for confirmation in the response (e.g., "你好像喜欢高 BPM 歌曲，对吗？" / "It seems you like high-BPM songs, right?") before permanently storing it in the Impression. The system MUST prioritize explicit confirmation (user replies with "是", "对", "yes", "correct", etc.). If explicit confirmation is not received, the system MAY accept implicit confirmation if the user continues the conversation assuming the preference is correct. Only after user confirms (explicitly or implicitly) should the preference be stored

---

### User Story 4 - Multi-Modal Content Support (Priority: P2)

Users can share images (such as Taiko no Tatsujin screenshots) with the bot and receive relevant descriptions, analysis, or themed responses about the visual content.

**Why this priority**: Multi-modal support enhances the bot's capabilities and user engagement, but text-only functionality (P1) provides core value independently.

**Independent Test**: Can be fully tested by sending images to the bot and verifying it provides relevant, themed responses about the visual content. Delivers value through enhanced interaction capabilities.

**Acceptance Scenarios**:

1. **Given** a user sends an image of a Taiko no Tatsujin gameplay screenshot, **When** the bot processes the image, **Then** it provides detailed analysis including song identification, difficulty level, score details, and other relevant game elements, all with themed responses incorporating game elements ("Don!", "Katsu!", emojis 🥁🎶)
2. **Given** a user sends a non-game-related image, **When** the bot processes the image, **Then** it provides a themed response with game elements but politely indicates that the bot focuses on Taiko-related content

---

### Edge Cases

- What happens when the bot is called by name in multiple groups simultaneously?
- How does the system handle network failures when querying the song database?
- What happens when the LLM service is unavailable or times out?
- How does the bot handle messages with harmful or inappropriate content? (Content filtering blocks excessive hatred including ethnic hatred, political topics, and religious content per FR-007)
- What happens when a user queries a song name that matches multiple songs in the database?
- How does the system handle very long conversation histories that exceed storage limits? (Conversation history is automatically deleted after 90 days per FR-005)
- What happens when the bot receives messages faster than it can process them? (Rate limiting: 20 requests/user/minute, 50 requests/group/minute. High-quality concurrent multi-threaded architecture handles queuing and processing)
- How does the system handle malformed or invalid input from users?
- What happens when a user sends an image that exceeds size limits or uses an unsupported format? (System returns user-friendly, themed error messages like "图片太大啦！" per FR-006)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST only respond to messages that explicitly mention the bot's name ("Mika" or recognized variants like "mika", "米卡", "Mika酱")
- **FR-002**: System MUST provide accurate information about Taiko no Tatsujin songs when queried, including difficulty ratings and BPM. taikowiki API is the PRIMARY data source. System MUST fetch from taikowiki API first and update local JSON file (data/database.json) periodically (e.g., hourly) for caching. Local JSON file is used ONLY as fallback when taikowiki API is unavailable. System MUST implement in-memory caching with periodic refresh (e.g., hourly) for song data. Queries MUST prioritize cached data for fast response times, with automatic background refresh to maintain data freshness. When updating local file, system SHOULD replace existing data to ensure consistency with API source
- **FR-003**: System MUST incorporate thematic game elements (e.g., "Don!", "Katsu!", emojis 🥁🎶) in all responses to maintain consistency
- **FR-004**: System MUST support fuzzy matching for song name queries to handle partial or misspelled names. When fuzzy matching finds multiple potential matches, the system MUST return only the single best match (highest similarity score) and ask the user for confirmation in the response (e.g., "你是指《XXX》吗？" / "Did you mean 'XXX'?") before providing song details. The confirmation request MUST be included in a themed response with game elements per FR-003. This prevents information overload while ensuring accuracy
- **FR-005**: System MUST store and retrieve user conversation history and preferences to enable contextual responses. Conversation history MUST be automatically deleted after 90 days, while user preferences are retained permanently until user explicitly requests deletion. The number of recent conversations retrieved for context (conversation history limit) MUST be configurable via environment variable (e.g., `CONVERSATION_HISTORY_LIMIT`) with a default value of 10. This allows future flexibility to adjust context window size based on performance requirements, LLM token limits, or user needs. The configuration MUST be loaded from config.py using environment variables per NFR-009
- **FR-006**: System MUST support processing of both text and image content in user messages. Image processing MUST enforce reasonable limits: maximum file size (e.g., 10MB) and supported formats (JPEG, PNG, WebP). When images exceed limits or use unsupported formats, system MUST return user-friendly, themed error messages (e.g., "图片太大啦！" with thematic game elements). For Taiko no Tatsujin related images, the system MUST provide comprehensive detailed analysis including song identification, difficulty level, score details, and other relevant game elements. For non-Taiko related images, the system MUST still provide a themed response but politely indicate that the bot focuses on Taiko-related content. All image analysis responses MUST maintain thematic consistency with game elements ("Don!", "Katsu!", emojis 🥁🎶) per FR-003. Comprehensive prompt engineering MUST be implemented for detailed image analysis and themed response generation
- **FR-013**: System MUST implement a structured prompt template system that makes adding new prompts simple and maintainable. Prompts MUST be organized hierarchically: use_case (general_chat, song_query, image_analysis, memory_aware) → intent (greeting, help, goodbye, preference_confirmation, song_query, song_recommendation, difficulty_advice, game_tips, etc.) → scenario (optional, for specific contexts). System MUST provide a simple API for adding new prompts (e.g., `add_prompt(name, template, variables, use_case, intent, scenario)` function) and MUST support prompt versioning and A/B testing capabilities. Prompt templates MUST use Python string templates or a template engine (e.g., Jinja2) for variable substitution. When intent detection fails or is uncertain, system MUST fallback to use_case-based prompt selection (infer use_case from message content) and MUST log intent detection failures for analysis and improvement. This enables easy prompt iteration without code changes and facilitates prompt engineering best practices
- **FR-007**: System MUST filter out harmful or inappropriate content before processing or responding. Content filtering MUST block: excessive hatred (including ethnic hatred), political topics, and religious content. Normal game-related discussions are allowed while divisive or inflammatory content is blocked
- **FR-008**: System MUST handle multiple concurrent requests from different QQ groups without failures. When the same user sends rapid consecutive messages, system MUST process messages in order but MUST skip duplicate or highly similar messages (deduplication) to avoid redundant processing. Similarity threshold and deduplication window (e.g., within 5 seconds) MUST be configurable via environment variables
- **FR-009**: System MUST gracefully degrade when external services (song database, LLM) are unavailable. When services fail after retries, system MUST use cached data or default themed responses and MUST notify users in the response (e.g., "使用缓存数据，可能不是最新的" / "Using cached data, may not be latest"). Song database uses local JSON file (data/database.json) as primary source with periodic refresh from taikowiki. LLM fallback: system may support local LLM models in the future as an alternative to OpenRouter API. Temporal workflows MUST implement exponential backoff retry strategy (e.g., 1s, 2s, 4s, 8s intervals) with a maximum of 5 retry attempts for transient failures. This provides resilience against temporary service unavailability while preventing excessive retry overhead
- **FR-010**: System MUST inform users when the bot learns or remembers information about them. When the system automatically extracts user preferences from conversations using LLM analysis, it MUST ask the user for confirmation before permanently storing preferences in the Impression model. The confirmation request MUST be included in the bot's response (e.g., "你好像喜欢高 BPM 歌曲，对吗？" / "It seems you like high-BPM songs, right?"). The system MUST prioritize explicit confirmation (user replies with "是", "对", "yes", "correct", etc.). If explicit confirmation is not received, the system MAY accept implicit confirmation if the user continues the conversation assuming the preference is correct (e.g., continues discussing high-BPM songs after being asked about the preference). Only after user confirms (explicitly or implicitly) should preferences be permanently stored. If users do not respond to confirmation requests, system MUST retain unconfirmed preferences in pending state but MUST NOT actively re-ask the same question. System MUST wait for users to mention related topics in future conversations, then re-confirm the preference naturally in context. This balances automation with accuracy and ensures user awareness of what information is being learned while avoiding annoying users with repeated questions
- **FR-011**: System MUST respect user privacy by storing only necessary data for bot functionality. User identification MUST use hashed QQ user IDs (not plaintext) to enable cross-group memory while protecting privacy
- **FR-012**: System MUST support rate limiting to prevent abuse in large group environments. Rate limits: 20 requests per user per minute, 50 requests per group per minute. System MUST implement high-quality concurrent multi-threaded code architecture to efficiently handle high concurrency scenarios

### Non-Functional Requirements

- **NFR-001**: System MUST respond to user queries within 3 seconds under normal load conditions
- **NFR-002**: System MUST handle at least 100 concurrent requests without performance degradation. Implementation MUST use high-quality concurrent multi-threaded code patterns to ensure efficient resource utilization and thread safety
- **NFR-003**: System MUST maintain 99%+ uptime during normal operation periods
- **NFR-004**: System MUST implement error handling that logs errors without exposing technical details to users
- **NFR-010**: System MUST implement structured logging for all critical events (errors, warnings, info, debug levels). Logs MUST be in JSON format with structured fields including: user ID (hashed), request ID, timestamp, operation type, log level, message, and contextual metadata. Logs MUST support aggregation and querying for debugging, performance monitoring, and audit purposes. System MUST NOT log sensitive user data (plaintext user IDs, API keys, or personal information). Log retention and rotation policies MUST be configurable via environment variables
- **NFR-011**: System MUST implement basic monitoring metrics including: request rate (requests per second), error rate (errors per second), response time (p50, p95, p99 percentiles), and system resource usage (CPU, memory). Metrics MUST be accessible via health check endpoint (/health) and metrics export endpoint (e.g., /metrics in Prometheus format). This provides essential operational visibility for production deployment and troubleshooting
- **NFR-005**: System MUST support deployment across multiple QQ groups with appropriate isolation
- **NFR-006**: System MUST comply with privacy principles similar to GDPR (no data sharing without consent)
- **NFR-007**: System MUST be culturally sensitive and respectful of Japanese origins of Taiko no Tatsujin
- **NFR-008**: System MUST provide responses in multiple languages when requested (e.g., Chinese, English). System MUST automatically detect user message language, but MUST also allow users to explicitly specify their preferred language
- **NFR-009**: System MUST NOT hard-code API keys or sensitive credentials. All API keys (e.g., OpenRouter API key, MongoDB connection strings) MUST be loaded from environment variables via config.py using os.getenv(). Configuration files MUST contain placeholder values only, with actual secrets provided via environment variables
- **NFR-012**: System MUST implement comprehensive testing infrastructure including: (1) Automated test suite using pytest with unit tests (tests/unit/) and integration tests (tests/integration/) covering all user stories, edge cases, and error scenarios with target coverage of 80%+, (2) Test utilities including pytest fixtures (tests/fixtures/) for common test data (mock users, conversations, songs) and mocks for external services (OpenRouter API, taikowiki, MongoDB), (3) Manual testing scripts in `scripts/` directory for quick functional verification (e.g., `scripts/test_webhook.py` for testing LangBot webhook endpoint, `scripts/test_song_query.py` for testing song queries). This provides both automated quality assurance and developer-friendly manual testing tools for rapid iteration and debugging
- **NFR-013**: System MUST run all infrastructure services continuously in production deployment. Required services include: FastAPI backend + Temporal client (webhook handling, LLM calls, 5-step processing), Temporal server + PostgreSQL (workflow orchestration and retries), MongoDB (data persistence). External services that must also run continuously: LangBot (QQ message reception, deployed separately, connects via webhook), and Napcat (QQ protocol connection, deployed separately or as part of LangBot). Nginx is strongly recommended for reverse proxy, HTTPS, and load balancing. All listed services are critical for system functionality; any service downtime will cause functional failures. Docker Compose deployment MUST ensure all services start and remain running with appropriate health checks and restart policies. Note: LangBot and Napcat are deployed as external services (not in this project's Docker Compose), but must be configured to connect to the FastAPI backend webhook endpoint

### Key Entities

- **User**: Represents a QQ user who interacts with the bot. Key attributes include hashed QQ user ID (unique identifier for privacy-compliant cross-group recognition), conversation history, preferences (e.g., favorite song types, BPM preferences), and relationship data with the bot.
- **Conversation**: Represents a single interaction session between a user and the bot. Key attributes include message content, timestamp, context, and bot response. Conversations are automatically deleted after 90 days to balance memory functionality with privacy and storage requirements.
- **Song**: Represents a Taiko no Tatsujin song from the database. Key attributes include song name, difficulty rating (stars), BPM, and metadata.
- **Impression**: Represents the bot's "memory" or understanding of a user. Key attributes include preferences learned, relationship status, and interaction patterns.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users receive bot responses within 3 seconds for 95% of queries under normal load
- **SC-002**: System successfully handles 100 concurrent requests from different QQ groups without errors
- **SC-003**: 90% of song queries return accurate information with appropriate difficulty and BPM context
- **SC-004**: Bot correctly identifies when it is called by name (true positive rate > 95%) and ignores messages without name mentions (true negative rate > 98%)
- **SC-005**: Users report positive engagement with themed responses (measured through continued interaction rates)
- **SC-006**: System maintains conversation context across multiple interactions for 80% of active users
- **SC-007**: Multi-modal image processing successfully analyzes and responds to 85% of relevant Taiko-related images
- **SC-008**: System gracefully handles service failures with user-friendly error messages in 100% of failure scenarios
- **SC-009**: Privacy compliance: Zero instances of unauthorized data sharing or privacy violations
- **SC-010**: System successfully filters and blocks 100% of harmful or inappropriate content before processing

## Assumptions

- Users are familiar with Taiko no Tatsujin game terminology and concepts
- Song database (taikowiki JSON) is available and accessible in real-time
- QQ groups have appropriate moderation to prevent abuse
- Users understand the bot only responds when explicitly called by name
- Network connectivity is generally stable, with occasional failures handled gracefully
- LLM service (gpt-4o via OpenRouter) is available and within budget constraints
- Users primarily interact in Chinese or English languages

## Dependencies

### External Services
- **taikowiki API**: Real-time song database (HTTP endpoint) - PRIMARY data source. System fetches from API first and updates local JSON file (data/database.json) periodically (e.g., hourly) for caching. Local JSON file is used ONLY as fallback when API is unavailable
- **OpenRouter API**: gpt-4o access (REST API) for generating responses. System may support local LLM models in the future as an alternative fallback option
- **LangBot**: Core bot platform for QQ integration (deployed separately, must run continuously to receive QQ messages and manage triggers. Downtime prevents message reception. Connects to FastAPI backend via webhook at `/webhook/langbot`)
- **Napcat**: QQ protocol layer (deployed separately or as part of LangBot deployment, must run continuously to keep bot account online. Downtime prevents receiving messages from QQ platform)

### Infrastructure Services (Must Run Continuously)
- **FastAPI Backend + Temporal Client**: Must run continuously to handle webhooks, call gpt-4o, and execute 5-step processing chain
- **Temporal Server + PostgreSQL**: Must run continuously as workflow engine to schedule tasks and handle retries. Downtime prevents workflow execution
- **MongoDB**: Must run continuously to store user data, conversation history, and impressions. Downtime causes memory loss and data unavailability
- **Nginx** (Strongly Recommended): Long-running reverse proxy with HTTPS and load balancing to provide stable public network entry point

## Out of Scope

- Direct game integration or gameplay features
- User authentication or account management
- Payment or monetization features
- Integration with platforms other than QQ
- Real-time game data synchronization
- Advanced analytics or reporting dashboards
- Bot customization by end users (beyond conversation preferences)
