# Research & Technical Decisions: Mika Taiko Chatbot

**Feature**: `1-mika-bot`  
**Date**: 2026-01-08  
**Status**: Complete

This document consolidates research findings and technical decisions for the Mika Taiko Chatbot implementation.

## 1. LangBot Integration Patterns

### Research Question
How to configure LangBot for keyword triggers on "Mika" variants and group whitelisting?

### Findings
- LangBot supports keyword-based message triggers via regex patterns
- Group whitelist can be configured via configuration file or environment variables
- LangBot sends webhook POST requests to FastAPI backend with message data
- Message format includes: group_id, user_id, message text, optional images

### Decision
- **Keyword Trigger**: Use regex pattern `(?i)(mika|米卡|mika酱)` for case-insensitive matching
- **Group Whitelist**: Configure via `LANGBOT_ALLOWED_GROUPS` environment variable (comma-separated group IDs)
- **Webhook Endpoint**: `/webhook/langbot` in FastAPI application

### Rationale
LangBot's built-in keyword matching is efficient and reduces false positives. Group whitelist prevents unauthorized access and reduces spam risk.

### Alternatives Considered
- **Full message scanning**: Rejected - too resource-intensive, higher false positive rate
- **ML-based name detection**: Rejected - overkill for simple keyword matching, adds latency

### Implementation Notes
- Configure LangBot to send webhooks to FastAPI endpoint
- Validate group_id against whitelist in middleware before processing
- Log all webhook requests for debugging

---

## 2. Temporal.io Workflow Patterns

### Research Question
How to use Temporal Python SDK for orchestrating the 5-step processing chain with retries and fault tolerance?

### Findings
- Temporal Python SDK provides `@workflow.defn` decorator for workflows
- Activities are defined with `@activity.defn` decorator and must be deterministic
- Retry policies can be configured per Activity with exponential backoff
- Temporal handles activity timeouts, retries, and failure recovery automatically
- Activities should be idempotent for safe retries

### Decision
- **Workflow**: Single `process_message_workflow` orchestrating all 5 steps
- **Activities**: Each step (step1-5) wrapped as separate Temporal Activity
- **Retry Policy**: Exponential backoff (FR-009)
  - Initial interval: 1 second
  - Backoff coefficient: 2.0 (exponential: 1s, 2s, 4s, 8s)
  - Maximum interval: 8 seconds
  - Maximum attempts: 5
- **Activity Timeout**: 30 seconds per step (step4 may need longer for LLM calls)

### Rationale
Temporal provides built-in retry, timeout, and fault tolerance mechanisms. Separating each step as an Activity enables independent retries and better error isolation.

### Alternatives Considered
- **Celery task queue**: Rejected - requires manual retry logic, less reliable for long-running workflows
- **Direct async/await chain**: Rejected - no built-in retry or fault tolerance, harder to debug failures
- **Airflow**: Rejected - overkill for simple linear workflow, heavier infrastructure

### Implementation Notes
- Use `temporalio.client.Client` to start workflows from FastAPI
- Activities should use async/await for I/O operations
- Log all activity executions for observability
- Use Temporal's activity heartbeat for long-running operations (step4 LLM calls)

---

## 3. Beanie ODM Best Practices

### Research Question
How to efficiently use Beanie for async MongoDB operations with hashed user IDs and bulk cleanup?

### Findings
- Beanie uses Pydantic models with `Document` base class
- Async queries use `find_one()`, `find()`, `insert_one()`, `replace_one()` methods
- Indexes can be defined in model classes or created programmatically
- Bulk operations use `insert_many()`, `delete_many()` for efficiency
- Beanie supports async context managers for connection management

### Decision
- **Models**: Use Beanie `Document` classes with Pydantic validation
- **Indexing**: Create unique index on `hashed_user_id` in User model
- **Queries**: Use async/await for all database operations
- **Cleanup**: Use `delete_many()` with date filter for 90-day conversation cleanup
- **Connection**: Initialize Beanie once at application startup

### Rationale
Beanie provides type-safe async MongoDB operations with excellent performance. Indexing on hashed_user_id enables fast user lookups across groups.

