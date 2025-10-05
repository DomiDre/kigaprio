"""Pydantic BaseModels of admin API"""

from typing import Any

from pydantic import BaseModel, Field


class UpdateMagicWordRequest(BaseModel):
    new_magic_word: str = Field(..., min_length=4)


class AdminLoginRequest(BaseModel):
    identity: str  # email or username
    password: str


class AdminAuthResponse(BaseModel):
    token: str
    admin: dict[str, Any]


class MonthStatsResponse(BaseModel):
    totalSubmissions: int
    completedWeeks: int
    pendingWeeks: int
    uniqueUsers: int
    weeklyCompletion: list[dict[str, Any]]


class UserSubmissionResponse(BaseModel):
    userId: str
    userName: str
    email: str | None
    completedWeeks: int
    totalWeeks: int
    lastActivity: str
    status: str  # 'complete' | 'partial' | 'none'


class ReminderRequest(BaseModel):
    userIds: list[str]
    message: str
    month: str | None = None


class ReminderResponse(BaseModel):
    sent: int
    failed: int
    details: list[dict[str, Any]]
