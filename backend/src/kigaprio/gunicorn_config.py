import logging


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        # Filter out health check requests
        if hasattr(record, "args") and record.args:
            # Gunicorn access log format includes the URL path
            message = record.getMessage()
            return "/api/v1/health" not in message
        return True


# Gunicorn configuration
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"


# Configure logging
def on_starting(server):
    """Called just before the master process is initialized."""
    # Add filter to gunicorn access logger
    gunicorn_logger = logging.getLogger("gunicorn.access")
    gunicorn_logger.addFilter(HealthCheckFilter())

    # Also add to uvicorn if needed
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.addFilter(HealthCheckFilter())
