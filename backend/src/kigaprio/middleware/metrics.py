"""Prometheus metrics middleware for KigaPrio backend"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware

# ============================================================================
# METRIC DEFINITIONS
# ============================================================================

# HTTP Request metrics
http_requests_total = Counter(
    "kigaprio_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "kigaprio_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

# Authentication metrics
login_attempts_total = Counter(
    "kigaprio_login_attempts_total",
    "Total login attempts",
    ["result", "client_ip"],  # result: success, failed_credentials, rate_limited
)

failed_login_total = Counter(
    "kigaprio_failed_login_total",
    "Total failed login attempts",
    ["reason"],  # reason: invalid_credentials, rate_limited, account_locked
)

admin_failed_auth_total = Counter(
    "kigaprio_admin_failed_auth_total",
    "Failed admin authentication attempts",
    ["reason"],
)

active_sessions = Gauge(
    "kigaprio_active_sessions",
    "Number of active sessions",
    ["security_mode"],  # session, persistent
)

admin_sessions_active = Gauge(
    "kigaprio_admin_sessions_active",
    "Number of active admin sessions",
)

# Rate limiting metrics
rate_limit_exceeded_total = Counter(
    "kigaprio_rate_limit_exceeded_total",
    "Rate limit violations",
    ["endpoint", "limit_type"],  # limit_type: login, api, magic_word
)

# Security metrics
unauthorized_access_total = Counter(
    "kigaprio_unauthorized_access_total",
    "Unauthorized access attempts (403)",
    ["endpoint"],
)

encryption_error_total = Counter(
    "kigaprio_encryption_error_total",
    "Encryption/decryption errors",
    ["operation"],  # operation: encrypt, decrypt, key_derivation
)

csp_violation_total = Counter(
    "kigaprio_csp_violation_total",
    "Content Security Policy violations",
    ["directive"],
)

# Session metrics
session_lookups_total = Counter(
    "kigaprio_session_lookups_total",
    "Total session lookups",
    ["result"],  # result: cache_hit, cache_miss, invalid
)

session_cache_miss_total = Counter(
    "kigaprio_session_cache_miss_total",
    "Session cache misses requiring PocketBase refresh",
)

# Data access metrics
priority_submissions_total = Counter(
    "kigaprio_priority_submissions_total",
    "Total priority submissions",
    ["month"],
)

data_operations_total = Counter(
    "kigaprio_data_operations_total",
    "Total data operations",
    ["operation", "collection"],  # operation: create, read, update, delete
)

# Database metrics
db_query_duration_seconds = Histogram(
    "kigaprio_db_query_duration_seconds",
    "Database query duration",
    ["operation", "collection"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)

db_connection_pool_active = Gauge(
    "kigaprio_db_connection_pool_active",
    "Active database connections",
)

db_connection_pool_max = Gauge(
    "kigaprio_db_connection_pool_max",
    "Maximum database connections",
)

# Redis metrics
redis_connection_error_total = Counter(
    "kigaprio_redis_connection_error_total",
    "Redis connection errors",
)

redis_operation_duration_seconds = Histogram(
    "kigaprio_redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5),
)

# System metrics
active_connections = Gauge(
    "kigaprio_active_connections",
    "Number of active HTTP connections",
)

health_check_status = Gauge(
    "kigaprio_health_check_status",
    "Health check status (1=healthy, 0=unhealthy)",
    ["component"],  # backend, redis, pocketbase
)

# Business metrics
magic_word_verification_total = Counter(
    "kigaprio_magic_word_verification_total",
    "Magic word verifications",
    ["result"],  # success, failed
)

magic_word_verification_failed_total = Counter(
    "kigaprio_magic_word_verification_failed_total",
    "Failed magic word verifications",
)

user_registrations_total = Counter(
    "kigaprio_user_registrations_total",
    "Total user registrations",
    ["result"],  # success, failed
)


# ============================================================================
# MIDDLEWARE
# ============================================================================


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/api/v1/metrics":
            return await call_next(request)

        # Track request start time
        start_time = time.time()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Process request
        try:
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            method = request.method
            path = self._get_path_template(request)
            status = response.status_code

            # Record HTTP metrics
            http_requests_total.labels(
                method=method, endpoint=path, status=status
            ).inc()

            http_request_duration_seconds.labels(method=method, endpoint=path).observe(
                duration
            )

            # Track specific security events
            if status == 401:
                # Unauthorized - failed auth
                if "login" in path:
                    failed_login_total.labels(reason="invalid_credentials").inc()
                    login_attempts_total.labels(
                        result="failed_credentials", client_ip=client_ip
                    ).inc()

            elif status == 403:
                # Forbidden - unauthorized access
                unauthorized_access_total.labels(endpoint=path).inc()

            elif status == 429:
                # Rate limit exceeded
                limit_type = self._get_rate_limit_type(path)
                rate_limit_exceeded_total.labels(
                    endpoint=path, limit_type=limit_type
                ).inc()

            return response

        except Exception:
            # Track errors
            duration = time.time() - start_time
            method = request.method
            path = self._get_path_template(request)

            http_requests_total.labels(method=method, endpoint=path, status=500).inc()

            http_request_duration_seconds.labels(method=method, endpoint=path).observe(
                duration
            )

            raise

    @staticmethod
    def _get_path_template(request: Request) -> str:
        """Extract path template for metric labels (remove IDs)"""
        # Get the matched route if available
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        # Fallback to raw path (sanitized)
        path = request.url.path

        # Remove common ID patterns to group related endpoints
        import re

        # Replace UUID patterns
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{id}",
            path,
        )

        # Replace month patterns (YYYY-MM)
        path = re.sub(r"/\d{4}-\d{2}", "/{month}", path)

        return path

    @staticmethod
    def _get_rate_limit_type(path: str) -> str:
        """Determine rate limit type from path"""
        if "login" in path:
            return "login"
        elif "magic-word" in path:
            return "magic_word"
        else:
            return "api"


# ============================================================================
# METRICS HELPERS (to be called from business logic)
# ============================================================================


def track_login_attempt(result: str, client_ip: str):
    """Track a login attempt"""
    login_attempts_total.labels(result=result, client_ip=client_ip).inc()
    if result != "success":
        failed_login_total.labels(reason=result).inc()


def track_session_lookup(result: str):
    """Track session cache lookup"""
    session_lookups_total.labels(result=result).inc()
    if result == "cache_miss":
        session_cache_miss_total.inc()


def track_encryption_error(operation: str):
    """Track encryption error"""
    encryption_error_total.labels(operation=operation).inc()


def track_priority_submission(month: str):
    """Track priority submission"""
    priority_submissions_total.labels(month=month).inc()


def track_data_operation(operation: str, collection: str):
    """Track data operation"""
    data_operations_total.labels(operation=operation, collection=collection).inc()


def track_magic_word_verification(success: bool):
    """Track magic word verification"""
    result = "success" if success else "failed"
    magic_word_verification_total.labels(result=result).inc()
    if not success:
        magic_word_verification_failed_total.inc()


def track_user_registration(success: bool):
    """Track user registration"""
    result = "success" if success else "failed"
    user_registrations_total.labels(result=result).inc()


def update_active_sessions(count: int, security_mode: str):
    """Update active session count"""
    active_sessions.labels(security_mode=security_mode).set(count)


def update_admin_sessions(count: int):
    """Update active admin session count"""
    admin_sessions_active.set(count)


def track_db_query(operation: str, collection: str, duration: float):
    """Track database query"""
    db_query_duration_seconds.labels(
        operation=operation, collection=collection
    ).observe(duration)


def track_redis_operation(operation: str, duration: float):
    """Track Redis operation"""
    redis_operation_duration_seconds.labels(operation=operation).observe(duration)


def track_redis_error():
    """Track Redis connection error"""
    redis_connection_error_total.inc()


def update_health_status(component: str, is_healthy: bool):
    """Update component health status"""
    health_check_status.labels(component=component).set(1 if is_healthy else 0)


def track_csp_violation(directive: str):
    """Track CSP violation"""
    csp_violation_total.labels(directive=directive).inc()


# ============================================================================
# METRICS ENDPOINT
# ============================================================================


async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