### Alternatives Considered
- **Motor (async MongoDB driver)**: Rejected - lower-level, requires manual model definition
- **MongoEngine**: Rejected - synchronous, doesn't support async/await
- **Raw PyMongo**: Rejected - no type safety, manual query construction

### Implementation Notes
- Initialize Beanie with `init_beanie()` at FastAPI startup
- Use `@beanie_document` decorator for model classes
- Create indexes in model class: `class Settings: indexes = [IndexModel([("hashed_user_id", 1)], unique=True)]`
- Use background task for 90-day cleanup (run daily via cron or Temporal)

---

## 4. OpenRouter API Integration

### Research Question
How to integrate OpenRouter API for gpt-4o with multi-modal support and cost optimization?

### Findings
- OpenRouter provides unified REST API for multiple LLM providers
- gpt-4o model ID: `openai/gpt-4o`
- Vision support: Include base64-encoded images in messages array
- API format: POST to `https://openrouter.ai/api/v1/chat/completions`
- Authentication: Bearer token via `Authorization` header
- Cost: ~$0.005 per 1K input tokens, ~$0.015 per 1K output tokens for gpt-4o

### Decision
- **API Client**: Use `httpx` async client for OpenRouter requests
- **Model**: `openai/gpt-4o` for text and vision
- **Caching**: Cache responses for identical queries (TTL: 1 hour)
- **Token Limits**: Max 2000 tokens output, 4000 tokens input
- **Error Handling**: Retry with exponential backoff, fallback to default response on failure

### Rationale
OpenRouter provides reliable access to gpt-4o with vision support. Caching reduces costs while maintaining response quality.

### Alternatives Considered
- **Direct OpenAI API**: Rejected - OpenRouter provides better rate limits and unified interface
- **Anthropic Claude**: Rejected - gpt-4o has better vision capabilities for image analysis
- **Local LLM (Ollama)**: Rejected - insufficient quality for themed responses, no vision support

### Implementation Notes
- Store OpenRouter API key in `OPENROUTER_API_KEY` environment variable
- Use `httpx.AsyncClient` for async requests
- Implement response caching in Redis or in-memory (for MVP)
- Monitor token usage and costs via OpenRouter dashboard

---

## 5. taikowiki JSON Structure

### Research Question
What is the structure of taikowiki JSON and how to implement efficient fuzzy matching?

### Findings
- taikowiki provides JSON API endpoint with song data
- Song structure: `{name, difficulty_stars, bpm, metadata}`
- Real-time queries may be rate-limited
- Fuzzy matching requires string similarity algorithms

### Decision
- **Fuzzy Matching Library**: Use `rapidfuzz` (fast, accurate fuzzy string matching)
- **Caching Strategy**: In-memory caching with periodic refresh (e.g., hourly) for song data (FR-002). Queries prioritize cached data for fast response times, with automatic background refresh to maintain data freshness
- **Query Pattern**: Load songs into memory at startup, refresh hourly via background job
- **Matching Algorithm**: Use `rapidfuzz.process.extractOne()` with threshold 0.7

### Rationale
rapidfuzz provides fast fuzzy matching suitable for real-time queries. Caching reduces external API calls and improves response time.

### Alternatives Considered
- **python-Levenshtein**: Rejected - slower than rapidfuzz
- **difflib**: Rejected - not optimized for performance
- **Live API queries**: Rejected - too slow, rate limit risks

### Implementation Notes
- Fetch taikowiki JSON at application startup
- Store songs in memory as list of dicts
- Background job refreshes cache daily
- Fallback to cached data if API unavailable

---

## 6. Content Filtering Implementation

### Research Question
How to filter harmful content (hatred, politics, religion) in Chinese and English text?

### Findings
- Keyword-based filtering is fast but may have false positives
- LLM-based filtering is accurate but adds latency and cost
- Hybrid approach balances speed and accuracy
- Chinese text requires specialized keyword lists

