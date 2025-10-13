"""Pydantic models used in priorities API"""

from datetime import datetime

from pydantic import BaseModel, Field


def validate_month_format_and_range(month: str) -> str:
    """
    Validate month is in YYYY-MM format and within allowed range.

    Allowed range: current month to 2 months in the future.

    Args:
        month: Month string in YYYY-MM format

    Returns:
        Validated month string

    Raises:
        ValueError: If format is invalid or out of range
    """
    month_date = datetime.strptime(month, "%Y-%m")

    now = datetime.now()
    current_month = datetime(now.year, now.month, 1)

    # Calculate max date (2 months ahead)
    max_month = current_month.month + 2
    max_year = current_month.year
    if max_month > 12:
        max_month -= 12
        max_year += 1
    max_date = datetime(max_year, max_month, 1)

    if month_date < current_month or month_date > max_date:
        raise ValueError(
            f"Month must be between {current_month.strftime('%Y-%m')} "
            f"and {max_date.strftime('%Y-%m')}"
        )

    return month


class WeekPriority(BaseModel):
    """Priority data for a single week."""

    weekNumber: int = Field(ge=1, le=53)
    monday: int | None = Field(ge=1, le=5, default=None)
    tuesday: int | None = Field(ge=1, le=5, default=None)
    wednesday: int | None = Field(ge=1, le=5, default=None)
    thursday: int | None = Field(ge=1, le=5, default=None)
    friday: int | None = Field(ge=1, le=5, default=None)


class PriorityResponse(BaseModel):
    """Response model for priority data."""

    month: str
    weeks: list[WeekPriority]
