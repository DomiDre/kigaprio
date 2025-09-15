from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from kigaprio.api.routes import health, upload, analyze
from kigaprio.config import settings

# Create FastAPI app
app = FastAPI(
    title="KigaPrio API",
    description="API for analyzing images and PDFs with Excel output generation",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analyze"])

# Serve static files (compiled Svelte frontend)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Serve index.html for SPA routing
    @app.get("/")
    async def serve_frontend():
        """Serve the frontend application."""
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {
            "message": "Frontend not found. Please build and copy your Svelte app to src/kigaprio/static/"
        }


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