### Decision
- **Hybrid Approach** (FR-007): Keyword/phrase lists for fast pre-filtering of obviously inappropriate content, followed by LLM judgment for ambiguous cases
- **Primary Filter**: Keyword-based with curated lists for hatred (including ethnic hatred), politics, religion
- **Secondary Filter**: LLM-based check for ambiguous cases (if keyword filter uncertain)
- **Language Support**: Separate keyword lists for Chinese and English
- **Action**: Block message processing if harmful content detected; log for review

### Rationale
Hybrid approach balances filtering accuracy, cost efficiency, and performance while minimizing false positives. Keyword filtering provides fast first-pass detection. LLM fallback handles nuanced cases without adding latency to every message.

### Alternatives Considered
- **LLM-only filtering**: Rejected - too slow and expensive for every message
- **Keyword-only filtering**: Rejected - too many false positives/negatives
- **Third-party API (Moderation API)**: Rejected - adds external dependency, cost

### Implementation Notes
- Maintain keyword lists in `content_filter.py`
- Use regex patterns for flexible matching
- LLM check only if keyword filter confidence < 0.8
- Log all filtered messages for pattern analysis

---

## 7. Rate Limiting Architecture

### Research Question
How to implement rate limiting (20/user/min, 50/group/min) in async FastAPI?

### Findings
- FastAPI supports middleware for rate limiting
- In-memory rate limiting is simple but doesn't scale across instances
- Redis-based rate limiting enables distributed rate limiting
- Sliding window algorithm provides accurate rate limiting

### Decision
- **MVP**: In-memory rate limiting with sliding window
- **Production**: Redis-based distributed rate limiting
- **Algorithm**: Sliding window with per-user and per-group counters
- **Middleware**: FastAPI middleware checks rate limits before request processing

### Rationale
In-memory is sufficient for MVP and single-instance deployment. Redis enables horizontal scaling when needed.

### Alternatives Considered
- **Token bucket algorithm**: Rejected - sliding window is more accurate for time-based limits
- **Fixed window**: Rejected - allows bursts at window boundaries
- **Third-party service (Cloudflare)**: Rejected - adds external dependency, cost

### Implementation Notes
- Use `collections.deque` for sliding window in-memory implementation
- Store timestamps of requests per user/group
- Return 429 status code when limit exceeded
- Log rate limit violations for monitoring

---

## 8. Language Detection

### Research Question
How to detect user language and store preferences for multi-language responses?

### Findings
- `langdetect` library provides fast language detection
- Supports Chinese and English detection
- User preferences can override auto-detection
- Preference storage enables persistence across sessions

### Decision
- **Detection Library**: Use `langdetect` for automatic language detection
- **Storage**: Store `preferred_language` in User model
- **Override**: System MUST automatically detect user message language, but MUST also allow users to explicitly specify their preferred language (NFR-008)
- **Fallback**: Default to detected language if no preference set

### Rationale
langdetect is lightweight and accurate for Chinese/English. Preference storage enables personalized experience.

### Alternatives Considered
- **Google Cloud Translation API**: Rejected - adds external dependency, cost
- **spaCy language detection**: Rejected - heavier dependency, overkill
- **Manual keyword detection**: Rejected - less accurate, maintenance burden

### Implementation Notes
- Use `langdetect.detect()` for message language detection
- Store preference in User model: `preferred_language: Optional[str]`
- Use preference if set, otherwise use detected language
- Pass language to LLM prompt for response generation

---

## 9. Structured Logging and Monitoring

### Research Question
How to implement structured logging and monitoring for production deployment?

### Findings
- Structured JSON logging enables log aggregation and querying
- Python libraries: `structlog`, `python-json-logger` for JSON formatting
- Monitoring metrics can be exported in Prometheus format
- FastAPI supports middleware for metrics collection
- Health check endpoints are standard for container orchestration

### Decision
- **Logging**: Structured JSON format with fields (hashed user ID, request ID, timestamp, operation type, log level, message, contextual metadata) (NFR-010)
- **Log Library**: Use `structlog` or `python-json-logger` for JSON formatting
- **Monitoring**: Basic metrics (request rate, error rate, response time p50/p95/p99, system resource usage CPU/memory) (NFR-011)
- **Endpoints**: `/health` for health checks, `/metrics` for Prometheus format export
- **Privacy**: MUST NOT log sensitive user data (plaintext user IDs, API keys, personal information)

