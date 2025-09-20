#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_DIR=$(realpath "$SCRIPT_DIR/..")
SECRETS_DIR="$PROJECT_DIR/.secrets"

mkdir -p "$SECRETS_DIR"

# Define secrets as "name:default" pairs. Use "RANDOM" for random generation, "PROMPT" to prompt user, or a fixed string.
# For random, we'll generate a 16-char alphanumeric string.
declare -a secrets=(
	"pb_admin_email:PROMPT"
	"pb_admin_password:RANDOM"
)

generate_random() {
	set +o pipefail # Temporarily disable pipefail to ignore expected SIGPIPE from tr when head closes the pipe
	tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32
}

for item in "${secrets[@]}"; do
	name="${item%%:*}"
	default="${item#*:}"
	file="$SECRETS_DIR/$name"

	if [ ! -f "$file" ]; then
		if [ "$default" = "RANDOM" ]; then
			value=$(generate_random)
			echo "$value" >"$file"
			echo "Created random $name secret file."
		elif [ "$default" = "PROMPT" ]; then
			read -rp "Enter value for $name: " value
			echo "$value" >"$file"
			echo "Created $name secret file from user input."
		else
			echo "$default" >"$file"
			echo "Created default $name secret file."
		fi
	fi
done

