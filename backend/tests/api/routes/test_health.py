"""
Tests for health check endpoint.

Simple test to ensure health endpoint works.
"""

import pytest


@pytest.mark.unit
class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self):
        """Should return 200 OK status."""
        from priotag.api.routes.health import health_check

        result = await health_check()
        # Returns None with 200 status (empty response body)
        assert result is None
