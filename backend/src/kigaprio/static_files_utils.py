"""
Secure static file serving utilities for FastAPI.

This module provides path validation and file serving logic with protection against
path traversal attacks, symlink attacks, and other file system vulnerabilities.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def is_safe_path(base_path: Path, requested_path: str) -> tuple[bool, Path | None]:
    """
    Validate that a requested path is safe and within the base directory.

    This function prevents path traversal attacks by:
    1. Resolving the full path (canonicalizes symlinks, .., etc.)
    2. Verifying the resolved path is within the base directory

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

        # Remove any leading slashes
        clean_path = requested_path.lstrip("/")

        # Reject paths with null bytes (potential injection attack)
        if "\x00" in clean_path:
            return False, None

        # Build and resolve the full path (resolves symlinks, .., etc)
        full_path = (base_path / clean_path).resolve()

        # CRITICAL: Verify the resolved path is within base_path
        # This prevents path traversal attacks like ../../etc/passwd
        full_path.relative_to(base_path.resolve())

        return True, full_path

    except (ValueError, RuntimeError, OSError):
        # ValueError: path is not relative to base_path (path traversal attempt)
        # RuntimeError: symlink loop or other path resolution issues
        # OSError: invalid path, permission issues, etc
        return False, None


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
        return resolved_path

    # Try directory with index.html
    if resolved_path.is_dir():
        index_file = resolved_path / "index.html"
        if index_file.is_file():
            # Verify index.html is still within base_path
            is_safe, _ = is_safe_path(base_path, str(index_file.relative_to(base_path)))
            if is_safe:
                return index_file

    # Try adding .html extension
    html_file = resolved_path.parent / f"{resolved_path.name}.html"
    if html_file.is_file():
        # Verify it's still within base_path
        try:
            html_file.relative_to(base_path.resolve())
            return html_file
        except (ValueError, RuntimeError):
            pass

    # Fallback to root index.html for SPA routing
    root_index = base_path / "index.html"
    if root_index.is_file():
        return root_index

    return None


def setup_static_file_serving(
    app: FastAPI, static_path: Path, env: str, serve_static: bool
) -> None:
    """
    Configure static file serving for the FastAPI application.

    Sets up:
    - StaticFiles middleware for _app and assets directories
    - Catch-all route for SPA routing with security validation

    Args:
        app: The FastAPI application instance
        static_path: Path to the static files directory
        env: Environment (development/production)
        serve_static: Whether to serve static files
    """
    should_serve = (env == "production" or serve_static) and static_path.exists()

    if not should_serve:
        if env == "development" and not serve_static:
            print("🚀 Development mode: Use Vite dev server at http://localhost:5173")
            print("   API available at http://localhost:8000/api/docs")
        else:
            print("⚠️  Static files not found at", static_path)
        return

    print(f"🎯 Serving static files from {static_path}")

    # Resolve static path once for security checks
    static_root = static_path.resolve()

    # Check if static files exist
    if not any(static_path.iterdir()):
        print("  ⚠️  Static directory exists but is empty")
        return

    # Mount SvelteKit app directories with StaticFiles
    if (static_path / "_app").exists():
        app.mount(
            "/_app",
            StaticFiles(directory=static_path / "_app", check_dir=True),
            name="static_app",
        )
        print("  ✓ Mounted /_app directory")

    if (static_path / "assets").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=static_path / "assets", check_dir=True),
            name="assets",
        )
        print("  ✓ Mounted /assets directory")

    # Catch-all route for SvelteKit client-side routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """
        Secure static file server with path traversal protection.

        Serves static files for SPA routing while preventing security vulnerabilities.
        """
        # API routes should never reach here (they're registered first)
        # but double-check as defense in depth
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Find and serve the appropriate file
        file_to_serve = find_file_to_serve(static_root, full_path)

        if file_to_serve and file_to_serve.is_file():
            return FileResponse(file_to_serve)

        raise HTTPException(status_code=404, detail="Not found")

    print("  ✓ Secure static file serving configured")
