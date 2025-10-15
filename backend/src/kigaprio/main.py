import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from kigaprio.api.routes import admin, auth, health, priorities
from kigaprio.config import settings
from kigaprio.middleware.auth_middleware import TokenRefreshMiddleware


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        return "/api/v1/health" not in message


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
logging.getLogger("gunicorn.access").addFilter(HealthCheckFilter())

# Create FastAPI app
app = FastAPI(
    title="KigaPrio API",
    description="API for analyzing images and PDFs with Excel output generation",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
ENV = os.getenv("ENV", "production")
SERVE_STATIC = os.getenv("SERVE_STATIC", "false").lower() == "true"

# CORS configuration
if ENV == "development":
    # In development, allow frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production CORS
    allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

# add middlewares
app.add_middleware(TokenRefreshMiddleware)

# API routes
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(priorities.router, prefix="/api/v1/priorities", tags=["Prioliste"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Pocketbase"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

# Serve static files (compiled Svelte frontend)
static_path = Path("/app/static")

# Serve static files in production OR when explicitly enabled in development
if (ENV == "production" or SERVE_STATIC) and static_path.exists():
    print(f"🎯 Serving static files from {static_path}")

    # Check if static files actually exist
    if any(static_path.iterdir()):
        # Mount SvelteKit app directories
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
            # Skip API routes
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")

            # Reject absolute paths
            if Path(full_path).is_absolute() or full_path.startswith("/"):
                raise HTTPException(status_code=400, detail="Invalid path")

            # Resolve static root once
            static_root = static_path.resolve()

            # Handle empty path (root request)
            if not full_path or full_path == "/":
                index_path = static_root / "index.html"
                if index_path.exists():
                    return FileResponse(index_path)
                raise HTTPException(status_code=404, detail="Not found")

            # Sanitize the requested path
            try:
                # Build the full path and resolve it
                requested_path = (static_root / full_path).resolve()

                # Security check: ensure the resolved path is within static_root
                requested_path.relative_to(static_root)
            except (ValueError, RuntimeError) as e:
                # Path traversal attempt or invalid path
                raise HTTPException(status_code=400, detail="Invalid path") from e

            # Try exact file match
            if requested_path.exists() and requested_path.is_file():
                return FileResponse(requested_path)

            # Try as directory with index.html
            index_in_dir = requested_path / "index.html"
            if index_in_dir.exists() and index_in_dir.is_file():
                return FileResponse(index_in_dir)

            # Try with .html extension
            html_file = (
                requested_path.parent / f"{requested_path.name}.html"
            ).resolve()
            if html_file.exists() and html_file.is_file():
                # Verify it's still within static_root
                try:
                    html_file.relative_to(static_root)
                    return FileResponse(html_file)
                except (ValueError, RuntimeError) as e:
                    raise HTTPException(status_code=400, detail="Invalid path") from e

            # Fallback to root index.html for client-side routing
            index_path = static_root / "index.html"
            if index_path.exists():
                return FileResponse(index_path)

            raise HTTPException(status_code=404, detail="Not found")

        print("  ✓ Static file serving configured")
    else:
        print("  ⚠️  Static directory exists but is empty")
elif ENV == "development" and not SERVE_STATIC:
    print("🚀 Development mode: Use Vite dev server at http://localhost:5173")
    print("   API available at http://localhost:8000/api/docs")
else:
    print("⚠️  Static files not found at", static_path)


# Catch-all route for SPA routing (should be last)
@app.get("/{path:path}")
async def catch_all(path: str):
    """Catch-all route for SPA routing."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")

    # Check if it's an API route
    if path.startswith("api/"):
        return {"error": "API endpoint not found"}

    # Serve index.html for all other routes (SPA routing)
    if os.path.exists(index_path):
        return FileResponse(index_path)

    return {
        "message": "Frontend not found. Please build and copy your Svelte app to src/kigaprio/static/"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "kigaprio.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENV == "development",
    )
