"""Pydantic models used in priorities API"""

from pydantic import BaseModel


class Priority(BaseModel):
    id: int
    name: str
    color: str


class DayPriorities(BaseModel):
    monday: int | None = None
    tuesday: int | None = None
    wednesday: int | None = None
    thursday: int | None = None
    friday: int | None = None


class PriorityRecord(BaseModel):
    userId: str | None = None
    month: str
    weekNumber: int
    priorities: DayPriorities
    startDate: str
    endDate: str


class PriorityResponse(BaseModel):
    id: str
    userId: str
    month: str
    weekNumber: int
    priorities: dict
    startDate: str
    endDate: str
    created: str
    updated: str
