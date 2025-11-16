"""Pydantic models used in priorities API"""

from datetime import datetime, timedelta

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


def get_week_start_date(year: int, month: int, week_number: int) -> datetime:
    """
    Calculate the Monday (start date) of a specific week in a month.

    IMPORTANT: This must match the frontend logic exactly!
    The frontend only counts weeks that contain at least one day from the target month.

    For example, if November 1st is a Saturday:
    - Week starting Oct 27 (Mon-Fri: Oct 27-31) has NO November days -> SKIP
    - Week starting Nov 3 (Mon-Fri: Nov 3-7) has November days -> This is Week 1

    Args:
        year: Year
        month: Month (1-12, standard calendar month)
        week_number: Week number within the month (1-5)

    Returns:
        datetime object representing Monday of that week
    """
    # Get the first day of the month
    first_day = datetime(year, month, 1)

    # Find the Monday of the week containing the first day
    # weekday(): Monday=0, Sunday=6
    day_of_week = first_day.weekday()
    days_to_subtract = day_of_week  # If first_day is Monday, subtract 0
    current_monday = first_day - timedelta(days=days_to_subtract)

    # Iterate through weeks, only counting those that contain days from the target month
    weeks_found = 0
    max_iterations = 10  # Safety limit

    for _ in range(max_iterations):
        # Check if this week (Mon-Fri) contains any days from the target month
        week_has_month_days = False
        for day_offset in range(5):  # Monday to Friday
            check_date = current_monday + timedelta(days=day_offset)
            if check_date.year == year and check_date.month == month:
                week_has_month_days = True
                break

        if week_has_month_days:
            weeks_found += 1
            if weeks_found == week_number:
                # Found the requested week
                print(f"[get_week_start_date] year={year}, month={month}, week_number={week_number}")
                print(f"[get_week_start_date] Found week {week_number} starting on {current_monday.strftime('%Y-%m-%d %A')}")
                return current_monday

        # Move to next week
        current_monday += timedelta(weeks=1)

    # If we get here, something went wrong
    raise ValueError(f"Could not find week {week_number} for {year}-{month:02d}")


def validate_weeks_not_started(month: str, weeks: list["WeekPriority"]) -> None:
    """
    Validate that none of the provided weeks have already started.

    Args:
        month: Month string in YYYY-MM format
        weeks: List of WeekPriority objects

    Raises:
        ValueError: If any week has already started
    """
    month_date = datetime.strptime(month, "%Y-%m")
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)  # Today at midnight

    for week in weeks:
        week_start = get_week_start_date(
            month_date.year, month_date.month, week.weekNumber
        )

        # Set time to midnight for accurate comparison
        week_start_midnight = datetime(
            week_start.year, week_start.month, week_start.day
        )

        if today >= week_start_midnight:
            raise ValueError(
                f"Woche {week.weekNumber} hat bereits begonnen und kann nicht mehr bearbeitet werden"
            )


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
