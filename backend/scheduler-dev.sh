#!/bin/sh
# Development scheduler script with more frequent runs for testing
# This runs cleanup tasks more often so you can test the functionality

set -e

echo "Starting KigaPrio cleanup scheduler (DEVELOPMENT MODE)..."
echo "⚠️  Running with shorter intervals for testing purposes"

# Create a crontab for cleanup tasks (more frequent for dev)
cat > /tmp/cleanup-crontab <<EOF
# Run cleanup tasks every hour (instead of daily) for testing
*/1 * * * * cd /app && /home/ubuntu/.local/bin/uv run python -m kigaprio.scripts.run_cleanup_tasks

# Run monitoring updates every 2 minutes (instead of 5) for testing
*/1 * * * * cd /app && /home/ubuntu/.local/bin/uv run python -m kigaprio.scripts.run_monitoring
EOF

echo "Development crontab configured:"
cat /tmp/cleanup-crontab
echo ""
echo "📋 Schedule:"
echo "  - Cleanup tasks: Every hour"
echo "  - Monitoring: Every 2 minutes"
echo ""
echo "💡 To manually trigger cleanup, run:"
echo "   docker compose exec scheduler uv run python -m kigaprio.scripts.run_cleanup_tasks"
echo ""

# Run supercronic with the crontab
exec /usr/local/bin/supercronic -debug /tmp/cleanup-crontab