### Rationale
Structured JSON logs support aggregation and querying for debugging, performance monitoring, and audit purposes. Basic monitoring metrics provide essential operational visibility without the complexity of full distributed tracing.

### Alternatives Considered
- **Full distributed tracing (OpenTelemetry)**: Rejected - too complex for MVP, basic metrics sufficient
- **Plain text logging**: Rejected - harder to parse and aggregate, no machine-readable format
- **Third-party logging service (Datadog, Splunk)**: Rejected - adds cost and external dependency for MVP

### Implementation Notes
- Configure structured logging at application startup
- Include request ID in all log entries for traceability
- Export metrics in Prometheus format for standard monitoring tools
- Log retention and rotation policies configurable via environment variables

---

## 10. Image Processing Limits and Error Handling

### Research Question
What limits should be imposed on multi-modal image processing and how to handle errors?

### Findings
- Large images consume significant memory and processing time
- LLM vision APIs have size and format limitations
- User-friendly error messages improve UX
- Themed error messages maintain bot identity consistency

### Decision
- **Size Limit**: Maximum 10MB per image (FR-006)
- **Format Support**: JPEG, PNG, WebP only (FR-006)
- **Error Messages**: User-friendly, themed error messages (e.g., "图片太大啦！" with thematic game elements) when limits exceeded (FR-006)
- **Prompt Engineering**: Comprehensive prompt engineering MUST be implemented for detailed image analysis and themed response generation (FR-006)

### Rationale
Reasonable limits balance user experience with system resource constraints. Themed error messages maintain consistency with bot identity. Comprehensive prompt engineering ensures high-quality image analysis responses.

### Alternatives Considered
- **No size limits**: Rejected - risk of memory exhaustion and slow processing
- **Strict limits (2MB)**: Rejected - too restrictive, poor user experience
- **Generic error messages**: Rejected - breaks thematic consistency

### Implementation Notes
- Validate image size and format before processing
- Return themed error message immediately if validation fails
- Implement comprehensive prompt templates for image analysis scenarios
- Test with various image sizes and formats

---

## 12. Prompt Template System Architecture

### Research Question
How should prompt templates be organized and managed to make adding new prompts simple and maintainable?

### Findings
- Prompt templates can be organized in single file (`prompts.py`) or directory structure (`prompts/`)
- Python string templates (`str.format()` or f-strings) provide simple variable substitution
- Jinja2 template engine offers more advanced features (conditionals, loops, inheritance)
- Prompt versioning enables A/B testing and gradual rollouts
- Simple API (e.g., `add_prompt()`) reduces barrier to adding new prompts

### Decision
- **Template System**: Use Python string templates (str.format() or f-strings) for variable substitution, with option to use Jinja2 for advanced cases (FR-013)
- **Organization**: Organize prompts by use case (general chat, song queries, image analysis, memory-aware) in single `src/prompts.py` file or `src/prompts/` directory with individual template files
- **API**: Provide simple API for adding new prompts (e.g., `add_prompt(name, template, variables)` function)
- **Versioning**: Support prompt versioning and A/B testing capabilities for experimentation

### Rationale
Structured template system enables easy prompt iteration without code changes, facilitates prompt engineering best practices, and supports experimentation through versioning and A/B testing. Simple API reduces barrier to adding new prompts and makes prompt management accessible to non-developers.

### Alternatives Considered
- **Hard-coded prompts in code**: Rejected - difficult to iterate, requires code changes for prompt updates
- **External configuration files (YAML/JSON)**: Rejected - adds complexity, harder to maintain type safety
- **Database-stored prompts**: Rejected - overkill for MVP, adds latency and complexity

### Implementation Notes
- Create `PromptManager` class with `add_prompt()`, `get_prompt()`, `list_prompts()` methods
- Support prompt versioning with version tags (e.g., "v1", "v2", "experimental")
- Enable A/B testing by allowing multiple versions of same prompt with traffic splitting
- Organize prompts by use case for easy discovery and maintenance
- Use Python string templates for simple cases, Jinja2 for complex conditional logic

