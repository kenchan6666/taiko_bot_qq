# Tasks: Mika Taiko Chatbot

**Input**: Design documents from `/specs/1-mika-bot/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md

**Tests**: Included per user requirements for comprehensive coverage

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Clarifications Integrated**: All clarifications from spec.md are reflected in tasks, including:
- FR-013: Structured prompt template system with simple API (`add_prompt` function), versioning, and A/B testing support
- FR-013 Enhancement: Intent classification and scenario-based prompting (fine-grained intents: greeting, help, goodbye, preference_confirmation, song_query, song_recommendation, difficulty_advice, game_tips, etc.; scenario-based prompts for specific contexts; hierarchical organization: use_case → intent → scenario). Intent detection failure fallback to use_case-based prompts with logging
- FR-002 Enhancement: taikowiki API is PRIMARY data source, local JSON file (data/database.json) used ONLY as fallback when API unavailable
- FR-008 Enhancement: Concurrent message deduplication (process in order but skip duplicate/similar messages, configurable similarity threshold and deduplication window)
- FR-010 Enhancement: Unconfirmed preference handling (retain in pending state, do not re-ask, re-confirm naturally in context)
- FR-009 Enhancement: Detailed error recovery (use cached/default responses with user notification, song database falls back to local JSON, LLM may support local models)
- NFR-012: Comprehensive testing infrastructure (automated pytest suite, fixtures/mocks, manual testing scripts)
- NFR-013: Deployment architecture with external services (LangBot, Napcat deployed separately, webhook endpoint exposure with ngrok for local development, Nginx/public IP for production)
- All other clarifications (logging, monitoring, caching, retry strategies, image limits, etc.)

## Format: `[ID] [P?] [Story] Description (Effort: Xh)`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- **Effort**: Estimated hours (h) or story points (sp)
- Include exact file paths in descriptions

## Priority Levels

- **P0**: Core functionality (5 steps + name trigger) - MVP critical
- **P1**: Temporal and Docker integration - Production readiness
- **P2**: Advanced features and comprehensive tests - Enhancement

---

## Phase 1: Setup (Shared Infrastructure) - P0

**Purpose**: Project initialization and basic structure

**Effort Estimate**: 8-12 hours

- [x] T001 [P] Create project directory structure per plan.md in repository root (Effort: 1h)
- [x] T002 [P] Initialize Poetry project with pyproject.toml in repository root (Effort: 1h)
- [x] T003 [P] Add core dependencies to pyproject.toml: fastapi, uvicorn, beanie, temporalio, httpx, python-jose, langdetect, rapidfuzz, pydantic (Effort: 1h)
- [x] T004 [P] Add development dependencies: pytest, pytest-asyncio, black, mypy (Effort: 0.5h)
- [x] T005 [P] Create .env.example with all required environment variables in repository root (Effort: 0.5h)
- [x] T006 [P] Configure Black formatter in pyproject.toml (Effort: 0.5h)
- [x] T007 [P] Create README.md with project overview in repository root (Effort: 1h)
- [x] T008 Create src/ directory structure: steps/, models/, services/, workflows/, activities/, api/, utils/ (Effort: 0.5h)
- [x] T009 Create tests/ directory structure: unit/, integration/, fixtures/ (Effort: 0.5h)

**Checkpoint**: Project structure ready, dependencies configured

---

## Phase 2: Foundational (Blocking Prerequisites) - P0

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Effort Estimate**: 16-20 hours

### Configuration and Utilities

- [x] T010 [P] Create src/config.py with environment variable loading (OPENROUTER_API_KEY, MONGODB_URL, TEMPORAL_HOST, etc.) (Effort: 2h)
- [x] T011 [P] Create src/utils/hashing.py with SHA-256 user ID hashing function (Effort: 1h)
- [x] T012 [P] Create src/utils/language_detection.py with langdetect integration (Effort: 1h)

### Database Setup

- [x] T013 Create src/services/database.py with Beanie initialization and MongoDB connection (Effort: 2h)
- [x] T014 [P] Create src/models/user.py with User Beanie model (hashed_user_id, preferred_language, timestamps) (Effort: 1.5h)
- [x] T015 [P] Create src/models/conversation.py with Conversation Beanie model (user_id, group_id, message, response, expires_at) (Effort: 1.5h)
- [x] T016 [P] Create src/models/impression.py with Impression Beanie model (user_id, preferences, relationship_status, interaction_count) (Effort: 1.5h)
- [x] T017 Create database initialization script in scripts/init_database.py (Effort: 1h)

### Content Filtering

- [x] T018 [P] Create src/services/content_filter.py with keyword-based filtering for hatred, politics, religion (Effort: 3h)

### Rate Limiting

- [x] T019 [P] Create src/services/rate_limiter.py with sliding window algorithm (20/user/min, 50/group/min) (Effort: 3h)

### Intent Detection Service

- [x] T019A [P] Create src/services/intent_detection.py with rule-based keyword matching for common intents (greeting, help, goodbye, preference_confirmation, song_query, song_recommendation, difficulty_advice, game_tips, etc.) and optional LLM-based classification for complex cases (Effort: 3h)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Interactive Chatbot Conversations (Priority: P1) 🎯 MVP - P0

**Goal**: Users can interact with "Mika" bot that responds when mentioned by name with themed content

**Independent Test**: Send message mentioning "Mika" in QQ group, verify themed response. Send message without "Mika", verify no response.

**Effort Estimate**: 25-31 hours

### Core Step Functions (P0 - Critical Path)

- [x] T020 [US1] Create src/steps/step1.py with input parsing, "Mika" name detection (regex: (?i)(mika|米卡|mika酱)), hybrid content filtering integration (keyword lists + LLM judgment per FR-007), user ID hashing (SHA-256 per FR-011), basic intent detection integration (intent classification will be enhanced in Phase 7), and message deduplication (process messages in order but skip duplicate or highly similar messages, configurable similarity threshold and deduplication window via environment variables per FR-008) (Effort: 4h)
- [x] T021 [US1] Create src/steps/step2.py with Beanie User/Impression/Conversation context retrieval by hashed_user_id (Effort: 3h)
- [x] T022 [US1] Create src/steps/step3.py with taikowiki JSON query placeholder (return None for now, will implement fuzzy matching in US2) (Effort: 2h)
- [x] T023 [US1] Create src/prompts.py with structured prompt template system (FR-013: PromptManager class with add_prompt(), get_prompt(), list_prompts() methods, support for versioning and A/B testing, organized hierarchically: use_case → intent → scenario) (Effort: 3h)
- [x] T024 [US1] Create src/services/llm.py with OpenRouter API client for gpt-4o (Effort: 3h)
- [x] T025 [US1] Create src/steps/step4.py with OpenRouter gpt-4o invocation using PromptManager from prompts.py (basic use_case-based prompt selection; intent-based selection will be enhanced in Phase 7) (Effort: 3h)
- [x] T026 [US1] Create src/steps/step5.py with Beanie Impression and Conversation update logic (Effort: 3h)

### FastAPI Integration

- [x] T027 [US1] Create src/api/main.py with FastAPI application setup and structured JSON logging configuration (NFR-010) (Effort: 2h)
- [x] T028 [US1] Create src/api/routes/langbot.py with /webhook/langbot POST endpoint (Effort: 2h)
- [x] T029 [US1] Integrate rate limiting middleware in src/api/middleware/rate_limit.py (Effort: 2h)

### Basic Testing

- [ ] T030 [P] [US1] Create tests/unit/test_step1.py with name detection and content filtering tests (Effort: 2h)
- [ ] T031 [P] [US1] Create tests/unit/test_step2.py with Beanie context retrieval tests (Effort: 2h)
- [ ] T032 [P] [US1] Create tests/unit/test_step4.py with LLM invocation tests (mocked) (Effort: 2h)
- [ ] T033 [US1] Create tests/integration/test_basic_flow.py with end-to-end test (mocked LLM) (Effort: 2h)

**Checkpoint**: At this point, User Story 1 should be fully functional - bot responds to "Mika" mentions with themed content

---

## Phase 4: User Story 2 - Song Information Queries (Priority: P1) - P0

**Goal**: Users can query Taiko song information with difficulty and BPM details, including fuzzy matching

**Independent Test**: Query specific song name, verify accurate info. Query misspelled name, verify fuzzy match. Query non-existent song, verify graceful error.

**Effort Estimate**: 16-20 hours

### Song Query Implementation

- [x] T034 [US2] Create src/services/song_query.py with taikowiki API as PRIMARY data source, local JSON file (data/database.json) as fallback when API unavailable, and in-memory caching with periodic refresh (hourly) per FR-002. When updating local file, replace existing data for consistency (Effort: 3h)
- [x] T035 [US2] Implement fuzzy matching in src/services/song_query.py using rapidfuzz library; when multiple matches found, return only single best match and surface confirmation metadata (Effort: 3h)
- [x] T036 [US2] Update src/steps/step3.py with full song query implementation: use taikowiki API as PRIMARY data source, fallback to local JSON file (data/database.json) when API unavailable, fuzzy matching, BPM/difficulty commentary, and themed confirmation prompt for best match. When API unavailable, notify user (e.g., "使用缓存数据，可能不是最新的") (e.g., “你是指《XXX》吗？”/“Did you mean 'XXX'?”) (Effort: 3h)
- [x] T037 [US2] Create scripts/seed_songs.py to fetch and cache taikowiki song data at startup (Effort: 2h)

### Prompt Enhancement

- [x] T038 [US2] Add song information injection prompt templates to src/prompts.py using PromptManager API (Effort: 1.5h)

### Testing

- [x] T039 [P] [US2] Create tests/unit/test_step3.py with song query and fuzzy matching tests, including best-match confirmation prompt content, taikowiki API as primary data source, and local JSON fallback when API unavailable (Effort: 3h)
- [x] T040 [P] [US2] Create tests/unit/test_song_query.py with taikowiki integration tests (mocked) (Effort: 2h)
- [x] T041 [US2] Create tests/integration/test_song_queries.py with end-to-end song query tests (Effort: 2h)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - bot responds with song information

---

## Phase 5: Temporal.io Integration - P1

**Purpose**: Add workflow orchestration for reliability, retries, and fault tolerance

**Effort Estimate**: 20-24 hours

### Temporal Activities

- [x] T042 [P] Create src/activities/step1_activity.py wrapping step1.py as Temporal Activity (Effort: 2h)
- [x] T043 [P] Create src/activities/step2_activity.py wrapping step2.py as Temporal Activity (Effort: 2h)
- [x] T044 [P] Create src/activities/step3_activity.py wrapping step3.py as Temporal Activity (Effort: 2h)
- [x] T045 [P] Create src/activities/step4_activity.py wrapping step4.py as Temporal Activity (Effort: 2h)
- [x] T046 [P] Create src/activities/step5_activity.py wrapping step5.py as Temporal Activity (Effort: 2h)

### Temporal Workflow

- [x] T047 Create src/workflows/message_workflow.py with process_message_workflow orchestrating all 5 steps (Effort: 3h)
- [x] T048 Configure retry policies in message_workflow.py (exponential backoff: 1s, 2s, 4s, 8s intervals, max 5 attempts per FR-009) (Effort: 2h)
- [x] T049 Create src/workers/temporal_worker.py to register workflows and activities (Effort: 2h)

### FastAPI Integration

- [x] T050 Update src/api/routes/langbot.py to start Temporal workflow instead of direct step calls (Effort: 2h)

### Testing

- [x] T051 [P] Create tests/unit/test_activities.py with Activity tests (Effort: 2h)
- [x] T052 Create tests/integration/test_workflow.py with end-to-end workflow test (Effort: 3h)

**Checkpoint**: Temporal workflow operational - all steps orchestrated with retries

---

## Phase 6: User Story 3 - Contextual Conversations with Memory (Priority: P2) - P1

**Goal**: Bot remembers previous interactions and provides personalized responses

**Independent Test**: Have multiple conversations, verify bot references past interactions. Verify impression updates and relationship status changes.

**Effort Estimate**: 12-16 hours

### Memory Enhancement

- [x] T053 [US3] Update src/steps/step2.py to retrieve recent conversations using configurable limit via env var `CONVERSATION_HISTORY_LIMIT` (default 10) for context (Effort: 2h)
- [x] T054 [US3] Update src/steps/step4.py to include conversation history in LLM prompt using memory-aware template from PromptManager (Effort: 2h)
- [x] T055 [US3] Enhance src/steps/step5.py with impression learning logic (extract preferences, update relationship_status) and confirmation flow: ask user for confirmation, prioritize explicit “是/对/yes/correct”, allow implicit if user continues assuming preference is correct (Effort: 3h)
- [x] T056 [US3] Add memory-aware prompt templates to src/prompts.py using PromptManager API (Effort: 1.5h)

### User Notification

- [x] T057 [US3] Implement user notification in step4.py when pending preferences exist, naturally asking for confirmation in response. Re-confirm naturally when users mention related topics (FR-010 Enhancement) (Effort: 2h)

### Testing

- [x] T058 [P] [US3] Create tests/unit/test_memory.py with impression update and context retrieval tests, covering configurable history limit, explicit/implicit preference confirmation, and unconfirmed preference handling (pending state, natural re-confirmation) (Effort: 3h)
- [x] T059 [US3] Create tests/integration/test_memory_flow.py with multi-conversation memory tests, including confirmation flows and preference persistence (Effort: 2h)

**Checkpoint**: Bot remembers user preferences and references past conversations

---

## Phase 7: User Story 4 - Multi-Modal Content Support (Priority: P2) - P1

**Goal**: Bot processes images and provides themed responses about visual content

**Independent Test**: Send Taiko screenshot, verify themed description. Send non-game image, verify appropriate response.

**Effort Estimate**: 11-13 hours

### Multi-Modal Support

- [x] T060 [US4] Update src/steps/step1.py to handle image data from LangBot webhook with validation (10MB limit, JPEG/PNG/WebP formats per FR-006) (Effort: 2h)
- [x] T061 [US4] Update src/services/llm.py to support multi-modal requests (base64 image encoding) (Effort: 2h)
- [x] T062 [US4] Update src/steps/step4.py to include images in OpenRouter API call using image analysis template from PromptManager; provide detailed analysis for Taiko images (song, difficulty, score) and themed response for non-Taiko images (Effort: 2h)
- [x] T063 [US4] Add image analysis prompt templates to src/prompts.py using PromptManager API for Taiko-detailed analysis and non-Taiko themed response per FR-006 (Effort: 1.5h)

### Testing

- [x] T064 [P] [US4] Create tests/unit/test_multimodal.py with image processing tests (Effort: 2h)
- [x] T065 [US4] Create tests/integration/test_image_flow.py with end-to-end image processing tests (Effort: 2h)

**Checkpoint**: Bot processes images and provides themed responses

---

## Phase 7: Intent Classification & Scenario-Based Prompting Enhancement - P1

**Purpose**: Implement fine-grained intent classification and scenario-based prompts for contextually appropriate responses

**Effort Estimate**: 14-18 hours

### Intent Classification System

- [ ] T065A [US1] Enhance src/services/intent_detection.py with fine-grained intent classification:
  - Conversational intents: greeting, help, goodbye, preference_confirmation, clarification_request
  - Song-related intents: song_query, song_recommendation, difficulty_advice, bpm_analysis
  - Game-related intents: game_tips, achievement_celebration, practice_advice
  - Rule-based keyword matching for common intents
  - Optional LLM-based classification for complex/ambiguous cases (Effort: 3h)

### Intent-Specific Prompt Templates

- [ ] T065B [US1] Add intent-specific prompt templates to src/prompts.py using PromptManager API:
  - Conversational intents: greeting, help, goodbye prompts
  - Song-related intents: song_recommendation, difficulty_advice, bpm_analysis prompts
  - Game-related intents: game_tips, achievement_celebration, practice_advice prompts (Effort: 2h)

### Scenario-Based Prompt Templates

- [ ] T065C [US1] Add scenario-based prompt templates to src/prompts.py for specific contexts:
  - song_recommendation_high_bpm, song_recommendation_beginner_friendly
  - difficulty_advice_beginner, difficulty_advice_expert
  - game_tips_timing, game_tips_accuracy (Effort: 2h)

### Intent-Based Prompt Selection

- [ ] T065D [US1] Update src/steps/step4.py to use intent-based prompt selection:
  - Detect intent from parsed_input and context using intent_detection service
  - Select appropriate prompt template based on intent and scenario
  - Fallback to use_case-based prompts if intent not detected (infer use_case from message content)
  - Log intent detection failures for analysis and improvement (Effort: 3h)

### Intent Detection Integration

- [ ] T065E [US1] Update src/steps/step1.py to integrate intent detection service and pass detected intent to subsequent steps (Effort: 2h)

### Testing

- [ ] T065F [P] [US1] Create tests/unit/test_intent_detection.py with intent classification tests (rule-based and LLM-based) and fallback to use_case-based prompts when intent detection fails (Effort: 2h)
- [ ] T065G [US1] Create tests/integration/test_intent_prompt_selection.py with end-to-end intent-based prompt selection tests, including fallback scenarios and logging verification (Effort: 2h)

**Checkpoint**: Intent classification system operational, contextually appropriate responses based on detected intents and scenarios

---

## Phase 8: LangBot Configuration - P1

**Purpose**: Configure LangBot for QQ integration with keyword triggers, group whitelist, and webhook endpoint exposure

**Effort Estimate**: 8-10 hours

- [ ] T066 [P] Create LangBot configuration file with keyword trigger pattern (?i)(mika|米卡|mika酱) (Effort: 2h)
- [ ] T067 [P] Configure group whitelist in LangBot (LANGBOT_ALLOWED_GROUPS environment variable) (Effort: 1h)
- [ ] T068 Update src/api/routes/langbot.py to validate group_id against whitelist (Effort: 2h)
- [ ] T069 [P] Document webhook endpoint exposure methods in quickstart.md: ngrok for local development, Nginx/public IP for production (Effort: 1h)
- [ ] T070 [P] Create setup guide for exposing webhook endpoint (local: ngrok setup instructions, production: Nginx configuration) (Effort: 1.5h)
- [ ] T071 Configure LangBot to send webhooks to FastAPI backend endpoint (/webhook/langbot) - use ngrok URL for local development or public domain/IP for production (Effort: 1h)
- [ ] T072 Test LangBot integration with QQ groups (verify webhook delivery, test keyword triggers, validate group whitelist) (Effort: 2.5h)

**Checkpoint**: LangBot configured and responding in QQ groups via webhook connection (local development with ngrok or production with public endpoint)

---

## Phase 9: Docker Compose Deployment - P1

**Purpose**: Full stack deployment with all services (LangBot and Napcat are external services)

**Effort Estimate**: 8-10 hours

- [ ] T073 [P] Create docker/Dockerfile.backend for FastAPI application (Effort: 2h)
- [ ] T074 [P] Create docker/Dockerfile.temporal for Temporal worker (Effort: 1h)
- [ ] T075 Create docker-compose.yml with services: backend, mongo, temporal, temporal-postgresql, nginx (optional). Note: LangBot and Napcat are external services deployed separately (Effort: 3h)
- [ ] T076 Create .dockerignore file (Effort: 0.5h)
- [ ] T077 Update quickstart.md with Docker Compose deployment instructions and external service setup (LangBot, Napcat) (Effort: 1h)
- [ ] T078 [P] Document external service deployment requirements (LangBot and Napcat must be deployed separately, webhook endpoint configuration) (Effort: 1h)
- [ ] T079 Test full stack deployment locally (verify all services start, test webhook endpoint accessibility) (Effort: 2.5h)

**Checkpoint**: Full stack deployable via Docker Compose

---

## Phase 10: Advanced Features & Polish - P2

**Purpose**: Additional features and optimizations

**Effort Estimate**: 17-21 hours

### Cleanup Job

- [ ] T080 Create scripts/cleanup_old_conversations.py for 90-day conversation deletion (Effort: 2h)
- [ ] T081 Configure cleanup job as Temporal scheduled workflow or cron job (Effort: 1h)

### Language Detection Enhancement

- [ ] T082 Update src/steps/step1.py with automatic language detection using langdetect (Effort: 1h)
- [ ] T083 Update src/steps/step4.py to use detected/preferred language in LLM prompt via PromptManager (Effort: 1h)

### Prompt Engineering & Template System Enhancement

- [ ] T087 [P] Enhance PromptManager in src/prompts.py with prompt versioning support (version tags, version history) (Effort: 2h)
- [ ] T088 [P] Add A/B testing capabilities to PromptManager (traffic splitting, experiment tracking) (Effort: 2h)
- [ ] T089 Add cultural sensitivity guidelines to prompt templates in src/prompts.py (Effort: 1h)

### Error Handling & Graceful Degradation

- [ ] T090 Implement fallback mechanisms in step3.py: use local JSON file (data/database.json) when taikowiki API unavailable, notify user (e.g., "使用缓存数据，可能不是最新的" / "Using cached data, may not be latest") (Effort: 2h)
- [ ] T091 Implement fallback mechanisms in step4.py: use cached data or default themed responses when LLM fails, notify user in response. System may support local LLM models in the future as alternative to OpenRouter API (Effort: 2h)

### Monitoring & Health Checks

- [ ] T092 Create src/api/routes/health.py with /health endpoint (MongoDB, Temporal, OpenRouter status) per NFR-011 (Effort: 2h)
- [ ] T093 Create src/api/routes/metrics.py with /metrics endpoint (Prometheus format: request rate, error rate, response time p50/p95/p99, system resources) per NFR-011 (Effort: 2h)

**Checkpoint**: Advanced features complete, system production-ready

---

## Phase 11: Comprehensive Testing - P2

**Purpose**: Comprehensive test coverage for edge cases, integration scenarios, and manual testing scripts per NFR-012

**Effort Estimate**: 24-28 hours

### Edge Case Tests

- [ ] T094 [P] Create tests/unit/test_edge_cases.py: no name trigger, network failure, LLM timeout, malformed input (Effort: 4h)
- [ ] T095 [P] Create tests/unit/test_content_filter.py: hatred, politics, religion filtering edge cases (Effort: 3h)
- [ ] T096 [P] Create tests/unit/test_rate_limiter.py: rate limit enforcement, sliding window accuracy (Effort: 2h)

### Integration Tests

- [ ] T097 Create tests/integration/test_multi_group.py: concurrent requests from multiple groups (Effort: 3h)
- [ ] T098 Create tests/integration/test_error_scenarios.py: service failures, graceful degradation (Effort: 3h)
- [ ] T099 Create tests/integration/test_privacy.py: hashed user IDs, 90-day deletion, cross-group recognition (Effort: 3h)

### Load Testing

- [ ] T100 Create tests/load/test_concurrent_requests.py: 100 concurrent requests test (Effort: 3h)
- [ ] T101 Create tests/load/test_response_time.py: < 3s response time validation (Effort: 2h)

### Manual Testing Scripts (NFR-012)

- [ ] T102 [P] Create scripts/test_webhook.py for manual testing of LangBot webhook endpoint (accepts command-line arguments for message, group_id, user_id, optional image) (Effort: 2h)
- [ ] T103 [P] Create scripts/test_song_query.py for manual testing of song queries (accepts command-line arguments for song name, tests fuzzy matching and caching) (Effort: 2h)

**Checkpoint**: Comprehensive test coverage achieved (80%+ target), manual testing scripts available for rapid iteration

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - P0 MVP critical path
- **User Story 2 (Phase 4)**: Depends on Foundational, can start after US1 step3 placeholder
- **Temporal Integration (Phase 5)**: Depends on US1 and US2 step functions - P1
- **User Story 3 (Phase 6)**: Depends on US1 and US2 - P1
- **User Story 4 (Phase 7)**: Depends on US1 - P1
- **Intent Classification (Phase 7)**: Depends on US1 (prompts.py, step4.py) - P1. Enhances prompt selection with intent-based routing
- **LangBot Configuration (Phase 8)**: Depends on US1 FastAPI endpoint - P1. Includes webhook endpoint exposure (ngrok for local, Nginx/public IP for production)
- **Docker Compose (Phase 9)**: Depends on all core functionality - P1. Note: LangBot and Napcat are external services deployed separately
- **Advanced Features (Phase 10)**: Depends on core functionality - P2
- **Comprehensive Testing (Phase 11)**: Depends on all features - P2

### Task Dependencies Within Phases

**Phase 2 (Foundational)**:
- T013 (database.py) must complete before T014-T016 (models)
- T014-T016 (models) can run in parallel
- T018 (content_filter), T019 (rate_limiter), and T019A (intent_detection) can run in parallel

**Phase 3 (US1)**:
- T020 (step1) → T021 (step2) → T022 (step3) → T024 (llm) → T025 (step4) → T026 (step5) - sequential dependency
- T023 (prompts: structured template system with PromptManager) can run in parallel with step functions
- T027-T029 (FastAPI) depends on all steps
- T030-T033 (tests) can run in parallel after implementation

**Phase 4 (US2)**:
- T034-T036 (song query) sequential
- T037 (seed script) can run in parallel
- T038 (prompts) depends on T036
- Tests can run after implementation

**Phase 5 (Temporal)**:
- T042-T046 (Activities) can run in parallel
- T047 (Workflow) depends on all Activities
- T048 (retry policies) depends on T047
- T049 (worker) depends on T047-T048
- T050 (FastAPI integration) depends on T047-T049

### Parallel Opportunities

**Phase 1 (Setup)**:
- T001-T009 can all run in parallel (different files/directories)

**Phase 2 (Foundational)**:
- T010-T012 (config/utils) can run in parallel
- T014-T016 (models) can run in parallel
- T018-T019-T019A (services: content_filter, rate_limiter, intent_detection) can run in parallel

**Phase 3 (US1)**:
- T023 (prompts) can run while implementing steps
- T030-T032 (unit tests) can run in parallel

**Phase 5 (Temporal)**:
- T042-T046 (Activities) can run in parallel

**Phase 7 (Intent Classification)**:
- T065A (intent_detection enhancement) can run in parallel with T065B-T065C (prompt templates)
- T065F-T065G (tests) can run in parallel after implementation

**Phase 10 (Advanced)**:
- T087-T089 (prompt enhancements) can run in parallel
- T092-T093 (monitoring endpoints) can run in parallel

**Phase 7 (Intent Classification)**:
- T065A (intent_detection enhancement) can run in parallel with T065B-T065C (prompt templates)
- T065F-T065G (tests) can run in parallel after implementation

**Phase 11 (Testing)**:
- T094-T096 (edge case tests) can run in parallel
- T097-T099 (integration tests) can run in parallel
- T102-T103 (manual testing scripts) can run in parallel

---

## Implementation Strategy

### MVP First (P0 Tasks Only)

1. Complete Phase 1: Setup (T001-T009)
2. Complete Phase 2: Foundational (T010-T019A) - CRITICAL BLOCKER
3. Complete Phase 3: User Story 1 (T020-T033) - Core bot functionality
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

**MVP Scope**: Bot responds to "Mika" mentions with themed content (no song queries, no memory, no images)

### Incremental Delivery

1. **Week 1-2**: Setup + Foundational + US1 → Basic bot working
2. **Week 2-3**: US2 → Song queries working
3. **Week 3-4**: Temporal Integration → Reliability added
4. **Week 4**: US3 → Memory working
5. **Week 4-5**: US4 → Multi-modal working
6. **Week 5**: LangBot + Docker → Production deployment
7. **Week 6**: Intent Classification Enhancement → Contextually appropriate responses
8. **Week 6-7**: Advanced Features + Testing → Production-ready

### Parallel Team Strategy

With multiple developers:

1. **Developer A**: Setup + Foundational (T001-T019A)
2. **Once Foundational complete**:
   - Developer A: US1 core steps (T020-T026)
   - Developer B: US1 FastAPI + tests (T027-T033)
3. **Once US1 complete**:
   - Developer A: US2 song queries (T034-T041)
   - Developer B: Temporal Activities (T042-T046)
4. **Once US2 + Temporal ready**:
   - Developer A: Temporal Workflow (T047-T052)
   - Developer B: US3 memory (T053-T059)
5. **Once US3 complete**:
   - Developer A: US4 multi-modal (T060-T065)
   - Developer B: Intent Classification (T065A-T065G)
6. **Final sprint**:
   - Developer A: LangBot + Docker (T066-T079)
   - Developer B: Advanced features (T080-T093)
   - Developer C: Comprehensive testing (T094-T103)

---

## Effort Summary

| Phase | Tasks | Estimated Hours | Priority |
|-------|-------|----------------|----------|
| Phase 1: Setup | T001-T009 | 8-12h | P0 |
| Phase 2: Foundational | T010-T019A | 19-23h | P0 |
| Phase 3: US1 (MVP) | T020-T033 | 25-31h | P0 |
| Phase 4: US2 | T034-T041 | 15.5-19.5h | P0 |
| Phase 5: Temporal | T042-T052 | 20-24h | P1 |
| Phase 6: US3 | T053-T059 | 12-16h | P1 |
| Phase 7: US4 | T060-T065 | 11-13h | P1 |
| Phase 7: Intent Classification | T065A-T065G | 14-18h | P1 |
| Phase 8: LangBot | T066-T072 | 8-10h | P1 |
| Phase 9: Docker | T073-T079 | 8-10h | P1 |
| Phase 10: Advanced | T080-T093 | 17-21h | P2 |
| Phase 11: Testing | T094-T103 | 24-28h | P2 |
| **Total** | **110 tasks** | **175-227h** | |

**MVP (P0 only)**: ~68-86 hours
**Production Ready (P0+P1)**: ~157-197 hours
**Complete (All)**: ~175-227 hours

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- P0 tasks are MVP-critical and should be completed first
- P1 tasks add production readiness (Temporal, Docker, advanced features)
- P2 tasks add comprehensive testing and polish

---

**Status**: Ready for implementation
**Next Step**: Begin with Phase 1 (Setup) tasks
