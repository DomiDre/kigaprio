"""
Secure static file serving utilities for FastAPI.

This module provides path validation and file serving logic with protection against
path traversal attacks, symlink attacks, and other file system vulnerabilities.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Configure logging for security events
logger = logging.getLogger(__name__)

# Whitelist of allowed file extensions for static serving
ALLOWED_EXTENSIONS = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".woff",
    ".woff2",
    ".ttf",
    ".ico",
    ".webp",
    ".map",
    ".txt",
    ".xml",
    ".pdf",
    ".webm",
    ".mp4",
    ".avif",
}


def is_allowed_file(path: Path) -> bool:
    """
    Check if a file has an allowed extension for serving.

    Prevents serving sensitive files like .env, .git, database files, etc.

    Args:
        path: Path to check

    Returns:
        True if the file extension is allowed
    """
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def is_safe_path(base_path: Path, requested_path: str) -> tuple[bool, Path | None]:
    """
    Validate that a requested path is safe and within the base directory.

    This function prevents path traversal attacks by:
    1. Resolving the full path (canonicalizes symlinks, .., etc.)
    2. Verifying the resolved path is within the base directory
    3. Normalizing case to prevent case-sensitivity bypasses

    Args:
        base_path: The base directory that files must be within
        requested_path: The user-requested path to validate

    Returns:
        Tuple of (is_safe, resolved_path)
        - is_safe: True if the path is safe to use
        - resolved_path: The resolved Path object, or None if unsafe

    Examples:
        >>> base = Path("/app/static")
        >>> is_safe_path(base, "index.html")
        (True, Path("/app/static/index.html"))
        >>> is_safe_path(base, "../../etc/passwd")
        (False, None)
    """
    try:
        # Handle empty path (root request)
        if not requested_path:
            return True, base_path / "index.html"

        # Remove any leading slashes and normalize case
        # Case normalization prevents bypasses on case-insensitive filesystems
        clean_path = requested_path.lstrip("/").strip().lower()

        # Reject paths with null bytes (potential injection attack)
        if "\x00" in clean_path:
            logger.warning(f"Null byte injection attempt: {requested_path!r}")
            return False, None

        # Reject absolute paths after cleaning
        candidate_path = Path(clean_path)
        if candidate_path.is_absolute():
            logger.warning(f"Absolute path attempt: {requested_path}")
            return False, None

        # Build and resolve the full path (resolves symlinks, .., etc)
        full_path = (base_path / candidate_path).resolve()

        # CRITICAL: Verify the resolved path is within base_path
        # This prevents path traversal attacks like ../../etc/passwd
        base_real = base_path.resolve()

        if not full_path.is_relative_to(base_real):
            logger.warning(f"Path traversal attempt: {requested_path} -> {full_path}")
            return False, None

        return True, full_path

    except (ValueError, RuntimeError, OSError) as e:
        # ValueError: path is not relative to base_path (path traversal attempt)
        # RuntimeError: symlink loop or other path resolution issues
        # OSError: invalid path, permission issues, etc
        logger.warning(f"Path validation error for {requested_path}: {e}")
        return False, None


def validate_directory_safety(directory: Path, base: Path) -> bool:
    """
    Validate that a directory is safe to mount and doesn't escape base path.

    Args:
        directory: The directory to validate
        base: The base path that directory must be within

    Returns:
        True if the directory is safe to use
    """
    try:
        resolved = directory.resolve()
        base_resolved = base.resolve()

        # Check that resolved directory is within base
        if not resolved.is_relative_to(base_resolved):
            logger.warning(f"Directory outside base path: {directory}")
            return False

        return True
    except (ValueError, RuntimeError, OSError) as e:
        logger.warning(f"Directory validation error for {directory}: {e}")
        return False


def find_file_to_serve(base_path: Path, requested_path: str) -> Path | None:
    """
    Find the appropriate file to serve for a given request.

    Tries in order:
    1. Exact file match
    2. Directory with index.html
    3. File with .html extension
    4. Fallback to root index.html (for SPA routing)

    All paths are validated for security before being returned.

    Args:
        base_path: The base static directory
        requested_path: The requested path (will be cleaned and validated)

    Returns:
        Path to serve, or None if no valid file found

    Examples:
        >>> base = Path("/app/static")
        >>> find_file_to_serve(base, "about")
        Path("/app/static/about.html")  # if about.html exists
        >>> find_file_to_serve(base, "../../etc/passwd")
        None  # unsafe path rejected
    """
    is_safe, resolved_path = is_safe_path(base_path, requested_path)

    if not is_safe or resolved_path is None:
        return None

    # Try exact file match
    if resolved_path.is_file():
        if is_allowed_file(resolved_path):
            return resolved_path
        else:
            logger.warning(f"Blocked serving disallowed file type: {resolved_path}")
            return None

    # Try directory with index.html
    if resolved_path.is_dir():
        index_file = resolved_path / "index.html"
        if index_file.is_file():
            # Verify index.html is still within base_path
            try:
                relative_index = str(index_file.relative_to(base_path))
                is_safe_idx, validated_index = is_safe_path(base_path, relative_index)
                if is_safe_idx and validated_index and is_allowed_file(validated_index):
                    return validated_index
            except ValueError:
                logger.warning(f"Index file validation failed: {index_file}")
                pass

    # Try adding .html extension (with proper exception handling)
    html_file = resolved_path.parent / f"{resolved_path.name}.html"
    try:
        # Only validate if html_file can be made relative to base_path
        relative_html = str(html_file.relative_to(base_path))
        is_safe_html, resolved_html_file = is_safe_path(base_path, relative_html)

        if (
            is_safe_html
            and resolved_html_file is not None
            and resolved_html_file.is_file()
        ):
            if is_allowed_file(resolved_html_file):
                return resolved_html_file
    except ValueError:
        # html_file is outside base_path, skip this attempt
        pass

    # Fallback to root index.html for SPA routing
    root_index = base_path / "index.html"
    if root_index.is_file() and is_allowed_file(root_index):
        return root_index

    return None


def setup_static_file_serving(
    app: FastAPI, static_path: Path, env: str, serve_static: bool
) -> None:
    """
    Configure static file serving for the FastAPI application.

    Sets up:
    - StaticFiles middleware for _app and assets directories (with validation)
    - Catch-all route for SPA routing with security validation
    - Security headers for all static responses

    Args:
        app: The FastAPI application instance
        static_path: Path to the static files directory
        env: Environment (development/production)
        serve_static: Whether to serve static files
    """
    should_serve = (env == "production" or serve_static) and static_path.exists()

    if not should_serve:
        if env == "development" and not serve_static:
            logger.info("🚀 Development mode: Use Vite dev server at http://localhost:5173")
            logger.info("   API available at http://localhost:8000/api/docs")
        else:
            logger.info("⚠️  Static files not found at", static_path)
        return

    logger.info(f"🎯 Serving static files from {static_path}")

    # Resolve static path once for security checks
    static_root = static_path.resolve()

    # Check if static files exist
    if not any(static_path.iterdir()):
        logger.info("  ⚠️  Static directory exists but is empty")
        return

    # Mount SvelteKit app directories with StaticFiles (with security validation)
    app_dir = static_path / "_app"
    if app_dir.exists() and validate_directory_safety(app_dir, static_root):
        app.mount(
            "/_app",
            StaticFiles(directory=app_dir, check_dir=True),
            name="static_app",
        )
        logger.info("  ✓ Mounted /_app directory")
    elif app_dir.exists():
        logger.error(f"Unsafe _app directory detected, not mounting: {app_dir}")
        logger.info("  ⚠️  _app directory failed security validation")

    assets_dir = static_path / "assets"
    if assets_dir.exists() and validate_directory_safety(assets_dir, static_root):
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir, check_dir=True),
            name="assets",
        )
        logger.info("  ✓ Mounted /assets directory")
    elif assets_dir.exists():
        logger.error(f"Unsafe assets directory detected, not mounting: {assets_dir}")
        logger.info("  ⚠️  assets directory failed security validation")

    # Catch-all route for SvelteKit client-side routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """
        Secure static file server with path traversal protection.

        Serves static files for SPA routing while preventing security vulnerabilities.
        Includes TOCTOU mitigation and security headers.
        """
        # API routes should never reach here (they're registered first)
        # but double-check as defense in depth
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Find and serve the appropriate file
        file_to_serve = find_file_to_serve(static_root, full_path)

        if file_to_serve and file_to_serve.is_file():
            # TOCTOU mitigation: Re-validate the path just before serving
            try:
                relative_path = str(file_to_serve.relative_to(static_root))
                is_safe, revalidated_path = is_safe_path(static_root, relative_path)

                if not is_safe or revalidated_path != file_to_serve:
                    logger.warning(f"TOCTOU validation failed for: {full_path}")
                    raise HTTPException(status_code=404, detail="Not found")

                # Final file type check
                if not is_allowed_file(file_to_serve):
                    logger.warning(
                        f"Attempted to serve disallowed file: {file_to_serve}"
                    )
                    raise HTTPException(status_code=404, detail="Not found")

                # Security headers to prevent common attacks
                headers = {
                    "X-Content-Type-Options": "nosniff",  # Prevent MIME sniffing
                    "X-Frame-Options": "DENY",  # Prevent clickjacking
                    "Content-Security-Policy": "default-src 'self'",  # Basic CSP
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                }

                return FileResponse(file_to_serve, headers=headers)

            except ValueError as e:
                logger.warning(f"Path validation failed during serving: {full_path}")
                raise HTTPException(status_code=404, detail="Not found") from e

        raise HTTPException(status_code=404, detail="Not found")

    _ = serve_spa  # suppress warning that function is unused
    logger.info("  ✓ Secure static file serving")