---

## Summary

All research questions have been resolved with concrete technical decisions. Implementation can proceed with confidence in the chosen technologies and patterns.

**Key Technologies Selected**:
- Temporal.io for workflow orchestration (exponential backoff retry: 1s, 2s, 4s, 8s, max 5 attempts)
- Beanie for async MongoDB ODM
- OpenRouter + gpt-4o for AI responses (with comprehensive prompt engineering)
- rapidfuzz for fuzzy song matching
- langdetect for language detection (auto-detect + user override)
- FastAPI + Uvicorn for backend
- LangBot for QQ integration
- structlog/python-json-logger for structured JSON logging
- In-memory caching with periodic refresh (hourly) for song data
- Hybrid content filtering (keyword lists + LLM judgment)
- Structured prompt template system (Python string templates or Jinja2) with versioning and A/B testing support
- pytest + pytest-asyncio for comprehensive testing infrastructure (automated tests, fixtures, mocks, manual scripts)

## 13. Testing Infrastructure Architecture

### Research Question
What testing infrastructure should the system provide to ensure code quality, enable rapid iteration, and support both automated and manual testing workflows?

### Findings
- pytest is the standard testing framework for Python with excellent async support (pytest-asyncio)
- pytest fixtures provide reusable test data and mocks, reducing test code duplication
- Mocking external services (APIs, databases) is essential for isolated unit tests
- Manual testing scripts enable rapid functional verification during development
- Test coverage targets (80%+) are industry standard for production applications

### Decision
- **Automated Test Suite**: Implement comprehensive pytest test suite with unit tests (tests/unit/) and integration tests (tests/integration/) covering all user stories and edge cases, targeting 80%+ coverage (NFR-012)
- **Test Utilities**: Create pytest fixtures (tests/fixtures/) for common test data (mock users, conversations, songs) and mocks for external services (OpenRouter API, taikowiki, MongoDB)
- **Manual Testing Scripts**: Provide manual testing scripts in `scripts/` directory for quick functional verification (e.g., `scripts/test_webhook.py` for testing LangBot webhook endpoint, `scripts/test_song_query.py` for testing song queries)

### Rationale
Automated test suite ensures code quality and prevents regressions. Test utilities (fixtures and mocks) improve test maintainability and reduce duplication. Manual testing scripts enable rapid iteration and debugging during development. This provides both automated quality assurance and developer-friendly manual testing tools.

### Alternatives Considered
- **Unit tests only**: Rejected - integration tests are essential for verifying end-to-end workflows
- **No manual testing scripts**: Rejected - manual scripts significantly improve development velocity
- **Mock-free integration tests**: Rejected - too slow and unreliable for CI/CD pipelines

### Implementation Notes
- Use pytest-asyncio for async test support
- Create conftest.py in tests/fixtures/ for shared fixtures
- Use unittest.mock or pytest-mock for service mocking
- Manual scripts should accept command-line arguments for flexibility
- Test coverage reporting via pytest-cov

---

**Key Clarifications Integrated**:
- ✅ Structured JSON logging with aggregation support
- ✅ Basic monitoring metrics with /health and /metrics endpoints
- ✅ Hybrid content filtering (keyword + LLM)
- ✅ In-memory caching with periodic refresh for song data
- ✅ Exponential backoff retry strategy for Temporal workflows
- ✅ Image processing limits (10MB, JPEG/PNG/WebP) with themed error messages
- ✅ API key management via environment variables, placeholder configs
- ✅ Comprehensive prompt engineering for image analysis
- ✅ Structured prompt template system with simple API, versioning, and A/B testing support (FR-013)
- ✅ Comprehensive testing infrastructure (automated pytest suite, fixtures/mocks, manual testing scripts) (NFR-012)
- ✅ Deployment architecture with continuous service requirements (all infrastructure services must run continuously: FastAPI backend + Temporal client, Temporal server + PostgreSQL, MongoDB, Nginx recommended. External services: LangBot and Napcat deployed separately) (NFR-013)

**Next Steps**: Proceed to Phase 1 (Data Model Design and API Contracts)
