#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_DIR=$(realpath "$SCRIPT_DIR/..")

cd $PROJECT_DIR

if [ -f "pocketbase/pb_data/data.db" ]; then
    # database already exists. Assuming it was properly initialized
    exit 0
fi

echo "No database found. Initializing..."

# Create directories if they don't exist
echo "Checking if pocketbase directories exist"
mkdir -p pocketbase/pb_data
mkdir -p pocketbase/pb_public
mkdir -p pocketbase/pb_migrations
mkdir -p pocketbase/pb_hooks

# Check if we need sudo
if [ ! -w "pocketbase/pb_data" ]; then
    # We cant write
    if [ "$EUID" -eq 0 ]; then
        # Running as root
        chown -R 1000:1000 pocketbase/pb_*
        echo "✓ Ownership set to UID/GID 1000"
    else
        # Not root, try with sudo
        echo "Need elevated permissions to fix ownership..."
        sudo chown -R 1000:1000 pocketbase/pb_*
        echo "✓ Ownership set to UID/GID 1000"
    fi
fi


# run command to initialize superuser
if [ ! -f "$PROJECT_DIR/.secrets/pb_admin_email" ]; then
    echo "Missing definition of pocketbase admin mail. Aborting initialization"
    exit 1;
fi
if [ ! -f "$PROJECT_DIR/.secrets/pb_admin_password" ]; then
    echo "Missing definition of pocketbase admin password. Aborting initialization"
    exit 1;
fi

echo "Setting password to $(cat $PROJECT_DIR/.secrets/pb_admin_password)"
docker compose -f docker-compose.dev.yml run --rm pocketbase ./pocketbase superuser upsert $(cat $PROJECT_DIR/.secrets/pb_admin_email) $(cat $PROJECT_DIR/.secrets/pb_admin_password)

# check that db file was created
if [ ! -f "pocketbase/pb_data/data.db" ]; then
    # exit with error in case it is missing
    exit 1
fi

