"""Pydantic models used in priorities API"""

from pydantic import BaseModel, Field


class WeekPriority(BaseModel):
    """Priority data for a single week."""

    weekNumber: int = Field(ge=1, le=53)
    monday: int | None = Field(ge=1, le=5, default=None)
    tuesday: int | None = Field(ge=1, le=5, default=None)
    wednesday: int | None = Field(ge=1, le=5, default=None)
    thursday: int | None = Field(ge=1, le=5, default=None)
    friday: int | None = Field(ge=1, le=5, default=None)


class PriorityResponse(BaseModel):
    month: str
    weeks: list[WeekPriority]
