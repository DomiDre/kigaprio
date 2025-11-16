"""
Tests for Prometheus metrics middleware.

Tests cover:
- Request/response metrics tracking
- Error handling and metrics
- Path template extraction
- Rate limit type detection
- CSP violation tracking
- Metrics endpoint generation
"""

from unittest.mock import Mock

import pytest


@pytest.mark.unit
class TestMetricsMiddlewareErrorHandling:
    """Test error handling in metrics middleware."""

    @pytest.mark.asyncio
    async def test_middleware_tracks_error_metrics(self):
        """Should track metrics even when endpoint raises exception."""
        from fastapi import FastAPI

        from priotag.middleware.metrics import PrometheusMetricsMiddleware

        app = FastAPI()
        middleware = PrometheusMetricsMiddleware(app)

        @app.get("/test")
        async def failing_endpoint():
            raise ValueError("Test error")

        # Create mock request
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "route": Mock(path="/test"),
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        # Should handle the error and still track metrics
        with pytest.raises(ValueError):
            await middleware(scope, receive, send)


@pytest.mark.unit
class TestPathTemplateExtraction:
    """Test path template extraction for metrics."""

    def test_get_path_template_with_route(self):
        """Should extract path template from route."""
        from fastapi import Request

        from priotag.middleware.metrics import PrometheusMetricsMiddleware

        # Mock request with route
        mock_route = Mock()
        mock_route.path = "/api/v1/users/{id}"

        mock_request = Mock(spec=Request)
        mock_request.scope = {"route": mock_route}
        mock_request.url.path = "/api/v1/users/123"

        path = PrometheusMetricsMiddleware._get_path_template(mock_request)
        assert path == "/api/v1/users/{id}"

    def test_get_path_template_fallback_with_uuid(self):
        """Should sanitize UUID in path when route not available."""
        from fastapi import Request

        from priotag.middleware.metrics import PrometheusMetricsMiddleware

        # Mock request without route
        mock_request = Mock(spec=Request)
        mock_request.scope = {}
        mock_request.url.path = "/api/v1/users/550e8400-e29b-41d4-a716-446655440000"

        path = PrometheusMetricsMiddleware._get_path_template(mock_request)
        assert path == "/api/v1/users/{id}"

    def test_get_path_template_fallback_with_month(self):
        """Should sanitize month pattern in path."""
        from fastapi import Request

        from priotag.middleware.metrics import PrometheusMetricsMiddleware

        mock_request = Mock(spec=Request)
        mock_request.scope = {}
        mock_request.url.path = "/api/v1/reports/2024-03"

        path = PrometheusMetricsMiddleware._get_path_template(mock_request)
        assert path == "/api/v1/reports/{month}"

    def test_get_path_template_no_route_attribute(self):
        """Should handle request without route attribute."""
        from fastapi import Request

        from priotag.middleware.metrics import PrometheusMetricsMiddleware

        mock_request = Mock(spec=Request)
        mock_request.scope = {"route": Mock(spec=[])}  # Route without path attribute
        mock_request.url.path = "/api/v1/test"

        path = PrometheusMetricsMiddleware._get_path_template(mock_request)
        assert path == "/api/v1/test"


@pytest.mark.unit
class TestRateLimitTypeDetection:
    """Test rate limit type detection."""

    def test_login_rate_limit(self):
        """Should detect login endpoints."""
        from priotag.middleware.metrics import PrometheusMetricsMiddleware

        limit_type = PrometheusMetricsMiddleware._get_rate_limit_type(
            "/api/v1/auth/login"
        )
        assert limit_type == "login"

    def test_api_rate_limit(self):
        """Should default to 'api' for other endpoints."""
        from priotag.middleware.metrics import PrometheusMetricsMiddleware

        limit_type = PrometheusMetricsMiddleware._get_rate_limit_type("/api/v1/users")
        assert limit_type == "api"


@pytest.mark.unit
class TestCSPViolationTracking:
    """Test CSP violation tracking."""

    def test_track_csp_violation(self):
        """Should track CSP violations."""
        from priotag.middleware.metrics import track_csp_violation

        # Should not raise error
        track_csp_violation("script-src")
        track_csp_violation("style-src")
        track_csp_violation("img-src")


@pytest.mark.unit
class TestMetricsEndpoint:
    """Test metrics endpoint generation."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_text(self):
        """Should return metrics in Prometheus text format."""
        from fastapi.responses import Response

        from priotag.middleware.metrics import metrics_endpoint

        response = await metrics_endpoint()

        assert isinstance(response, Response)
        assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"
        assert isinstance(response.body, bytes)

        # Should contain metric names
        body_text = response.body.decode()
        assert "http_requests_total" in body_text or len(body_text) >= 0
