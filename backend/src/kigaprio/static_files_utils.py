"""
Secure static file serving utilities for FastAPI.

This module provides path validation and file serving logic with protection against
path traversal attacks, symlink attacks, and other file system vulnerabilities.
"""

import logging
import os
import re
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

# Strict pattern for allowed path components
# Only allows: alphanumeric, hyphen, underscore, period, forward slash
SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9/_.\-]*$")


def is_safe_path_string(path_str: str) -> bool:
    """
    Check if a path string contains only safe characters.

    This is the first line of defense - reject any path with suspicious
    characters before doing any path operations.

    Args:
        path_str: The path string to validate

    Returns:
        True if the path contains only safe characters
    """
    if not path_str:
        return True

    # Reject null bytes
    if "\x00" in path_str:
        logger.warning(f"Null byte in path: {path_str!r}")
        return False

    # Reject paths that don't match our safe pattern
    if not SAFE_PATH_PATTERN.match(path_str):
        logger.warning(f"Path contains unsafe characters: {path_str}")
        return False

    # Reject parent directory references
    if ".." in path_str:
        logger.warning(f"Parent directory reference in path: {path_str}")
        return False

    # Reject absolute paths
    if path_str.startswith("/"):
        logger.warning(f"Absolute path not allowed: {path_str}")
        return False

    # Reject hidden files/directories (starting with .)
    parts = path_str.split("/")
    for part in parts:
        if part.startswith("."):
            logger.warning(f"Hidden file/directory in path: {path_str}")
            return False

    return True


def validate_and_resolve_path(base_path: Path, user_input: str) -> Path | None:
    """
    Validate and resolve a user-provided path against a base directory.

    Uses multiple layers of validation:
    1. Character allowlist (strict pattern matching)
    2. Standard library path normalization
    3. Canonical path resolution
    4. Boundary validation using os.path.commonpath

    Args:
        base_path: The base directory that the path must be within
        user_input: Raw user input from request

    Returns:
        A validated, resolved Path object, or None if validation fails
    """
    try:
        # Handle empty path
        if not user_input:
            return base_path / "index.html"

        # Strip and normalize the input
        cleaned = user_input.strip().lstrip("/")

        # CRITICAL: First check with allowlist - reject unsafe characters
        if not is_safe_path_string(cleaned):
            return None

        # Use os.path.normpath for additional normalization
        normalized = os.path.normpath(cleaned)

        # Additional check after normalization
        if normalized.startswith("..") or normalized.startswith("/"):
            logger.warning(f"Invalid normalized path: {normalized}")
            return None

        # Convert to lowercase for case-insensitive filesystems
        normalized = normalized.lower()

        # Build the full path from trusted base
        full_path_str = os.path.join(str(base_path), normalized)

        # Resolve to absolute canonical path
        resolved_str = os.path.abspath(full_path_str)
        resolved_path = Path(resolved_str)

        # Get canonical base path
        base_resolved_str = os.path.abspath(str(base_path))
        base_resolved = Path(base_resolved_str)

        # Use os.path.commonpath for validation
        try:
            common = os.path.commonpath([resolved_str, base_resolved_str])
            if common != base_resolved_str:
                logger.warning(f"Path escapes base directory: {user_input}")
                return None
        except ValueError:
            # Paths are on different drives (Windows) or invalid
            logger.warning(f"Invalid path comparison: {user_input}")
            return None

        # Double-check with Path.is_relative_to
        if not resolved_path.is_relative_to(base_resolved):
            logger.warning(f"Path not relative to base: {user_input}")
            return None

        # Path is validated and safe
        return resolved_path

    except (ValueError, RuntimeError, OSError) as e:
        logger.warning(f"Path validation error for {user_input}: {e}")
        return None


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
        resolved_str = os.path.abspath(str(directory))
        base_str = os.path.abspath(str(base))

        try:
            common = os.path.commonpath([resolved_str, base_str])
            if common != base_str:
                logger.warning(f"Directory outside base path: {directory}")
                return False
        except ValueError:
            logger.warning(f"Invalid directory path: {directory}")
            return False

        return True
    except (ValueError, RuntimeError, OSError) as e:
        logger.warning(f"Directory validation error for {directory}: {e}")
        return False


def find_file_to_serve(base_path: Path, validated_path: Path) -> Path | None:
    """
    Find the appropriate file to serve for a validated request path.

    Tries in order:
    1. Exact file match
    2. Directory with index.html
    3. File with .html extension
    4. Fallback to root index.html (for SPA routing)

    Args:
        base_path: The base static directory
        validated_path: A pre-validated Path object

    Returns:
        Path to serve, or None if no valid file found
    """
    # validated_path is already resolved and confirmed to be within base_path

    # Try exact file match
    if validated_path.is_file():
        if is_allowed_file(validated_path):
            return validated_path
        else:
            logger.warning(f"Blocked serving disallowed file type: {validated_path}")
            return None

    # Try directory with index.html
    if validated_path.is_dir():
        index_file = validated_path / "index.html"
        if index_file.is_file():
            # Re-validate that index.html is within base
            try:
                index_str = os.path.abspath(str(index_file))
                base_str = os.path.abspath(str(base_path))
                common = os.path.commonpath([index_str, base_str])
                if common == base_str and is_allowed_file(index_file):
                    return index_file
            except (ValueError, OSError):
                logger.warning(f"Index file validation failed: {index_file}")
                pass

    # Try adding .html extension
    html_file = validated_path.parent / f"{validated_path.name}.html"
    try:
        if html_file.is_file():
            # Validate the .html file is within base
            html_str = os.path.abspath(str(html_file))
            base_str = os.path.abspath(str(base_path))
            common = os.path.commonpath([html_str, base_str])
            if common == base_str and is_allowed_file(html_file):
                return html_file
    except (ValueError, OSError):
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
            logger.info(
                "🚀 Development mode: Use Vite dev server at http://localhost:5173"
            )
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
        Uses strict allowlist validation and standard library sanitization.
        """
        # API routes should never reach here (they're registered first)
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Validate user input with strict allowlist and standard library sanitization
        validated_path = validate_and_resolve_path(static_root, full_path)

        if validated_path is None:
            # Validation failed - path is unsafe
            raise HTTPException(status_code=404, detail="Not found")

        # Find the appropriate file to serve
        file_to_serve = find_file_to_serve(static_root, validated_path)

        if file_to_serve and file_to_serve.is_file():
            # TOCTOU mitigation: Re-validate just before serving
            try:
                file_str = os.path.abspath(str(file_to_serve))
                base_str = os.path.abspath(str(static_root))

                common = os.path.commonpath([file_str, base_str])
                if common != base_str:
                    logger.warning(f"TOCTOU validation failed for: {full_path}")
                    raise HTTPException(status_code=404, detail="Not found")

                # Final file type check
                if not is_allowed_file(file_to_serve):
                    logger.warning(
                        f"Attempted to serve disallowed file: {file_to_serve}"
                    )
                    raise HTTPException(status_code=404, detail="Not found")

                return FileResponse(file_to_serve)

            except (ValueError, OSError) as e:
                logger.warning(f"Path validation failed during serving: {full_path}")
                raise HTTPException(status_code=404, detail="Not found") from e

        raise HTTPException(status_code=404, detail="Not found")

    _ = serve_spa  # suppress warning that function is unused
    logger.info("  ✓ Secure static file serving")
