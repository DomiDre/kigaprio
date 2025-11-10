import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application logging."""

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger("priotag").setLevel(
        logging.DEBUG if log_level == "DEBUG" else logging.INFO
    )
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Suppress noisy libraries
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info(f"Logging configured with level: {log_level}")

    class HealthCheckFilter(logging.Filter):
        def filter(self, record):
            message = record.getMessage()
            return "/api/v1/health" not in message and "/api/health" not in message

    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
    logging.getLogger("gunicorn.access").addFilter(HealthCheckFilter())
    logging.getLogger("httpx").addFilter(HealthCheckFilter())
