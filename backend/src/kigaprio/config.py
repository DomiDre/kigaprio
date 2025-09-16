"""Configuration settings for the application."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env")
    # Environment
    ENV: str = Field(default="development", description="Environment")
    LOG_LEVEL: str = Field(default="info", description="Log level")

    # API Settings
    API_PREFIX: str = Field(default="/api", description="API prefix")
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # File Upload Settings
    MAX_FILE_SIZE: int = Field(
        default=50 * 1024 * 1024, description="Max file size in bytes (50MB)"
    )
    ALLOWED_EXTENSIONS: list[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".pdf", ".gif", ".bmp", ".tiff"],
        description="Allowed file extensions",
    )
    UPLOAD_DIR: str = Field(default="uploads", description="Upload directory")
    OUTPUT_DIR: str = Field(default="output", description="Output directory")

    # Processing Settings
    MAX_CONCURRENT_PROCESSES: int = Field(
        default=4, description="Max concurrent file processes"
    )
    PROCESS_TIMEOUT: int = Field(default=300, description="Process timeout in seconds")


# Create global settings instance
settings = Settings()
