from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

InterviewRound = Literal["APTITUDE", "TECHNICAL", "MANAGERIAL", "HR"]
InterviewStatus = Literal["SCHEDULED", "COMPLETED", "CANCELLED", "RESCHEDULED"]
InterviewResult = Literal["PENDING", "PASSED", "FAILED"]


class InterviewSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_id: int = Field(gt=0)
    round: InterviewRound
    interviewer_user_id: int = Field(gt=0)
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=240)

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Interview date/time must include a timezone.")
        return value


class InterviewReschedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime
    interviewer_user_id: int | None = Field(default=None, gt=0)

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Interview date/time must include a timezone.")
        return value


class InterviewResultUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: Literal["PASSED", "FAILED"]
    feedback: str | None = Field(default=None, max_length=5000)

    @field_validator("feedback")
    @classmethod
    def clean_feedback(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class InterviewerOption(BaseModel):
    id: int
    full_name: str
    email: str


class InterviewResponse(BaseModel):
    id: int
    application_id: int
    drive_title: str
    company_name: str
    round: InterviewRound
    interviewer_user_id: int | None
    interviewer_name: str | None
    scheduled_at: datetime
    duration_minutes: int
    status: InterviewStatus
    result: InterviewResult | None = None
    feedback: str | None = None
    student_name: str | None = None
    student_email: str | None = None
    roll_number: str | None = None
    branch: str | None = None
    cgpa: float | None = None


class StudentInterviewResponse(BaseModel):
    id: int
    application_id: int
    drive_title: str
    company_name: str
    round: InterviewRound
    scheduled_at: datetime
    duration_minutes: int
    status: InterviewStatus

