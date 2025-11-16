"""
Unit tests for priority models and validation functions.

Tests cover:
- validate_weeks_not_started (week validation logic)
- validate_month_format_and_range (month validation)
- get_week_start_date (week calculation)
- WeekPriority model validation
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from priotag.models.priorities import (
    WeekPriority,
    get_week_start_date,
    validate_month_format_and_range,
    validate_weeks_not_started,
)


@pytest.mark.unit
class TestValidateWeeksNotStarted:
    """Test validate_weeks_not_started function."""

    def test_future_weeks_pass_validation(self):
        """Should pass validation for weeks that haven't started yet."""
        # Get a future month (next month)
        future_month = (datetime.now() + timedelta(days=32)).strftime("%Y-%m")

        weeks = [
            WeekPriority(weekNumber=1, monday=1),
            WeekPriority(weekNumber=2, tuesday=2),
            WeekPriority(weekNumber=3, wednesday=3),
        ]

        # Should not raise an exception
        validate_weeks_not_started(future_month, weeks)

    def test_started_week_fails_validation(self):
        """Should raise ValueError for weeks that have already started."""
        # Get current month
        current_month = datetime.now().strftime("%Y-%m")
        now = datetime.now()

        # Create a week that should have started (week 1 of current month)
        # This test assumes we're not in the first week of the month
        # If we are, we need to handle it differently

        # Calculate which week of the current month we're in
        first_day = datetime(now.year, now.month, 1)
        day_of_week = first_day.weekday()
        first_week_monday = first_day - timedelta(days=day_of_week)

        # Calculate the current week number
        days_since_first_monday = (now - first_week_monday).days
        current_week_number = (days_since_first_monday // 7) + 1

        # If we're in week 1 or later, test with week 1
        if current_week_number >= 1:
            weeks = [WeekPriority(weekNumber=1, monday=1)]

            with pytest.raises(ValueError) as exc_info:
                validate_weeks_not_started(current_month, weeks)

            assert "hat bereits begonnen" in str(exc_info.value)
            assert "Woche 1" in str(exc_info.value)

    def test_mixed_weeks_fails_validation(self):
        """Should raise ValueError if any week has started, even if others haven't."""
        current_month = datetime.now().strftime("%Y-%m")

        # Mix of started week (1) and future weeks
        weeks = [
            WeekPriority(weekNumber=1, monday=1),
            WeekPriority(weekNumber=5, tuesday=2),  # Likely future week
        ]

        # Should fail because week 1 has likely started
        with pytest.raises(ValueError) as exc_info:
            validate_weeks_not_started(current_month, weeks)

        assert "hat bereits begonnen" in str(exc_info.value)

    def test_empty_weeks_pass_validation(self):
        """Should pass validation for empty weeks list."""
        current_month = datetime.now().strftime("%Y-%m")
        weeks = []

        # Should not raise an exception
        validate_weeks_not_started(current_month, weeks)


@pytest.mark.unit
class TestValidateMonthFormatAndRange:
    """Test validate_month_format_and_range function."""

    def test_current_month_passes(self):
        """Should pass validation for current month."""
        current_month = datetime.now().strftime("%Y-%m")
        result = validate_month_format_and_range(current_month)
        assert result == current_month

    def test_future_month_within_range_passes(self):
        """Should pass validation for month within allowed range."""
        future_month = (datetime.now() + timedelta(days=32)).strftime("%Y-%m")
        result = validate_month_format_and_range(future_month)
        assert result == future_month

    def test_past_month_fails(self):
        """Should raise ValueError for past months."""
        past_month = (datetime.now() - timedelta(days=32)).strftime("%Y-%m")

        with pytest.raises(ValueError) as exc_info:
            validate_month_format_and_range(past_month)

        assert "Month must be between" in str(exc_info.value)

    def test_far_future_month_fails(self):
        """Should raise ValueError for months too far in the future."""
        far_future = (datetime.now() + timedelta(days=120)).strftime("%Y-%m")

        with pytest.raises(ValueError) as exc_info:
            validate_month_format_and_range(far_future)

        assert "Month must be between" in str(exc_info.value)

    def test_invalid_format_fails(self):
        """Should raise ValueError for invalid month format."""
        with pytest.raises(ValueError):
            validate_month_format_and_range("2025-13")  # Invalid month

        with pytest.raises(ValueError):
            validate_month_format_and_range("202501")  # Wrong format

        with pytest.raises(ValueError):
            validate_month_format_and_range("01-2025")  # Wrong order


@pytest.mark.unit
class TestGetWeekStartDate:
    """Test get_week_start_date function."""

    def test_first_week_of_month_starting_monday(self):
        """Should calculate correct Monday for month starting on Monday."""
        # January 2024 starts on a Monday
        result = get_week_start_date(2024, 1, 1)

        # First week should start on Jan 1, 2024 (Monday)
        assert result == datetime(2024, 1, 1)
        assert result.weekday() == 0  # Monday

    def test_first_week_of_month_not_starting_monday(self):
        """Should calculate Monday in previous month if needed."""
        # January 2025 starts on a Wednesday
        result = get_week_start_date(2025, 1, 1)

        # First week's Monday should be Dec 30, 2024
        assert result == datetime(2024, 12, 30)
        assert result.weekday() == 0  # Monday

    def test_subsequent_weeks(self):
        """Should calculate correct dates for subsequent weeks."""
        # Get first week
        week1 = get_week_start_date(2025, 1, 1)

        # Week 2 should be 7 days later
        week2 = get_week_start_date(2025, 1, 2)
        assert week2 == week1 + timedelta(days=7)
        assert week2.weekday() == 0

        # Week 3 should be 14 days after week 1
        week3 = get_week_start_date(2025, 1, 3)
        assert week3 == week1 + timedelta(days=14)
        assert week3.weekday() == 0

    def test_week_5(self):
        """Should calculate correct date for week 5."""
        week5 = get_week_start_date(2025, 1, 5)

        # Should still be a Monday
        assert week5.weekday() == 0


@pytest.mark.unit
class TestWeekPriorityModel:
    """Test WeekPriority Pydantic model."""

    def test_valid_week_priority(self):
        """Should create valid WeekPriority with valid data."""
        week = WeekPriority(
            weekNumber=1,
            monday=1,
            tuesday=2,
            wednesday=3,
            thursday=4,
            friday=5,
        )

        assert week.weekNumber == 1
        assert week.monday == 1
        assert week.tuesday == 2

    def test_week_number_validation(self):
        """Should validate week number range."""
        # Week number too low
        with pytest.raises(ValidationError):
            WeekPriority(weekNumber=0, monday=1)

        # Week number too high
        with pytest.raises(ValidationError):
            WeekPriority(weekNumber=54, monday=1)

        # Valid range
        WeekPriority(weekNumber=1, monday=1)  # Min
        WeekPriority(weekNumber=53, monday=1)  # Max

    def test_priority_value_validation(self):
        """Should validate priority values (1-5)."""
        # Priority too low
        with pytest.raises(ValidationError):
            WeekPriority(weekNumber=1, monday=0)

        # Priority too high
        with pytest.raises(ValidationError):
            WeekPriority(weekNumber=1, monday=6)

        # Valid range
        WeekPriority(weekNumber=1, monday=1)  # Min
        WeekPriority(weekNumber=1, monday=5)  # Max

    def test_optional_days(self):
        """Should allow None for day priorities."""
        week = WeekPriority(weekNumber=1)

        assert week.monday is None
        assert week.tuesday is None
        assert week.wednesday is None
        assert week.thursday is None
        assert week.friday is None

    def test_partial_week_data(self):
        """Should allow partial week data with some days set."""
        week = WeekPriority(
            weekNumber=1,
            monday=1,
            wednesday=3,
            friday=5,
        )

        assert week.monday == 1
        assert week.tuesday is None
        assert week.wednesday == 3
        assert week.thursday is None
        assert week.friday == 5
