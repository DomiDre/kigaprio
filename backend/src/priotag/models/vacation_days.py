"""Pydantic models used in vacation days API"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def validate_date_format(date_str: str) -> str:
    """
    Validate date is in YYYY-MM-DD format.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Validated date string

    Raises:
        ValueError: If format is invalid
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Date must be in YYYY-MM-DD format: {e}") from e
    return date_str


class VacationDayCreate(BaseModel):
    """Request model for creating a vacation day."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    type: Literal["vacation", "admin_leave", "public_holiday"] = Field(
        ..., description="Type of vacation/leave day"
    )
    description: str = Field(
        default="", max_length=200, description="Optional description of the day"
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        return validate_date_format(v)


class VacationDayUpdate(BaseModel):
    """Request model for updating a vacation day."""

    type: Literal["vacation", "admin_leave", "public_holiday"] | None = Field(
        default=None, description="Type of vacation/leave day"
    )
    description: str | None = Field(
        default=None, max_length=200, description="Optional description of the day"
    )


class VacationDayResponse(BaseModel):
    """Response model for vacation day data (admin view)."""

    id: str
    date: str
    type: Literal["vacation", "admin_leave", "public_holiday"]
    description: str
    created_by: str
    created: str
    updated: str


class VacationDayUserResponse(BaseModel):
    """Response model for vacation day data (user view - simplified)."""

    date: str
    type: Literal["vacation", "admin_leave", "public_holiday"]
    description: str


class BulkVacationDayCreate(BaseModel):
    """Request model for creating multiple vacation days at once."""

    days: list[VacationDayCreate] = Field(
        ..., min_length=1, max_length=100, description="List of vacation days to create"
    )


class BulkVacationDayResponse(BaseModel):
    """Response model for bulk vacation day creation."""

    created: int
    skipped: int
    errors: list[dict[str, str]]


class VacationDayQuery(BaseModel):
    """Query parameters for filtering vacation days."""

    year: int | None = Field(default=None, ge=2020, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    type: Literal["vacation", "admin_leave", "public_holiday"] | None = None
    start_date: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="End date (YYYY-MM-DD)")

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_dates(cls, v: str | None) -> str | None:
        if v is not None:
            validate_date_format(v)
        return v
