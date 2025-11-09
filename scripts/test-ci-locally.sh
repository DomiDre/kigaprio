#!/bin/bash
# Script to test CI workflow locally before pushing
# Run from project root: ./scripts/test-ci-locally.sh

set -e

# Change to project root directory (parent of scripts/)
cd "$(dirname "$0")/.."

echo "🧪 Testing CI workflow locally..."
echo ""

if [ -d ".secrets" ]; then
    echo "ℹ️  Your .secrets/ folder will remain untouched"
    echo ""
fi

# Create temporary test secrets directory with unique name
TEST_SECRETS_DIR="$(pwd)/.secrets.ci.test.$$"
echo "📝 Creating test secrets in ${TEST_SECRETS_DIR}/..."
mkdir -p "${TEST_SECRETS_DIR}"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  | openssl pkey -pubout -out "${TEST_SECRETS_DIR}/admin_public_key.pem"
echo "admin@example.com" > "${TEST_SECRETS_DIR}/pb_admin_email"
echo "admintest" > "${TEST_SECRETS_DIR}/pb_admin_password"
echo "service-id-$(openssl rand -hex 16)" > "${TEST_SECRETS_DIR}/pb_service_id"
echo "service-password-$(openssl rand -base64 32)" > "${TEST_SECRETS_DIR}/pb_service_password"
echo "redis-password-$(openssl rand -base64 32)" > "${TEST_SECRETS_DIR}/redis_pass"
echo "cache-key-$(openssl rand -base64 32)" > "${TEST_SECRETS_DIR}/server_cache_key"
echo "metrics-token-$(openssl rand -base64 32)" > "${TEST_SECRETS_DIR}/metrics_token"
echo "✅ Test secrets created"
echo ""

# Export SECRETS_DIR for docker-compose.ci.yml to use
export SECRETS_DIR="${TEST_SECRETS_DIR}"

# Cleanup function
cleanup() {
    local exit_code=$?
    echo ""
    echo "🧹 Cleaning up..."

    # Shutdown docker services
    docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml down -v 2>/dev/null || true

    # Remove test secrets directory
    if [ -d "${TEST_SECRETS_DIR}" ]; then
        echo "🗑️  Removing test secrets"
        rm -rf "${TEST_SECRETS_DIR}"
    fi

    if [ $exit_code -ne 0 ]; then
        echo "❌ Script failed with exit code $exit_code"
    fi

    exit $exit_code
}

# Set trap to ensure cleanup happens even on error
trap cleanup EXIT INT TERM

# Build images
echo "🏗️  Building Docker images..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml build backend pocketbase
echo "✅ Images built"
echo ""

# Start dependencies
echo "🚀 Starting PocketBase and Redis..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml up -d pocketbase redis
echo "⏳ Waiting for services to be healthy..."
timeout 120 sh -c 'until docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml ps pocketbase | grep -q "healthy" && docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml ps redis | grep -q "healthy"; do sleep 2; done'
echo "✅ Services are ready!"
echo ""

# Initialize PocketBase admin
echo "👤 Creating PocketBase superuser..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml run --rm pocketbase \
  ./pocketbase superuser upsert admin@example.com admintest
echo "✅ Superuser created"
echo ""

# Setup PocketBase data (magic word, service account)
echo "🔧 Setting up PocketBase test data..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml run --rm backend \
  uv run python tests/integration/setup_pocketbase.py
echo "✅ PocketBase data setup complete"
echo ""

# Run tests
echo "🧪 Running tests with coverage..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml run --rm \
  backend \
  uv run pytest --cov=kigaprio --cov-report=xml --cov-report=term-missing

# Copy coverage report
echo ""
echo "📊 Copying coverage report..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml run --rm \
  backend \
  cat coverage.xml > coverage.xml 2>/dev/null || echo "⚠️  No coverage file found"

echo ""
echo "✅ CI test completed successfully!"
echo "📊 Coverage report saved to: coverage.xml"
