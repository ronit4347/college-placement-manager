from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ApplicationStatus = Literal[
    "APPLIED", "SHORTLISTED", "REJECTED", "INTERVIEW", "SELECTED", "OFFERED", "JOINED"
]


class ApplicationSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cover_letter: str | None = Field(default=None, max_length=5000)

    @field_validator("cover_letter")
    @classmethod
    def clean_cover_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ApplicationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ApplicationStatusEventResponse(BaseModel):
    id: int
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    actor_name: str | None
    note: str | None
    created_at: datetime


class ApplicationResponse(BaseModel):
    id: int
    job_drive_id: int
    drive_title: str
    company_name: str
    student_id: int
    student_name: str
    student_email: str
    roll_number: str | None
    branch: str | None
    cgpa: float | None
    status: ApplicationStatus
    cover_letter: str | None
    applied_at: datetime
    updated_at: datetime
    timeline: list[ApplicationStatusEventResponse]
