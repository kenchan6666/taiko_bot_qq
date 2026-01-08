<!--
Sync Impact Report:
Version change: (none) → 1.0.0
Modified principles: (none - initial creation)
Added sections: Core Principles (4 principles), Development Guidelines (4 subsections), Governance and Maintenance
Removed sections: (none - initial creation)
Templates requiring updates:
  ✅ plan-template.md - Constitution Check section will reference these principles
  ✅ spec-template.md - No changes needed (constitution-agnostic)
  ✅ tasks-template.md - No changes needed (constitution-agnostic)
  ✅ commands/*.md - No changes needed (constitution-agnostic)
Follow-up TODOs: (none)
-->

# Taiko Bot (Mika) Constitution

## Core Principles

These are the non-negotiable values that guide every aspect of the project.

### I. Fun and Thematic Consistency

The bot must embody the spirit of Taiko no Tatsujin: joyful, rhythmic, and engaging. All responses should incorporate game elements like "Don!", "Katsu!", emojis (🥁🎶), and references to songs, difficulties (e.g., 10-star as "extreme challenge"), BPM (e.g., 300+ as "super fast"), and characters (e.g., Don-chan).

User interactions should feel playful and encouraging, promoting positive experiences like "Full Combo!" for successes.

Avoid overly serious or off-theme content; prioritize entertainment while providing useful info (e.g., song queries via taikowiki JSON).

### II. User Privacy and Safety

Handle user data (e.g., conversation history, impressions, relationships) with strict privacy: Use MongoDB (via Beanie) for storage, encrypt sensitive fields if needed, and comply with GDPR-like principles (no sharing without consent).

Never store or log QQ user IDs, messages, or personal info beyond what's necessary for bot functionality (e.g., memory for contextual responses).

Implement safeguards against harmful content: Filter out disallowed activities per safety instructions (e.g., no violence, no child exploitation).

Bot should only respond when explicitly called by name ("Mika" or variants), to prevent spam in large groups.

### III. Reliability and Scalability

The system must handle multi-group concurrency (e.g., dozens of QQ groups) without failures: Use Temporal for workflow orchestration to ensure retries, timeouts, and fault tolerance in the 5-step processing chain.

Performance goals: Response time < 3 seconds (using gpt-4o via OpenRouter); handle up to 100 concurrent requests with Uvicorn workers.

Error handling: Graceful degradation (e.g., fallback to local cache if taikowiki JSON fetch fails); log errors without exposing details to users.

### IV. Ethical AI Usage

LLM (gpt-4o) must be used responsibly: Prompts should inject Taiko drum knowledge (e.g., difficulty stars, BPM insights) and bot identity ("Mika" as a cute drum spirit).

Avoid biases: Responses should be inclusive, culturally sensitive (e.g., respect Japanese origins of Taiko), and fact-based (e.g., song data from reliable sources like taikowiki).

Transparency: If the bot "learns" from conversations (via impression updates), inform users subtly (e.g., "Mika remembers you like high-BPM songs!").

## Development Guidelines

These standards ensure high-quality code and processes, aligned with Spec-Kit methodology.

### Code Quality and Structure

**Language**: Python 3.12+ exclusively.

**Dependency Management**: Use Poetry for all dependencies; lock versions in poetry.lock.

**Project Structure**: Follow modular design with main flow in step1.py to step5.py; auxiliaries in config.py, database.py (Beanie), llm.py (OpenRouter/gpt-4o), song_query.py, prompts.py.

**Coding Standards**:

* PEP 8 compliance (use Black for formatting).
* Type hints everywhere (via Pydantic/Beanie).
* No hard-coded secrets: API keys (e.g., OpenRouter key) in environment variables or config.py via os.getenv.

**Version Control**: Git with feature branches (e.g., via Spec-Kit auto-branching); commit messages follow Conventional Commits.

### Testing Standards

**Coverage**: Aim for 80%+ unit/integration tests (pytest); test each step function individually and the full chain.

**Types**:

* Unit: Test isolated functions (e.g., song_query fuzzy matching).
* Integration: End-to-end flows (e.g., message processing with mocked LLM).
* Edge Cases: Name detection variants, high-concurrency simulations, error scenarios (e.g., network failure).

**CI/CD**: Use GitHub Actions for automated tests on PRs.

### User Experience Consistency

**Bot Identity**: Fixed as "Mika" (configurable via get_bot_name() function in config.py); responses always themed.

**Multi-Modal**: Support text + images (e.g., describe Taiko screenshots via gpt-4o vision).

**Accessibility**: Responses should be readable (short paragraphs, emojis for visual aid); support multiple languages if queried (e.g., Chinese/English).

**Feedback Loop**: Bot "improves" via MongoDB updates; periodically review stored impressions for privacy.

### Performance and Deployment Requirements

**Deployment**: Docker Compose mandatory for production (services: backend, mongo, temporal, langbot, napcat, optional nginx).

**Monitoring**: Integrate logging (structlog) and metrics (e.g., response times); alert on failures.

**Scalability**: Design for large QQ groups (rate limiting in LangBot); use Redis if caching needs expand.

**Resource Limits**: Optimize for mid-tier VPS (4-core, 8GB RAM); gpt-4o calls budgeted (e.g., < $0.01 per query).

## Governance and Maintenance

**Decision-Making**: All changes must align with this constitution; major updates require review against principles.

**Updates to Constitution**: Use /speckit.constitution to refine (e.g., add new principles based on user feedback).

**Compliance Checks**: During Spec-Kit /speckit.analyze, verify specs/plans/tasks against this document.

**Ethical Reviews**: Periodically audit bot behavior (e.g., no promotion of disallowed activities per safety instructions).

**Open-Source Considerations**: If public, license under MIT; attribute sources (e.g., taikowiki JSON).

**Version**: 1.0.0 | **Ratified**: 2026-01-08 | **Last Amended**: 2026-01-08
