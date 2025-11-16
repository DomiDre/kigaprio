"""
Tests for security headers middleware.

Tests cover:
- ScriptExtractor HTML parser
- SecurityHeadersMiddleware initialization and CSP generation
- Path validation and header injection
- Relaxed CSP for API docs
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from starlette.requests import Request

from priotag.middleware.security_headers import (
    ScriptExtractor,
    SecurityHeadersMiddleware,
)


@pytest.mark.unit
class TestScriptExtractor:
    """Test ScriptExtractor HTML parser."""

    def test_extract_inline_script(self):
        """Should extract inline script content."""
        html = "<html><script>alert('test');</script></html>"
        parser = ScriptExtractor()
        parser.feed(html)

        assert len(parser.scripts) == 1
        assert parser.scripts[0] == "alert('test');"

    def test_extract_multiple_inline_scripts(self):
        """Should extract multiple inline scripts."""
        html = """
        <html>
            <script>var a = 1;</script>
            <script>var b = 2;</script>
        </html>
        """
        parser = ScriptExtractor()
        parser.feed(html)

        assert len(parser.scripts) == 2
        assert "var a = 1;" in parser.scripts
        assert "var b = 2;" in parser.scripts

    def test_ignore_external_scripts(self):
        """Should ignore scripts with src attribute."""
        html = '<html><script src="app.js"></script></html>'
        parser = ScriptExtractor()
        parser.feed(html)

        assert len(parser.scripts) == 0

    def test_ignore_empty_scripts(self):
        """Should ignore empty script tags."""
        html = "<html><script></script><script>   </script></html>"
        parser = ScriptExtractor()
        parser.feed(html)

        assert len(parser.scripts) == 0

    def test_extract_script_with_whitespace(self):
        """Should handle scripts with whitespace correctly."""
        html = """
        <script>
            function test() {
                console.log('hello');
            }
        </script>
        """
        parser = ScriptExtractor()
        parser.feed(html)

        assert len(parser.scripts) == 1
        assert "function test()" in parser.scripts[0]

    def test_mixed_inline_and_external_scripts(self):
        """Should only extract inline scripts, not external ones."""
        html = """
        <html>
            <script src="external.js"></script>
            <script>var inline = true;</script>
            <script src="another.js"></script>
        </html>
        """
        parser = ScriptExtractor()
        parser.feed(html)

        assert len(parser.scripts) == 1
        assert parser.scripts[0] == "var inline = true;"


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    """Test SecurityHeadersMiddleware."""

    def test_init_creates_script_hashes(self):
        """Should create script hashes from static HTML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            html_file = static_path / "index.html"
            html_file.write_text(
                "<html><head><script>alert('test');</script></head></html>"
            )

            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            # Should have extracted and hashed the inline script
            assert len(middleware.script_hashes) > 0

    def test_calculate_hash_sha256(self):
        """Should calculate SHA-256 hash correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            content = "alert('test');"
            hash_value = middleware._calculate_hash(content)

            assert hash_value.startswith("'sha256-")
            assert hash_value.endswith("'")

    def test_calculate_hash_deterministic(self):
        """Should produce same hash for same content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            content = "console.log('hello');"
            hash1 = middleware._calculate_hash(content)
            hash2 = middleware._calculate_hash(content)

            assert hash1 == hash2

    def test_is_safe_file_path_within_static(self):
        """Should allow files within static directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            test_file = static_path / "test.html"
            test_file.touch()

            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            assert middleware._is_safe_file_path(test_file) is True

    def test_is_safe_file_path_outside_static(self):
        """Should reject files outside static directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir) / "static"
            static_path.mkdir()

            outside_file = Path(tmpdir) / "outside.html"

            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            assert middleware._is_safe_file_path(outside_file) is False

    def test_is_safe_file_path_traversal_attempt(self):
        """Should reject path traversal attempts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir) / "static"
            static_path.mkdir()

            # Create a path that tries to escape
            traversal_path = static_path / ".." / "secret.txt"

            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            # resolved path would be outside static
            assert middleware._is_safe_file_path(traversal_path) is False

    def test_extract_hashes_skips_large_files(self):
        """Should skip files larger than 10MB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)

            # Create a file reporting > 10MB size
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 11 * 1024 * 1024  # 11MB

                html_file = static_path / "large.html"
                html_file.write_text("<script>test</script>")

                app = FastAPI()
                # Should skip the large file
                middleware = SecurityHeadersMiddleware(app, static_path)

                # No scripts should be extracted from large file
                assert len(middleware.script_hashes) == 0

    def test_build_csp_includes_script_hashes(self):
        """Should include script hashes in CSP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            # Manually add a hash
            middleware.script_hashes.add("'sha256-test123'")
            csp = middleware._build_csp()

            assert "'sha256-test123'" in csp
            assert "script-src 'self'" in csp

    def test_build_csp_with_hsts(self):
        """Should include upgrade-insecure-requests when HSTS is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path, enable_hsts=True)

            csp = middleware.csp_header
            assert "upgrade-insecure-requests" in csp

    def test_build_csp_without_hsts(self):
        """Should not include upgrade-insecure-requests when HSTS is disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path, enable_hsts=False)

            csp = middleware.csp_header
            assert "upgrade-insecure-requests" not in csp

    def test_build_csp_with_report_uri(self):
        """Should include report-uri when configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(
                app, static_path, csp_report_uri="https://example.com/csp-report"
            )

            csp = middleware.csp_header
            assert "report-uri https://example.com/csp-report" in csp

    def test_build_relaxed_csp(self):
        """Should build relaxed CSP for API docs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            relaxed_csp = middleware._build_relaxed_csp()

            assert "'unsafe-inline'" in relaxed_csp
            assert "'unsafe-eval'" in relaxed_csp

    def test_should_use_relaxed_csp_for_docs(self):
        """Should use relaxed CSP for /api/docs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            assert middleware._should_use_relaxed_csp("/api/docs") is True
            assert middleware._should_use_relaxed_csp("/api/docs/") is True
            assert middleware._should_use_relaxed_csp("/api/redoc") is True

    def test_should_use_relaxed_csp_for_docs_subpaths(self):
        """Should use relaxed CSP for subpaths of /api/docs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            assert middleware._should_use_relaxed_csp("/api/docs/swagger.js") is True

    def test_should_not_use_relaxed_csp_for_regular_routes(self):
        """Should not use relaxed CSP for regular routes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            assert middleware._should_use_relaxed_csp("/api/v1/priorities") is False
            assert middleware._should_use_relaxed_csp("/") is False

    def test_validate_content_type_normal(self):
        """Should allow normal content types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            assert middleware._validate_content_type("text/html") is True
            assert middleware._validate_content_type("application/json") is True

    def test_validate_content_type_with_newlines(self):
        """Should reject content types with newlines (header injection)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            assert middleware._validate_content_type("text/html\nX-Evil: true") is False
            assert middleware._validate_content_type("text/html\r\n") is False

    def test_validate_content_type_empty(self):
        """Should allow empty content type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            assert middleware._validate_content_type("") is True
            assert middleware._validate_content_type(None) is True

    @pytest.mark.asyncio
    async def test_dispatch_adds_security_headers_to_html(self):
        """Should add security headers to HTML responses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            mock_request = Mock(spec=Request)
            mock_request.url.path = "/"

            mock_response = Response(content="<html></html>", media_type="text/html")

            async def call_next(_request):
                return mock_response

            result = await middleware.dispatch(mock_request, call_next)

            assert "Content-Security-Policy" in result.headers
            assert "X-Frame-Options" in result.headers
            assert "X-Content-Type-Options" in result.headers

    @pytest.mark.asyncio
    async def test_dispatch_adds_hsts_when_enabled(self):
        """Should add HSTS header when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path, enable_hsts=True)

            mock_request = Mock(spec=Request)
            mock_request.url.path = "/"

            mock_response = Response(content="<html></html>", media_type="text/html")

            async def call_next(_request):
                return mock_response

            result = await middleware.dispatch(mock_request, call_next)

            assert "Strict-Transport-Security" in result.headers

    @pytest.mark.asyncio
    async def test_dispatch_no_headers_for_invalid_content_type(self):
        """Should not add headers if content-type validation fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            mock_request = Mock(spec=Request)
            mock_request.url.path = "/"

            mock_response = Response()
            mock_response.headers["content-type"] = "text/html\nX-Evil: header"

            async def call_next(_request):
                return mock_response

            result = await middleware.dispatch(mock_request, call_next)

            # Should not add CSP due to invalid content-type
            assert "Content-Security-Policy" not in result.headers

    @pytest.mark.asyncio
    async def test_dispatch_uses_relaxed_csp_for_docs(self):
        """Should use relaxed CSP for API documentation routes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            app = FastAPI()
            middleware = SecurityHeadersMiddleware(app, static_path)

            mock_request = Mock(spec=Request)
            mock_request.url.path = "/api/docs"

            mock_response = Response(content="<html></html>", media_type="text/html")

            async def call_next(_request):
                return mock_response

            result = await middleware.dispatch(mock_request, call_next)

            # Should return early for relaxed CSP routes (no CSP header added)
            assert "Content-Security-Policy" not in result.headers
