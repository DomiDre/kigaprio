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


def validate_path_component(component: str) -> str | None:
    """Validate a single path component and return sanitized version."""
    if not component or component == "." or component == "..":
        return None

    if "\x00" in component or "/" in component or "\\" in component:
        return None

    if component.startswith("."):
        return None

    allowed_chars = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    )
    if not all(c in allowed_chars for c in component):
        return None

    return component.lower()


def safe_join_path(base: Path, user_input: str) -> Path | None:
    """Safely join user input to base path by validating each component."""
    if not user_input:
        return base / "index.html"

    cleaned = user_input.strip().lstrip("/")
    if not cleaned:
        return base / "index.html"

    components = cleaned.split("/")

    validated_parts = []
    for component in components:
        validated = validate_path_component(component)
        if validated is None:
            logger.warning(f"Invalid path component: {component}")
            return None
        validated_parts.append(validated)

    result = base
    for part in validated_parts:
        result = result / part

    try:
        resolved = result.resolve()
        base_resolved = base.resolve()

        if not resolved.is_relative_to(base_resolved):
            logger.warning("Path traversal attempt detected")
            return None

        return resolved
    except (ValueError, RuntimeError, OSError) as e:
        logger.warning(f"Path resolution error: {e}")
        return None


def is_allowed_file(path: Path) -> bool:
    """Check if a file has an allowed extension for serving."""
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def validate_directory_safety(directory: Path, base: Path) -> bool:
    """Validate that a directory is safe to mount and doesn't escape base path."""
    try:
        resolved = directory.resolve()
        base_resolved = base.resolve()

        if not resolved.is_relative_to(base_resolved):
            logger.warning(f"Directory outside base path: {directory}")
            return False

        return True
    except (ValueError, RuntimeError, OSError) as e:
        logger.warning(f"Directory validation error for {directory}: {e}")
        return False


def find_file_to_serve(base_path: Path, validated_path: Path) -> Path | None:
    """Find the appropriate file to serve for a validated request path."""

    if validated_path.is_file():
        if is_allowed_file(validated_path):
            return validated_path
        else:
            logger.warning(f"Blocked serving disallowed file type: {validated_path}")
            return None

    if validated_path.is_dir():
        index_file = validated_path / "index.html"
        if index_file.is_file():
            try:
                index_resolved = index_file.resolve()
                base_resolved = base_path.resolve()
                if index_resolved.is_relative_to(base_resolved) and is_allowed_file(
                    index_file
                ):
                    return index_file
            except (ValueError, OSError):
                logger.warning(f"Index file validation failed: {index_file}")

    html_file = validated_path.parent / f"{validated_path.name}.html"
    try:
        if html_file.is_file():
            html_resolved = html_file.resolve()
            base_resolved = base_path.resolve()
            if html_resolved.is_relative_to(base_resolved) and is_allowed_file(
                html_file
            ):
                return html_file
    except (ValueError, OSError):
        pass

    root_index = base_path / "index.html"
    if root_index.is_file() and is_allowed_file(root_index):
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
            logger.info("⚠️  Static files not found at", static_path)
        return

    logger.info(f"🎯 Serving static files from {static_path}")

    static_root = static_path.resolve()

    if not any(static_path.iterdir()):
        logger.info("  ⚠️  Static directory exists but is empty")
        return

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

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Secure static file server with path traversal protection."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        validated_path = safe_join_path(static_root, full_path)

        if validated_path is None:
            raise HTTPException(status_code=404, detail="Not found")

        file_to_serve = find_file_to_serve(static_root, validated_path)

        if file_to_serve and file_to_serve.is_file():
            try:
                file_resolved = file_to_serve.resolve()
                base_resolved = static_root.resolve()

                if not file_resolved.is_relative_to(base_resolved):
                    logger.warning(f"TOCTOU validation failed for: {full_path}")
                    raise HTTPException(status_code=404, detail="Not found")

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

    _ = serve_spa
    logger.info("  ✓ Secure static file serving")
