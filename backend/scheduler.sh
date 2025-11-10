#!/bin/sh
# Scheduler script that runs cleanup tasks on a schedule using supercronic
# supercronic is a cron-compatible job runner designed for containers

set -e

echo "Starting PrioTag cleanup scheduler..."

# Create a crontab for cleanup tasks
cat > /tmp/cleanup-crontab <<EOF
# Run cleanup tasks daily at 2 AM
0 2 * * * python -m priotag.scripts.run_cleanup_tasks

# Run monitoring updates every 5 minutes (for health checks and metrics)
*/5 * * * * python -m priotag.scripts.run_monitoring
EOF

echo "Crontab configured:"
cat /tmp/cleanup-crontab

# Run supercronic with the crontab
exec /usr/local/bin/supercronic /tmp/cleanup-crontab
