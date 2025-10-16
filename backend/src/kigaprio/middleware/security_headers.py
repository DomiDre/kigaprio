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
        self.style_hashes: set[str] = set()

        # Extract hashes at startup
        self._extract_hashes()

        # Build CSP header once
        self.csp_header = self._build_csp()
        logger.info(f"CSP initialized with {len(self.script_hashes)} script hashes")

    def _extract_inline_scripts(self, html_content: str) -> list[str]:
        """Extract inline script contents from HTML."""
        # Match <script> tags without src attribute
        pattern = r"<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>"
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        return [match.strip() for match in matches if match.strip()]

    def _extract_inline_styles(self, html_content: str) -> list[str]:
        """Extract inline style contents from HTML."""
        # Match <style> tags
        pattern = r"<style[^>]*>(.*?)</style>"
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        return [match.strip() for match in matches if match.strip()]

    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash for content."""
        hash_digest = hashlib.sha256(content.encode("utf-8")).digest()
        hash_b64 = base64.b64encode(hash_digest).decode("utf-8")
        return f"'sha256-{hash_b64}'"

    def _extract_hashes(self):
        """Extract and hash all inline scripts and styles from static HTML files."""
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
                for script in inline_scripts:
                    hash_value = self._calculate_hash(script)
                    self.script_hashes.add(hash_value)
                    logger.debug(
                        f"Found inline script in {html_file.name}: {hash_value}"
                    )

                # Extract and hash inline styles (optional, for stricter CSP)
                inline_styles = self._extract_inline_styles(html_content)
                for style in inline_styles:
                    hash_value = self._calculate_hash(style)
                    self.style_hashes.add(hash_value)
                    logger.debug(
                        f"Found inline style in {html_file.name}: {hash_value}"
                    )

            except Exception as e:
                logger.error(f"Error processing {html_file}: {e}")

    def _build_csp(self) -> str:
        """Build the Content Security Policy header."""
        # Start with base directives
        script_src = "'self'"
        if self.script_hashes:
            script_src += " " + " ".join(sorted(self.script_hashes))

        # For styles, you can choose between hashes or 'unsafe-inline'
        # Option 1: Use hashes (stricter)
        style_src = "'self'"
        if self.style_hashes:
            style_src += " " + " ".join(sorted(self.style_hashes))
        # Add unsafe-inline as fallback for SvelteKit transitions
        style_src += " 'unsafe-inline'"

        # Option 2: Just use unsafe-inline (simpler, still secure enough)
        # style_src = "'self' 'unsafe-inline'"

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

    async def dispatch(self, request: Request, call_next):
        # Process the request normally
        response = await call_next(request)

        # Only add headers to HTML responses and API responses
        # Skip for static assets like JS, CSS, images
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
                "encrypted-media=(), execution-while-not-rendered=(), "
                "execution-while-out-of-viewport=(), fullscreen=(self), "
                "geolocation=(), gyroscope=(), hid=(), idle-detection=(), "
                "magnetometer=(), microphone=(), midi=(), navigation-override=(), "
                "payment=(), picture-in-picture=(), publickey-credentials-get=(), "
                "screen-wake-lock=(), serial=(), sync-xhr=(), usb=(), "
                "web-share=(), xr-spatial-tracking=()"
            )

            # Other Security Headers
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        return response
