# List available commands
default:
    @just --list

# Start development environment
dev:
    docker compose -f docker-compose.dev.yml up

# Start development environment with rebuild
dev-build:
    docker compose -f docker-compose.dev.yml up --build

# Start development environment in detached mode
dev-detached:
    docker compose -f docker-compose.dev.yml up -d

# Start production environment
prod:
    docker compose up -d

# Build production images without cache
build-prod:
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
    docker compose exec backend /bin/bash

# Open shell in backend container (development)
shell-backend-dev:
    docker compose -f docker-compose.dev.yml exec backend /bin/bash

# Open shell in frontend container
shell-frontend:
    docker compose exec frontend /bin/sh

# Open shell in frontend container (development)
shell-frontend-dev:
    docker compose -f docker-compose.dev.yml exec frontend /bin/sh

# Run database migrations
migrate:
    docker compose exec backend uv run alembic upgrade head

# Run database migrations (development)
migrate-dev:
    docker compose -f docker-compose.dev.yml exec backend uv run alembic upgrade head

# Create a new migration
migration-create name:
    docker compose -f docker-compose.dev.yml exec backend uv run alembic revision --autogenerate -m "{{name}}"

# Backup database
backup:
    #!/usr/bin/env bash
    mkdir -p backup
    echo "Backing up database..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    docker compose exec db pg_dump -U ${DB_USER:-user} ${DB_NAME:-kigaprio} > backup/backup_${timestamp}.sql
    echo "Backup completed: backup/backup_${timestamp}.sql"

# Backup database (development)
backup-dev:
    #!/usr/bin/env bash
    mkdir -p backup
    echo "Backing up development database..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    docker compose -f docker-compose.dev.yml exec db pg_dump -U user kigaprio > backup/backup_dev_${timestamp}.sql
    echo "Backup completed: backup/backup_dev_${timestamp}.sql"

# List available backups
list-backups:
    @ls -la backup/*.sql 2>/dev/null || echo "No backups found"

# Restore database from backup
restore backup_file:
    #!/usr/bin/env bash
    if [ ! -f "{{backup_file}}" ]; then
        echo "Backup file not found: {{backup_file}}"
        exit 1
    fi
    echo "Restoring database from {{backup_file}}..."
    docker compose exec -T db psql -U ${DB_USER:-user} ${DB_NAME:-kigaprio} < {{backup_file}}
    echo "Restore completed!"

# Restore database from backup (development)
restore-dev backup_file:
    #!/usr/bin/env bash
    if [ ! -f "{{backup_file}}" ]; then
        echo "Backup file not found: {{backup_file}}"
        exit 1
    fi
    echo "Restoring development database from {{backup_file}}..."
    docker compose -f docker-compose.dev.yml exec -T db psql -U user kigaprio < {{backup_file}}
    echo "Restore completed!"

# Run backend tests
test-backend:
    docker compose -f docker-compose.dev.yml exec backend uv run pytest

# Run frontend tests
test-frontend:
    docker compose -f docker-compose.dev.yml exec frontend npm test

# Run all tests
test: test-backend test-frontend

# Format backend code
format-backend:
    docker compose -f docker-compose.dev.yml exec backend uv run ruff format .
    docker compose -f docker-compose.dev.yml exec backend uv run ruff check --fix .

# Format frontend code
format-frontend:
    docker compose -f docker-compose.dev.yml exec frontend npm run format

# Format all code
format: format-backend format-frontend

# Lint backend code
lint-backend:
    docker compose -f docker-compose.dev.yml exec backend uv run ruff check .
    docker compose -f docker-compose.dev.yml exec backend uv run mypy .

# Lint frontend code  
lint-frontend:
    docker compose -f docker-compose.dev.yml exec frontend npm run lint

# Lint all code
lint: lint-backend lint-frontend

# Clean up Docker system
clean:
    docker compose down -v
    docker compose -f docker-compose.dev.yml down -v
    docker system prune -af

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

# Scale a service
scale service count:
    docker compose up -d --scale {{service}}={{count}}

# Execute command in backend container
exec-backend command:
    docker compose -f docker-compose.dev.yml exec backend {{command}}

# Execute command in frontend container
exec-frontend command:
    docker compose -f docker-compose.dev.yml exec frontend {{command}}

# View environment variables
env:
    docker compose -f docker-compose.dev.yml exec backend env | sort

# Create production deployment on server
deploy:
    #!/usr/bin/env bash
    echo "Building and pushing images..."
    docker compose build
    echo "Deploying to production..."
    ssh ${DEPLOY_USER}@${DEPLOY_HOST} "cd /opt/kigaprio && git pull && docker compose pull && docker-compose up -d"
    echo "Deployment completed!"

# SSH into production server
ssh-prod:
    ssh ${DEPLOY_USER}@${DEPLOY_HOST}

# View production logs
logs-prod:
    ssh ${DEPLOY_USER}@${DEPLOY_HOST} "cd /opt/kigaprio && docker compose logs -f"

# Quick health check
health:
    @curl -s http://localhost:8000/api/health | jq . || echo "Backend not responding"
    @curl -s http://localhost:5173 > /dev/null && echo "Frontend is running" || echo "Frontend not responding"

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

# Initialize project (first time setup)
init:
    #!/usr/bin/env bash
    echo "Initializing project..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
    echo "Creating necessary directories..."
    mkdir -p backup data/uploads nginx
    echo "Initialization complete! Run 'just dev' to start development"

# Generate secret key for production
generate-secret:
    @python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Create htpasswd for Traefik dashboard
generate-htpasswd username:
    @docker run --rm -it httpd:alpine htpasswd -nb {{username}} | sed 's/\$/\$\$/g'
