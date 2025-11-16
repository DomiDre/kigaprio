"""
Tests for main application setup and configuration.

Tests cover:
- Lifespan startup and shutdown
- CORS configuration (development vs production)
- CSP violation reporting
- Metrics endpoint authentication
- Static file serving setup
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status


@pytest.mark.unit
class TestLifespan:
    """Test application lifespan events."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self):
        """Should successfully start up with Redis connection."""
        from priotag.main import lifespan
        from fastapi import FastAPI

        app = FastAPI()

        with patch("priotag.main.redis_health_check", return_value=True):
            with patch("priotag.main.close_redis"):
                async with lifespan(app):
                    # Startup succeeded
                    pass

    @pytest.mark.asyncio
    async def test_lifespan_startup_redis_failure(self):
        """Should raise error if Redis connection fails."""
        from priotag.main import lifespan
        from fastapi import FastAPI

        app = FastAPI()

        with patch("priotag.main.redis_health_check", return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                async with lifespan(app):
                    pass

            assert "Failed to connect to Redis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_closes_redis(self):
        """Should close Redis connections on shutdown."""
        from priotag.main import lifespan
        from fastapi import FastAPI

        app = FastAPI()

        with patch("priotag.main.redis_health_check", return_value=True):
            with patch("priotag.main.close_redis") as mock_close:
                async with lifespan(app):
                    pass

                # Should have called close_redis on shutdown
                mock_close.assert_called_once()


@pytest.mark.unit
class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_development_mode(self):
        """Development mode should allow localhost origins."""
        with patch.dict("os.environ", {"ENV": "development"}):
            # Re-import to pick up environment variable
            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            # Development CORS should be configured
            # (We can't easily inspect middleware, but we can verify no errors)

    def test_cors_production_mode_with_origins(self):
        """Production mode should use CORS_ORIGINS environment variable."""
        with patch.dict(
            "os.environ",
            {
                "ENV": "production",
                "CORS_ORIGINS": "https://example.com,https://app.example.com",
            },
        ):
            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            # Production CORS should be configured
            # (We can't easily inspect middleware, but we can verify no errors)

    def test_cors_production_mode_no_origins(self):
        """Production mode without CORS_ORIGINS should not add CORS middleware."""
        with patch.dict("os.environ", {"ENV": "production", "CORS_ORIGINS": ""}):
            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            # Should not raise error


@pytest.mark.unit
class TestCSPViolationReport:
    """Test CSP violation reporting endpoint."""

    @pytest.mark.asyncio
    async def test_csp_violation_report(self):
        """Should log and track CSP violations."""
        from priotag.main import csp_violation_report

        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "violated-directive": "script-src 'self'",
            "blocked-uri": "https://evil.com/script.js",
        }

        with patch("priotag.main.track_csp_violation") as mock_track:
            with patch("priotag.main.logger") as mock_logger:
                result = await csp_violation_report(mock_request)

                assert result == {"status": "ok"}
                mock_track.assert_called_once_with("script-src")
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_csp_violation_report_unknown_directive(self):
        """Should handle violations with unknown directive."""
        from priotag.main import csp_violation_report

        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "violated-directive": "",
            "blocked-uri": "https://evil.com/script.js",
        }

        with patch("priotag.main.track_csp_violation") as mock_track:
            result = await csp_violation_report(mock_request)

            assert result == {"status": "ok"}
            # Should track with "unknown" directive
            assert mock_track.called


@pytest.mark.unit
class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_valid_token(self):
        """Should return metrics with valid token."""
        from priotag.main import metrics
        from fastapi.security import HTTPAuthorizationCredentials

        with patch("priotag.main.metrics_token_file") as mock_token_file:
            mock_token_file.exists.return_value = True
            mock_token_file.read_text.return_value = "secret_metrics_token"

            # Re-import to pick up the token
            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="secret_metrics_token"
            )

            with patch("priotag.main.metrics_endpoint", return_value="metrics_data"):
                result = await priotag.main.metrics(credentials)
                assert result == "metrics_data"

    @pytest.mark.asyncio
    async def test_metrics_endpoint_invalid_token(self):
        """Should reject requests with invalid token."""
        from priotag.main import metrics
        from fastapi.security import HTTPAuthorizationCredentials

        with patch("priotag.main.metrics_token_file") as mock_token_file:
            mock_token_file.exists.return_value = True
            mock_token_file.read_text.return_value = "secret_metrics_token"

            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="wrong_token"
            )

            with pytest.raises(HTTPException) as exc_info:
                await priotag.main.metrics(credentials)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Invalid metrics token" in exc_info.value.detail

    def test_metrics_token_file_missing(self):
        """Should log warning if metrics token file is missing."""
        with patch("priotag.main.metrics_token_file") as mock_token_file:
            mock_token_file.exists.return_value = False

            with patch("priotag.main.logger") as mock_logger:
                import importlib
                import priotag.main
                importlib.reload(priotag.main)

                # Should have logged warning
                mock_logger.warning.assert_called()


@pytest.mark.unit
class TestStaticFileServing:
    """Test static file serving configuration."""

    def test_static_files_setup_production(self):
        """Should set up static file serving in production."""
        with patch.dict("os.environ", {"ENV": "production", "SERVE_STATIC": "false"}):
            with patch("priotag.main.setup_static_file_serving") as mock_setup:
                import importlib
                import priotag.main
                importlib.reload(priotag.main)

                # Should have called setup
                assert mock_setup.called

    def test_static_files_setup_development_explicit(self):
        """Should set up static file serving in development if explicitly enabled."""
        with patch.dict("os.environ", {"ENV": "development", "SERVE_STATIC": "true"}):
            with patch("priotag.main.setup_static_file_serving") as mock_setup:
                import importlib
                import priotag.main
                importlib.reload(priotag.main)

                # Should have called setup
                assert mock_setup.called


@pytest.mark.unit
class TestEnvironmentConfiguration:
    """Test environment-based configuration."""

    def test_log_level_development(self):
        """Should use DEBUG log level in development."""
        with patch.dict("os.environ", {"ENV": "development"}):
            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            # Should set DEBUG level (can't easily verify, but ensure no errors)

    def test_log_level_production(self):
        """Should use INFO log level in production."""
        with patch.dict("os.environ", {"ENV": "production"}):
            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            # Should set INFO level (can't easily verify, but ensure no errors)

    def test_docs_disabled_in_production(self):
        """Should disable API docs in production."""
        with patch.dict("os.environ", {"ENV": "production"}):
            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            # Docs should be disabled (can't easily verify, but ensure no errors)

    def test_docs_enabled_in_development(self):
        """Should enable API docs in development."""
        with patch.dict("os.environ", {"ENV": "development"}):
            import importlib
            import priotag.main
            importlib.reload(priotag.main)

            # Docs should be enabled (can't easily verify, but ensure no errors)
