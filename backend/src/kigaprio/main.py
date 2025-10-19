import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from kigaprio.api.routes import admin, auth, health, priorities
from kigaprio.config import settings
from kigaprio.logging_config import setup_logging
from kigaprio.middleware.security_headers import SecurityHeadersMiddleware
from kigaprio.services.redis_service import close_redis, redis_health_check
from kigaprio.static_files_utils import setup_static_file_serving

ENV = os.getenv("ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if ENV == "development" else "INFO")
SERVE_STATIC = os.getenv("SERVE_STATIC", "false").lower() == "true"
setup_logging(LOG_LEVEL)


logger = logging.getLogger(__name__)
logger.info("Starting KigaPrio API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app  # remove unused warning
    # Startup: test Redis connection
    if not redis_health_check():
        raise RuntimeError("Failed to connect to Redis")
    print("✓ Redis connected")

    yield

    # Shutdown: close connections
    close_redis()
    print("✓ Redis connections closed")


# Create FastAPI app
app = FastAPI(
    title="KigaPrio API",
    description="API for analyzing images and PDFs with Excel output generation",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    livespan=lifespan,
)


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

static_path = Path("/app/static")
app.add_middleware(
    SecurityHeadersMiddleware,
    static_path=static_path,
    enable_hsts=(ENV == "production"),
    csp_report_uri="/api/csp-violations",
)

# API routes
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(priorities.router, prefix="/api/v1/priorities", tags=["Prioliste"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Pocketbase"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.post("/api/csp-violations")
async def csp_violation_report(request: Request):
    report = await request.json()
    logger.warning(f"CSP Violation: {report}")
    return {"status": "ok"}


# Serve static files in production OR when explicitly enabled in development
setup_static_file_serving(
    app=app, static_path=static_path, env=ENV, serve_static=SERVE_STATIC
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "kigaprio.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENV == "development",
    )
