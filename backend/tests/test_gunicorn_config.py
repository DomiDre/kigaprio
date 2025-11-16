"""
Tests for gunicorn configuration.

Tests cover:
- HealthCheckFilter logging filter
- on_starting callback
"""

import logging
from unittest.mock import Mock, patch

import pytest

from priotag.gunicorn_config import HealthCheckFilter, on_starting


@pytest.mark.unit
class TestHealthCheckFilter:
    """Test HealthCheckFilter for gunicorn access logs."""

    def test_filter_health_check_request(self):
        """Should filter out health check requests."""
        filter_obj = HealthCheckFilter()
        record = Mock()
        record.args = ("/api/v1/health",)
        record.getMessage = Mock(return_value="GET /api/v1/health 200")

        result = filter_obj.filter(record)
        assert result is False

    def test_filter_allows_other_requests(self):
        """Should allow non-health check requests."""
        filter_obj = HealthCheckFilter()
        record = Mock()
        record.args = ("/api/v1/priorities",)
        record.getMessage = Mock(return_value="GET /api/v1/priorities 200")

        result = filter_obj.filter(record)
        assert result is True

    def test_filter_no_args(self):
        """Should allow records without args."""
        filter_obj = HealthCheckFilter()
        record = Mock()
        record.args = None

        result = filter_obj.filter(record)
        assert result is True

    def test_filter_empty_args(self):
        """Should allow records with empty args."""
        filter_obj = HealthCheckFilter()
        record = Mock()
        record.args = ()

        result = filter_obj.filter(record)
        assert result is True

    def test_filter_health_check_in_message(self):
        """Should filter messages containing health check path."""
        filter_obj = HealthCheckFilter()
        record = Mock()
        record.args = ("some", "args")
        record.getMessage = Mock(
            return_value="192.168.1.1 - GET /api/v1/health HTTP/1.1 200"
        )

        result = filter_obj.filter(record)
        assert result is False

    def test_filter_health_check_not_in_message(self):
        """Should allow messages not containing health check path."""
        filter_obj = HealthCheckFilter()
        record = Mock()
        record.args = ("some", "args")
        record.getMessage = Mock(
            return_value="192.168.1.1 - GET /api/v1/priorities HTTP/1.1 200"
        )

        result = filter_obj.filter(record)
        assert result is True


@pytest.mark.unit
class TestOnStarting:
    """Test on_starting configuration callback."""

    @patch("logging.getLogger")
    def test_on_starting_adds_filter_to_gunicorn_logger(self, mock_get_logger):
        """Should add HealthCheckFilter to gunicorn.access logger."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_server = Mock()

        on_starting(mock_server)

        # Should have been called twice (gunicorn.access and uvicorn.access)
        assert mock_get_logger.call_count == 2
        mock_get_logger.assert_any_call("gunicorn.access")
        mock_get_logger.assert_any_call("uvicorn.access")

        # Should have added filter twice (once for each logger)
        assert mock_logger.addFilter.call_count == 2
        # Verify filter is HealthCheckFilter instance
        filter_arg = mock_logger.addFilter.call_args_list[0][0][0]
        assert isinstance(filter_arg, HealthCheckFilter)

    @patch("logging.getLogger")
    def test_on_starting_adds_filter_to_uvicorn_logger(self, mock_get_logger):
        """Should add HealthCheckFilter to uvicorn.access logger."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_server = Mock()

        on_starting(mock_server)

        # Verify uvicorn logger was accessed
        mock_get_logger.assert_any_call("uvicorn.access")
        # Both loggers should have filter added
        assert mock_logger.addFilter.call_count == 2
