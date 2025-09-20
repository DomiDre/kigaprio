#!/bin/sh
set -e

# Check if secrets directory exists and has files
if [ -d "/run/secrets" ]; then
    # for each secret file mounted into /run/secrets
    for secret in /run/secrets/*; do
        # Skip if no files found (glob didn't expand)
        [ -e "$secret" ] || continue
        
        # Skip if not a regular file
        [ -f "$secret" ] || continue
        
        # Get the filename and convert to uppercase for env var name
        name=$(basename "$secret" | tr '[:lower:]' '[:upper:]')
        
        # Read the secret value and export it
        value=$(cat "$secret")
        export "$name"="$value"
        
        echo "Loaded secret: $name"
    done
fi

# exec the real command
exec "$@"
