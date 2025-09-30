import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from kigaprio.api.routes import admin, analyze, database, health, priolist, upload
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
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
assert POCKETBASE_URL is not None, "Pocketbase URL not specified by env"

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
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analyze"])
app.include_router(priolist.router, prefix="/api/v1/priorities", tags=["Prioliste"])
app.include_router(database.router, prefix="/api/v1", tags=["Pocketbase"])
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
                return {"error": "Not found"}, 404

            # Helper to ensure a path stays inside static_path
            def safe_path(path: Path) -> Path | None:
                try:
                    resolved = path.resolve()
                    static_root = static_path.resolve()
                    if resolved.is_relative_to(static_root):
                        return resolved
                    else:
                        return None
                except Exception:
                    return None

            # Try exact file match first
            file_path = safe_path(static_path / full_path)
            if file_path and file_path.exists() and file_path.is_file():
                return FileResponse(file_path)

            # Try as directory with index.html (e.g., /login -> /login/index.html)
            index_in_dir = safe_path(static_path / full_path / "index.html")
            if index_in_dir and index_in_dir.exists():
                return FileResponse(index_in_dir)

            # Try with .html extension (e.g., /about -> /about.html)
            html_file = safe_path(static_path / f"{full_path}.html")
            if html_file and html_file.exists():
                return FileResponse(html_file)

            # Fallback to root index.html for client-side routing
            index_path = static_path / "index.html"
            if index_path.exists():
                return FileResponse(index_path)

            return {"error": "Not found"}, 404

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
