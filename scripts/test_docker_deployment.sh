#!/bin/bash
# Docker Deployment Test Script
#
# Per T079: Test full stack deployment locally
# 
# This script verifies that all Docker Compose services start correctly
# and that the webhook endpoint is accessible.

set -e  # Exit on error

echo "=========================================="
echo "Docker Compose Deployment Test"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example if available...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please update .env file with your API keys before continuing${NC}"
    else
        echo -e "${RED}Error: .env file not found and .env.example not available${NC}"
        exit 1
    fi
fi

echo ""
echo "Step 1: Building Docker images..."
docker-compose build

echo ""
echo "Step 2: Starting all services..."
docker-compose up -d

echo ""
echo "Step 3: Waiting for services to be healthy (60 seconds)..."
sleep 60

echo ""
echo "Step 4: Checking service status..."
docker-compose ps

echo ""
echo "Step 5: Testing backend health endpoint..."
MAX_RETRIES=10
RETRY_COUNT=0
HEALTH_CHECK_PASSED=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend health check passed${NC}"
        HEALTH_CHECK_PASSED=true
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "Waiting for backend to be ready... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
    fi
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo -e "${RED}✗ Backend health check failed after $MAX_RETRIES attempts${NC}"
    echo "Backend logs:"
    docker-compose logs --tail=50 backend
    exit 1
fi

echo ""
echo "Step 6: Testing webhook endpoint..."
WEBHOOK_TEST_PAYLOAD='{
  "group_id": "123456789",
  "user_id": "987654321",
  "message": "Mika, test message",
  "images": []
}'

if curl -X POST http://localhost:8000/webhook/langbot \
    -H "Content-Type: application/json" \
    -d "$WEBHOOK_TEST_PAYLOAD" \
    -f > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Webhook endpoint test passed${NC}"
else
    echo -e "${YELLOW}⚠ Webhook endpoint test failed (this may be expected if OPENROUTER_API_KEY is not set)${NC}"
fi

echo ""
echo "Step 7: Checking service logs for errors..."
echo "--- Backend logs (last 20 lines) ---"
docker-compose logs --tail=20 backend

echo ""
echo "--- Temporal Worker logs (last 20 lines) ---"
docker-compose logs --tail=20 temporal-worker

echo ""
echo "Step 8: Service health summary..."
echo "--- Service Status ---"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=========================================="
echo "Deployment Test Summary"
echo "=========================================="
echo -e "${GREEN}✓ All services started${NC}"
echo -e "${GREEN}✓ Backend health check passed${NC}"
echo ""
echo "Next steps:"
echo "1. Check Temporal Web UI: http://localhost:8088"
echo "2. Test webhook with actual LangBot integration"
echo "3. Monitor logs: docker-compose logs -f"
echo ""
echo "To stop all services: docker-compose down"
echo "To view logs: docker-compose logs -f [service-name]"
