# Quickstart Guide: Mika Taiko Chatbot

**Feature**: `1-mika-bot`  
**Date**: 2026-01-08

This guide provides step-by-step instructions for setting up and running the Mika Taiko Chatbot locally and in production.

## Prerequisites

- **Python**: 3.12 or higher
- **Poetry**: 1.6+ ([installation guide](https://python-poetry.org/docs/#installation))
- **Docker & Docker Compose**: For production deployment
- **MongoDB**: 7.0+ (can use Docker)
- **Temporal Server**: Can use Docker
- **OpenRouter API Key**: Sign up at [openrouter.ai](https://openrouter.ai)
- **ngrok** (for local development): For exposing local webhook endpoint to LangBot - [download ngrok](https://ngrok.com/download)

## Local Development Setup

### 1. Clone Repository and Install Dependencies

```bash
# Clone repository (if applicable)
git clone <repository-url>
cd taiko_bot

# Install dependencies using Poetry
poetry install

# Activate virtual environment
poetry shell
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=mika_bot

# Temporal
TEMPORAL_HOST=localhost
TEMPORAL_PORT=7233
TEMPORAL_NAMESPACE=default

# OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key_here

# LangBot
LANGBOT_WEBHOOK_URL=http://localhost:8000/webhook/langbot
LANGBOT_ALLOWED_GROUPS=123456789,987654321  # Comma-separated QQ group IDs

# Application
BOT_NAME=Mika
LOG_LEVEL=INFO
```

### 3. Start MongoDB and Temporal (Docker)

```bash
# Start MongoDB
docker run -d -p 27017:27017 --name mongo mongo:7.0

# Start Temporal (using Temporal Docker Compose)
git clone https://github.com/temporalio/docker-compose.git temporal-docker
cd temporal-docker
docker-compose up -d
cd ..
```

Or use the provided `docker-compose.yml` for all services:

```bash
docker-compose up -d mongo temporal
```

### 4. Initialize Database

```bash
# Run database initialization script (if provided)
python scripts/init_database.py

# Or manually create indexes via Beanie
python -c "from src.services.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 5. Load Song Data

```bash
# Fetch and cache taikowiki song data
python scripts/seed_songs.py
```

### 6. Run FastAPI Application

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or using Poetry
poetry run uvicorn src.api.main:app --reload
```

### 7. Run Temporal Worker

In a separate terminal:

```bash
# Start Temporal worker to process workflows
poetry run python src/workers/temporal_worker.py
```

### 8. Expose Webhook for LangBot (Local Development)

If you're running LangBot separately and need to connect it to your local FastAPI backend, use ngrok to expose the webhook endpoint:

```bash
# In a new terminal, start ngrok tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Use this URL in LangBot configuration: https://abc123.ngrok.io/webhook/langbot
```

**Note**: For production deployment, use a public domain or IP address instead of ngrok.

### 9. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Test webhook locally (simulate LangBot message)
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "Mika, what is the BPM of 千本桜?",
    "images": []
  }'

# If using ngrok, test via public URL:
# curl -X POST https://your-ngrok-url.ngrok.io/webhook/langbot \
#   -H "Content-Type: application/json" \
#   -d '{...}'
```

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_step1.py

# Run integration tests
poetry run pytest tests/integration/
```

## Docker Compose Deployment

### Full Stack Deployment

The `docker-compose.yml` file includes all required services that MUST run continuously (per NFR-013):

**Required Services** (must run continuously, deployed in this project):
- **backend**: FastAPI backend + Temporal client (handles webhooks, calls gpt-4o, executes 5-step chain)
- **temporal-worker**: Temporal worker to process workflows
- **temporal**: Temporal server (workflow engine must be online to schedule tasks and retries)
- **temporal-postgresql**: PostgreSQL database for Temporal (workflow state storage)
- **mongo**: MongoDB (must store user history and impressions; downtime causes memory loss)

**Recommended Service**:
- **nginx**: Reverse proxy with HTTPS and load balancing (strongly recommended for stable public network entry point)

**External Services** (must run continuously, deployed separately):
- **LangBot**: Core bot platform (must receive QQ messages and manage triggers). Deployed separately, connects to FastAPI backend via webhook at `/webhook/langbot`
- **Napcat**: QQ protocol layer (must keep bot account online; downtime prevents message reception). Deployed separately or as part of LangBot deployment

```yaml
services:
  backend:
    build: ./docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://mongo:27017
      - TEMPORAL_HOST=temporal
    depends_on:
      - mongo
      - temporal
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  temporal-worker:
    build: ./docker/Dockerfile.temporal
    depends_on:
      - temporal
      - mongo
    environment:
      - TEMPORAL_HOST=temporal:7233
      - MONGODB_URL=mongodb://mongo:27017
    restart: unless-stopped

  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    depends_on:
      - temporal-postgresql
    healthcheck:
      test: ["CMD", "tctl", "cluster", "health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  temporal-postgresql:
    image: postgres:15
    environment:
      - POSTGRES_DB=temporal
      - POSTGRES_USER=temporal
      - POSTGRES_PASSWORD=temporal
    volumes:
      - temporal_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U temporal"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  mongo:
    image: mongo:7.0
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  nginx:
    # LangBot service configuration
    # Must run continuously to receive QQ messages
    restart: unless-stopped
    # ...

  napcat:
    # Napcat service configuration
    # Must run continuously to keep bot account online
    restart: unless-stopped
    # ...

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  mongo_data:
  temporal_postgres_data:
```

### Deploy

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### External Services Setup

**Important**: LangBot and Napcat are external services that must be deployed separately. They are not included in this project's Docker Compose stack.

1. **Deploy LangBot** (follow LangBot official documentation):
   - Install and configure LangBot separately
   - Configure LangBot to send webhooks to your FastAPI backend: `http://your-backend-url:8000/webhook/langbot`
   - Ensure LangBot is running continuously

2. **Deploy Napcat** (if not included in LangBot deployment):
   - Install and configure Napcat separately
   - Configure Napcat to connect to LangBot (if required)
   - Ensure Napcat is running continuously

3. **Verify Connection**:
   - **For local development**: Ensure ngrok (or your tunneling service) is running and FastAPI backend is accessible
   - **For production**: Ensure FastAPI backend is accessible from the internet (check firewall rules, Nginx configuration)
   - Test webhook endpoint: `curl -X POST http://your-backend-url:8000/webhook/langbot` (or `https://` if using HTTPS)
   - Check LangBot logs to confirm successful webhook delivery
   - Check FastAPI backend logs to confirm webhook requests are being received

## LangBot Configuration (External Service)

**Note**: LangBot is deployed as an external service, separate from this project. Follow these steps to configure LangBot to connect to the FastAPI backend.

### 1. Install LangBot

Follow LangBot installation instructions for your platform. Refer to [LangBot official documentation](https://docs.langbot.app) for installation steps.

### 2. Expose Webhook Endpoint

**Important**: LangBot needs to be able to access your FastAPI backend's webhook endpoint. The method depends on your deployment environment:

#### Option A: Local Development (Using ngrok or similar)

If your FastAPI backend is running locally (localhost), you need to expose it to the internet using a tunneling service:

**Using ngrok** (recommended for local development):

```bash
# Install ngrok: https://ngrok.com/download
# Start ngrok tunnel
ngrok http 8000

# You'll get a public URL like: https://abc123.ngrok.io
# Use this URL in LangBot configuration
```

**Using other tunneling services**:
- Cloudflare Tunnel (`cloudflared`)
- localtunnel (`npx localtunnel --port 8000`)
- serveo (`ssh -R 80:localhost:8000 serveo.net`)

#### Option B: Production Deployment (Public IP/Domain)

If your FastAPI backend is deployed on a server with a public IP or domain:

- **With Nginx reverse proxy**: Use your domain with HTTPS (e.g., `https://api.yourdomain.com/webhook/langbot`)
- **Direct access**: Use your server's public IP (e.g., `http://your-server-ip:8000/webhook/langbot`)
- **Cloud deployment**: Use your cloud provider's load balancer URL

### 3. Configure Keyword Trigger

In LangBot configuration file, set up keyword trigger to send webhooks to the FastAPI backend:

**For local development (with ngrok)**:
```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    webhook_url: "https://abc123.ngrok.io/webhook/langbot"
```

**For production (with domain)**:
```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    webhook_url: "https://api.yourdomain.com/webhook/langbot"
```

**For production (with public IP)**:
```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    webhook_url: "http://your-server-ip:8000/webhook/langbot"
```

Replace the URL with your actual FastAPI backend URL.

### 4. Configure Group Whitelist

Set `LANGBOT_ALLOWED_GROUPS` environment variable in LangBot deployment or in LangBot config:

```yaml
allowed_groups:
  - "123456789"
  - "987654321"
```

Or set environment variable:
```bash
export LANGBOT_ALLOWED_GROUPS="123456789,987654321"
```

### 5. Start LangBot

```bash
# Start LangBot service (follow LangBot installation instructions)
langbot start

# Or if using Docker:
docker-compose -f /path/to/langbot/docker-compose.yml up -d
```

### 6. Verify Connection

After starting both FastAPI backend and LangBot:

```bash
# Test webhook endpoint from LangBot perspective
curl -X POST http://your-backend-url:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "Mika, test message",
    "images": []
  }'

# Check FastAPI backend logs to confirm webhook received
docker-compose logs -f backend
```

## Production Deployment

### 1. Environment Variables

Set all required environment variables in your deployment platform (e.g., Kubernetes, Docker Swarm, VPS).

### 2. Database Setup

- Use managed MongoDB (MongoDB Atlas) or self-hosted with backups
- Ensure indexes are created (Beanie auto-creates on startup)

### 3. Temporal Setup

- Deploy Temporal server (can use Temporal Cloud or self-hosted)
- Configure Temporal namespace and connection settings

### 4. Monitoring

- Set up logging aggregation (e.g., ELK, Loki)
- Configure health check endpoints (`/health`, `/metrics`)
- Set up alerts for:
  - High error rates
  - Rate limit violations
  - OpenRouter API failures
  - MongoDB connection issues

### 5. Cleanup Job

Set up a cron job or Temporal scheduled workflow for 90-day conversation cleanup:

```bash
# Daily cleanup job
0 2 * * * cd /path/to/taiko_bot && poetry run python scripts/cleanup_old_conversations.py
```

Or use Temporal scheduled workflow (recommended).

## Troubleshooting

### MongoDB Connection Issues

```bash
# Check MongoDB is running
docker ps | grep mongo

# Test connection
python -c "from motor.motor_asyncio import AsyncIOMotorClient; import asyncio; asyncio.run(AsyncIOMotorClient('mongodb://localhost:27017').admin.command('ping'))"
```

### Temporal Connection Issues

```bash
# Check Temporal is running
docker ps | grep temporal

# Test connection
temporal workflow list
```

### OpenRouter API Issues

- Verify API key is correct
- Check API usage limits in OpenRouter dashboard
- Monitor token usage and costs

### Rate Limiting

- Check rate limit logs in application logs
- Verify rate limit configuration matches requirements (20/user/min, 50/group/min)
- Consider Redis for distributed rate limiting in production

## Development Workflow

1. **Make Changes**: Edit code in `src/` directory
2. **Run Tests**: `poetry run pytest`
3. **Format Code**: `poetry run black src/ tests/`
4. **Type Check**: `poetry run mypy src/` (if configured)
5. **Commit**: Follow Conventional Commits format
6. **Test Locally**: Run FastAPI and Temporal worker
7. **Deploy**: Use Docker Compose or production deployment method

## Next Steps

- Review [plan.md](./plan.md) for architecture details
- Review [data-model.md](./data-model.md) for database schema
- Review [contracts/](./contracts/) for API definitions
- Run `/speckit.tasks` to generate task breakdown

---

**Questions?** Check the main [plan.md](./plan.md) or project documentation.
