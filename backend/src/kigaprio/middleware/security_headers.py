import base64
import hashlib
import logging
import re
from pathlib import Path

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, static_path: Path):
        super().__init__(app)
        self.static_path = static_path
        self.script_hashes: set[str] = set()

        self.relaxed_csp_routes = [
            "/api/docs",
        ]
        # Extract hashes at startup
        self._extract_hashes()

        # Build CSP header once
        self.csp_header = self._build_csp()
        self.relaxed_csp_header = self._build_relaxed_csp()
        logger.info(f"CSP initialized with {len(self.script_hashes)} script hashes")

        # Log all hashes for debugging
        for hash_val in sorted(self.script_hashes):
            logger.info(f"  Allowed script hash: {hash_val}")

    def _extract_inline_scripts(self, html_content: str) -> list[str]:
        """Extract inline script contents from HTML, preserving exact whitespace."""
        scripts = []

        # Match <script> tags without src attribute
        # This regex captures the content between <script> and </script>
        pattern = r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>"
        matches = re.finditer(pattern, html_content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            script_content = match.group(1)
            if script_content:  # Allow empty scripts too if present
                scripts.append(script_content)

        return scripts

    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash for content."""
        hash_digest = hashlib.sha256(content.encode("utf-8")).digest()
        hash_b64 = base64.b64encode(hash_digest).decode("utf-8")
        hash_str = f"'sha256-{hash_b64}'"

        return hash_str

    def _extract_hashes(self):
        """Extract and hash all inline scripts from static HTML files."""
        if not self.static_path.exists():
            logger.warning(f"Static path {self.static_path} does not exist")
            return

        # Find all HTML files in the static directory
        html_files = list(self.static_path.rglob("*.html"))

        if not html_files:
            logger.warning(f"No HTML files found in {self.static_path}")
            return

        logger.info(f"Processing {len(html_files)} HTML file(s) for CSP hashes")

        for html_file in html_files:
            try:
                with open(html_file, encoding="utf-8") as f:
                    html_content = f.read()

                # Extract and hash inline scripts
                inline_scripts = self._extract_inline_scripts(html_content)

                if inline_scripts:
                    logger.info(
                        f"Found {len(inline_scripts)} inline script(s) in {html_file.name}"
                    )

                for i, script in enumerate(inline_scripts):
                    hash_value = self._calculate_hash(script)
                    self.script_hashes.add(hash_value)

                    # Debug log
                    logger.debug(f"  Script {i + 1} hash: {hash_value}")
                    logger.debug(f"  Script {i + 1} length: {len(script)} bytes")
                    logger.debug(f"  Script {i + 1} preview: {repr(script[:80])}")

            except Exception as e:
                logger.error(f"Error processing {html_file}: {e}")

    def _build_csp(self) -> str:
        """Build the Content Security Policy header."""
        # Start with base directives
        script_src = "'self'"
        if self.script_hashes:
            script_src += " " + " ".join(sorted(self.script_hashes))

        # For styles - keep unsafe-inline for SvelteKit transitions
        style_src = "'self' 'unsafe-inline'"

        csp_parts = [
            "default-src 'self'",
            f"script-src {script_src}",
            f"style-src {style_src}",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",
            "upgrade-insecure-requests",
        ]

        return "; ".join(csp_parts)

    def _build_relaxed_csp(self) -> str:
        """Build relaxed CSP for API documentation (Swagger UI, ReDoc)."""
        csp_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Swagger needs eval
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "object-src 'none'",
        ]

        return "; ".join(csp_parts)

    def _should_use_relaxed_csp(self, path: str) -> bool:
        """Check if the request path should use relaxed CSP."""
        return any(path.startswith(route) for route in self.relaxed_csp_routes)

    async def dispatch(self, request: Request, call_next):
        # Process the request normally
        response = await call_next(request)
        path = request.url.path
        if self._should_use_relaxed_csp(path):
            logger.debug(f"Applied relaxed CSP for {path}")
            return response

        # Only add headers to HTML responses and API responses
        content_type = response.headers.get("content-type", "")

        if (
            "text/html" in content_type
            or "application/json" in content_type
            or not content_type
        ):
            # Content Security Policy
            response.headers["Content-Security-Policy"] = self.csp_header

            # Strict Transport Security
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

            # Permissions Policy
            response.headers["Permissions-Policy"] = (
                "accelerometer=(), ambient-light-sensor=(), autoplay=(), "
                "battery=(), camera=(), display-capture=(), document-domain=(), "
                "encrypted-media=(), fullscreen=(self), "
                "geolocation=(), gyroscope=(), microphone=(), "
                "payment=(), picture-in-picture=(), "
                "screen-wake-lock=(), usb=(), web-share=()"
            )

            # Other Security Headers
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        return response
