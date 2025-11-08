#!/bin/sh
# Development scheduler script with more frequent runs for testing
# This runs cleanup tasks more often so you can test the functionality

set -e

echo "Starting KigaPrio cleanup scheduler (DEVELOPMENT MODE)..."
echo "⚠️  Running with shorter intervals for testing purposes"

# Create a crontab for cleanup tasks (more frequent for dev)
cat > /tmp/cleanup-crontab <<EOF
# Run cleanup tasks every hour (instead of daily) for testing
0 * * * * cd /app && uv run python -m kigaprio.scripts.run_cleanup_tasks

# Run monitoring updates every 2 minutes (instead of 5) for testing
*/2 * * * * cd /app && uv run python -m kigaprio.scripts.run_monitoring

# Uncomment to run cleanup on startup (useful for testing)
# @reboot sleep 10 && cd /app && uv run python -m kigaprio.scripts.run_cleanup_tasks
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
exec supercronic /tmp/cleanup-crontab
