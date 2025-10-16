"""
Secure static file serving utilities for FastAPI.

This module provides path validation and file serving logic with protection against
path traversal attacks, symlink attacks, and other file system vulnerabilities.
"""

import logging
import unicodedata
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

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

# Maximum file size to serve (10MB default)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Maximum path depth to prevent deeply nested paths
MAX_PATH_DEPTH = 10


def normalize_unicode(text: str) -> str:
    """Normalize unicode to prevent homograph and normalization attacks."""
    # Use NFKC normalization to handle various unicode representations
    return unicodedata.normalize("NFKC", text)


def validate_path_component(component: str) -> str | None:
    """Validate a single path component and return sanitized version."""
    if not component or component == "." or component == "..":
        return None

    # Normalize unicode first to prevent bypass attempts
    component = normalize_unicode(component)

    # Check for null bytes and path separators (including URL-encoded versions)
    forbidden_chars = ["\x00", "/", "\\", "%00", "%2f", "%2F", "%5c", "%5C"]
    for char in forbidden_chars:
        if char.lower() in component.lower():
            return None

    # Block hidden files and files with suspicious patterns
    if component.startswith(".") or component.startswith("~"):
        return None

    # Prevent Windows reserved names
    windows_reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
    }
    if component.lower().split(".")[0] in windows_reserved:
        return None

    # Strict character whitelist
    allowed_chars = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    )
    if not all(c in allowed_chars for c in component):
        return None

    # Prevent multiple consecutive dots
    if ".." in component:
        return None

    return component.lower()


def safe_join_path(base: Path, user_input: str) -> Path | None:
    """Safely join user input to base path by validating each component."""
    if not user_input:
        return base / "index.html"

    # Normalize unicode in the entire path
    user_input = normalize_unicode(user_input)

    cleaned = user_input.strip().lstrip("/")
    if not cleaned:
        return base / "index.html"

    components = cleaned.split("/")

    # Check path depth
    if len(components) > MAX_PATH_DEPTH:
        logger.warning(f"Path depth exceeds maximum: {len(components)}")
        return None

    validated_parts = []
    for component in components:
        validated = validate_path_component(component)
        if validated is None:
            logger.warning(f"Invalid path component rejected: {component[:50]}")
            return None
        validated_parts.append(validated)

    result = base
    for part in validated_parts:
        result = result / part

    try:
        # Check if path exists before resolving to avoid information leakage
        resolved = result.resolve(strict=False)
        base_resolved = base.resolve()

        # Verify the resolved path is within base directory
        if not resolved.is_relative_to(base_resolved):
            logger.warning("Path traversal attempt detected")
            return None

        # Additional check: ensure no component in the real path contains ".."
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            logger.warning("Path validation failed during relative_to check")
            return None

        return resolved
    except (ValueError, RuntimeError, OSError) as e:
        logger.warning(f"Path resolution error: {type(e).__name__}")
        return None


def is_safe_symlink(path: Path, base: Path) -> bool:
    """Check if a symlink is safe (points within the allowed directory)."""
    if not path.is_symlink():
        return True

    try:
        # Check if symlink target is within base directory
        target = path.resolve()
        base_resolved = base.resolve()
        return target.is_relative_to(base_resolved)
    except (ValueError, RuntimeError, OSError):
        return False


def is_allowed_file(path: Path) -> bool:
    """Check if a file has an allowed extension for serving."""
    suffix = path.suffix.lower()

    # Double extension check (e.g., file.php.txt)
    parts = path.name.lower().split(".")
    if len(parts) > 2:
        # Check all extensions, not just the last one
        for i in range(1, len(parts)):
            ext = "." + parts[i]
            if ext not in ALLOWED_EXTENSIONS and ext in {
                ".php",
                ".py",
                ".sh",
                ".exe",
                ".bat",
                ".cmd",
            }:
                logger.warning(
                    f"Blocked file with suspicious double extension: {path.name}"
                )
                return False

    return suffix in ALLOWED_EXTENSIONS


def validate_file_size(path: Path) -> bool:
    """Check if file size is within allowed limits."""
    try:
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            logger.warning(f"File too large: {path} ({size} bytes)")
            return False
        return True
    except OSError:
        return False


def validate_directory_safety(directory: Path, base: Path) -> bool:
    """Validate that a directory is safe to mount and doesn't escape base path."""
    try:
        resolved = directory.resolve()
        base_resolved = base.resolve()

        if not resolved.is_relative_to(base_resolved):
            logger.warning(f"Directory outside base path: {directory}")
            return False

        # Check for symlink safety
        if not is_safe_symlink(directory, base):
            logger.warning(f"Unsafe symlink detected: {directory}")
            return False

        return True
    except (ValueError, RuntimeError, OSError) as e:
        logger.warning(
            f"Directory validation error for {directory}: {type(e).__name__}"
        )
        return False


