# List available commands
default:
    @just --list

# Start development environment
dev:
    docker compose -f docker-compose.dev.yml up

# Build dev images
dev-build:
    docker compose -f docker-compose.dev.yml build

# Start development environment in detached mode
dev-detached:
    docker compose -f docker-compose.dev.yml up -d

# Start production environment
prod:
    docker compose up -d

# Build production images
build:
    docker compose build

# Build production images without cache
build-no-cache:
    docker compose build --no-cache

# Stop all containers
down:
    docker compose down
    docker compose -f docker-compose.dev.yml down

# Stop all containers and remove volumes
down-volumes:
    docker compose down -v
    docker compose -f docker-compose.dev.yml down -v

# View container logs
logs service="":
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker compose logs -f
    else
        docker compose logs -f {{service}}
    fi

# View development container logs
logs-dev service="":
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker compose -f docker-compose.dev.yml logs -f
    else
        docker compose -f docker-compose.dev.yml logs -f {{service}}
    fi

# Open shell in backend container
shell-backend:
    docker compose run --rm -it backend /bin/bash

# Open shell in backend container (development)
shell-backend-dev:
    docker compose -f docker-compose.dev.yml run --rm -it backend /bin/bash

# Open shell in frontend container
shell-frontend:
    docker compose run --rm -it frontend /bin/sh

# Open shell in frontend container (development)
shell-frontend-dev:
    docker compose -f docker-compose.dev.yml run --rm -it frontend /bin/sh

# Run backend tests
test-backend:
    docker compose -f docker-compose.dev.yml run --rm backend uv run pytest

# Run frontend tests
test-frontend:
    docker compose -f docker-compose.dev.yml run --rm frontend npm test

# Run all tests
test: test-backend test-frontend

# Format backend code
format-backend:
    docker compose -f docker-compose.dev.yml run --rm backend uv run ruff format .
    docker compose -f docker-compose.dev.yml run --rm backend uv run ruff check --fix .

# Format frontend code
format-frontend:
    docker compose -f docker-compose.dev.yml run --rm frontend npm run format

# Format all code
format: format-backend format-frontend

# Lint backend code
lint-backend:
    docker compose -f docker-compose.dev.yml run --rm backend uv run ruff check .
    docker compose -f docker-compose.dev.yml run --rm backend uv run mypy .

# Lint frontend code  
lint-frontend:
    docker compose -f docker-compose.dev.yml run --rm frontend npm run lint

# Lint all code
lint: lint-backend lint-frontend

# Clean up Docker system
clean:
    docker compose down -v
    docker compose -f docker-compose.dev.yml down -v

# Check Docker stats
stats:
    docker stats

# Show running containers
ps:
    docker compose ps
    docker compose -f docker-compose.dev.yml ps

# Pull latest images
pull:
    docker compose pull
    docker compose -f docker-compose.dev.yml pull

# Restart a specific service
restart service:
    docker compose restart {{service}}

# Restart a specific service (development)
restart-dev service:
    docker compose -f docker-compose.dev.yml restart {{service}}

# Execute command in backend container
exec-backend command:
    docker compose -f docker-compose.dev.yml exec backend {{command}}

# Execute command in frontend container
exec-frontend command:
    docker compose -f docker-compose.dev.yml exec frontend {{command}}

# View environment variables
env:
    docker compose -f docker-compose.dev.yml exec backend env | sort

# Build frontend static files in development
build-frontend-dev:
    docker compose -f docker-compose.dev.yml exec frontend npm run build
    @echo "Frontend built! Static files are now available."

# Copy built frontend files to backend (for testing static serving)
copy-static-to-backend:
    #!/usr/bin/env bash
    echo "Building frontend..."
    docker compose -f docker-compose.dev.yml exec frontend npm run build
    echo "Copying static files to backend..."
    docker cp kigaprio-frontend-dev:/app/build/. kigaprio-backend-dev:/app/static/
    echo "Static files copied! Access at http://localhost:8000"

# Run development with static file building
dev-with-static:
    docker compose -f docker-compose.dev-with-static.yml up

# Initialize secrets needed for running containers
init-secrets:
    ./scripts/init-secrets.sh

# Initialize the admin public / private key, where public key is needed for the server to run
init-admin-key:
    #!/usr/bin/env bash
    docker run --rm -it -v ./backend:/app kigaprio-backend:dev uv run src/kigaprio/scripts/initialize_admin_keypair.py
    mv ./backend/admin_public_key.pem ./.secrets/
    mv ./backend/admin_private_key.pem ./

# Initialize pocketbase directories for storage
pocketbase-init: init-secrets
    ./pocketbase/init.sh

redis-init:
    #!/usr/bin/env bash
    echo "Initializing Redis persistence..."
    mkdir -p redis_data
    chmod 700 redis_data
    echo "Creating user for redis"
    sudo useradd --system \
      --uid 10001 --gid 10001 \
      --no-create-home \
      --shell /usr/sbin/nologin \
      redis-kigaprio
    echo "Setting ownership (requires sudo)..."
    sudo chown -R 10001:10001 redis_data || echo "⚠️  Could not set ownership - run: sudo chown -R 999:999 redis_data"
    echo "Redis persistence initialized"

# Reset redis cache
redis-clear:
    docker compose -f ./docker-compose.dev.yml exec redis redis-cli FLUSHALL