def find_file_to_serve(base_path: Path, validated_path: Path) -> Path | None:
    """Find the appropriate file to serve for a validated request path."""

    # Check if it's a regular file (not a symlink to a directory or device)
    if validated_path.is_file():
        # Verify symlink safety
        if not is_safe_symlink(validated_path, base_path):
            logger.warning(f"Blocked serving unsafe symlink: {validated_path}")
            return None

        if is_allowed_file(validated_path) and validate_file_size(validated_path):
            return validated_path
        else:
            logger.warning(
                f"Blocked serving disallowed or oversized file: {validated_path.name}"
            )
            return None

    # Directory handling
    if validated_path.is_dir():
        index_file = validated_path / "index.html"
        if index_file.is_file():
            try:
                index_resolved = index_file.resolve()
                base_resolved = base_path.resolve()
                if (
                    index_resolved.is_relative_to(base_resolved)
                    and is_allowed_file(index_file)
                    and is_safe_symlink(index_file, base_path)
                    and validate_file_size(index_file)
                ):
                    return index_file
            except (ValueError, OSError):
                logger.warning(f"Index file validation failed: {index_file.name}")

    # Try .html extension
    html_file = validated_path.parent / f"{validated_path.name}.html"
    try:
        if html_file.is_file():
            html_resolved = html_file.resolve()
            base_resolved = base_path.resolve()
            if (
                html_resolved.is_relative_to(base_resolved)
                and is_allowed_file(html_file)
                and is_safe_symlink(html_file, base_path)
                and validate_file_size(html_file)
            ):
                return html_file
    except (ValueError, OSError):
        pass

    # Fallback to root index
    root_index = base_path / "index.html"
    if (
        root_index.is_file()
        and is_allowed_file(root_index)
        and is_safe_symlink(root_index, base_path)
        and validate_file_size(root_index)
    ):
        return root_index

    return None


def setup_static_file_serving(
    app: FastAPI, static_path: Path, env: str, serve_static: bool
) -> None:
    """Configure static file serving for the FastAPI application."""
    should_serve = (env == "production" or serve_static) and static_path.exists()

    if not should_serve:
        if env == "development" and not serve_static:
            logger.info(
                "🚀 Development mode: Use Vite dev server at http://localhost:5173"
            )
            logger.info("   API available at http://localhost:8000/api/docs")
        else:
            logger.info(f"⚠️  Static files not found at {static_path}")
        return

    logger.info(f"🎯 Serving static files from {static_path}")

    try:
        static_root = static_path.resolve()
    except (ValueError, OSError) as e:
        logger.error(f"Failed to resolve static path: {e}")
        return

    if not any(static_path.iterdir()):
        logger.info("  ⚠️  Static directory exists but is empty")
        return

    # Mount _app directory
    app_dir = static_path / "_app"
    if app_dir.exists() and validate_directory_safety(app_dir, static_root):
        app.mount(
            "/_app",
            StaticFiles(directory=app_dir, check_dir=True, follow_symlink=False),
            name="static_app",
        )
        logger.info("  ✓ Mounted /_app directory")
    elif app_dir.exists():
        logger.error(f"Unsafe _app directory detected, not mounting: {app_dir}")

    # Mount assets directory
    assets_dir = static_path / "assets"
    if assets_dir.exists() and validate_directory_safety(assets_dir, static_root):
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir, check_dir=True, follow_symlink=False),
            name="assets",
        )
        logger.info("  ✓ Mounted /assets directory")
    elif assets_dir.exists():
        logger.error(f"Unsafe assets directory detected, not mounting: {assets_dir}")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        """Secure static file server with path traversal protection."""
        # Block API paths early
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Log suspicious patterns (but don't expose in error message)
        suspicious_patterns = ["../", "..\\", "%2e%2e", "~", "\x00"]
        if any(pattern in full_path.lower() for pattern in suspicious_patterns):
            logger.warning(
                f"Suspicious path pattern from {request.client.host if request.client else 'unknown'}: blocked"
            )
            raise HTTPException(status_code=404, detail="Not found")

        # Validate and sanitize the path
        validated_path = safe_join_path(static_root, full_path)

        if validated_path is None:
            raise HTTPException(status_code=404, detail="Not found")

        # Find appropriate file
        file_to_serve = find_file_to_serve(static_root, validated_path)

        if file_to_serve and file_to_serve.is_file():
            try:
                # Final TOCTOU validation
                file_resolved = file_to_serve.resolve()
                base_resolved = static_root.resolve()

                if not file_resolved.is_relative_to(base_resolved):
                    logger.warning(
                        "TOCTOU validation failed - potential race condition"
                    )
                    raise HTTPException(status_code=404, detail="Not found")

                if not is_allowed_file(file_to_serve):
                    logger.warning("Attempted to serve disallowed file type")
                    raise HTTPException(status_code=404, detail="Not found")

                if not is_safe_symlink(file_to_serve, static_root):
                    logger.warning("Unsafe symlink detected at serve time")
                    raise HTTPException(status_code=404, detail="Not found")

                if not validate_file_size(file_to_serve):
                    raise HTTPException(status_code=404, detail="Not found")

                # Use file descriptor for better TOCTOU protection
                return FileResponse(file_to_serve)

            except (ValueError, OSError, PermissionError) as e:
                logger.warning(f"Error during file serving: {type(e).__name__}")
                raise HTTPException(status_code=404, detail="Not found") from e

        raise HTTPException(status_code=404, detail="Not found")

    _ = serve_spa
    logger.info("  ✓ Secure static file serving enabled")
