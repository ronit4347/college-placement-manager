from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DriveStatus = Literal["DRAFT", "PUBLISHED", "CLOSED", "CANCELLED"]
EmploymentType = Literal["FULL_TIME", "PART_TIME", "INTERNSHIP", "CONTRACT", "OTHER"]


def _clean_text(value: str, *, minimum: int = 1) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) < minimum:
        raise ValueError(f"Value must contain at least {minimum} characters.")
    return cleaned


def _clean_names(values: list[str] | None, label: str) -> list[str] | None:
    if values is None:
        return None
    cleaned = [_clean_text(value) for value in values]
    canonical = [value.casefold() for value in cleaned]
    if len(canonical) != len(set(canonical)):
        raise ValueError(f"{label} cannot contain duplicates.")
    return cleaned


class JobDriveFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=20, max_length=20000)
    package_min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    package_max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    location: str | None = Field(default=None, max_length=200)
    employment_type: EmploymentType | None = None
    min_cgpa: Decimal | None = Field(default=None, ge=0, le=10, max_digits=4, decimal_places=2)
    max_backlogs: int | None = Field(default=None, ge=0)
    allowed_branches: list[str] | None = Field(default=None, max_length=100)
    graduation_year: int | None = Field(default=None, ge=2000, le=2100)
    required_skills: list[str] = Field(default_factory=list, max_length=50)
    application_deadline: datetime | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _clean_text(value, minimum=2)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return _clean_text(value, minimum=20)

    @field_validator("location")
    @classmethod
    def clean_location(cls, value: str | None) -> str | None:
        return _clean_text(value) if value is not None else None

    @field_validator("allowed_branches")
    @classmethod
    def clean_branches(cls, values: list[str] | None) -> list[str] | None:
        return _clean_names(values, "Allowed branches")

    @field_validator("required_skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        return _clean_names(values, "Required skills") or []

    @field_validator("application_deadline")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Application deadline must include a timezone.")
        return value

    @model_validator(mode="after")
    def valid_package_range(self) -> Self:
        if self.package_min is not None and self.package_max is not None and self.package_min > self.package_max:
            raise ValueError("Minimum package cannot exceed maximum package.")
        return self


class JobDriveCreate(JobDriveFields):
    pass


class JobDriveUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=20, max_length=20000)
    package_min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    package_max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    location: str | None = Field(default=None, max_length=200)
    employment_type: EmploymentType | None = None
    min_cgpa: Decimal | None = Field(default=None, ge=0, le=10, max_digits=4, decimal_places=2)
    max_backlogs: int | None = Field(default=None, ge=0)
    allowed_branches: list[str] | None = Field(default=None, max_length=100)
    graduation_year: int | None = Field(default=None, ge=2000, le=2100)
    required_skills: list[str] | None = Field(default=None, max_length=50)
    application_deadline: datetime | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return _clean_text(value, minimum=2) if value is not None else None

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return _clean_text(value, minimum=20) if value is not None else None

    @field_validator("location")
    @classmethod
    def clean_location(cls, value: str | None) -> str | None:
        return _clean_text(value) if value is not None else None

    @field_validator("allowed_branches")
    @classmethod
    def clean_branches(cls, values: list[str] | None) -> list[str] | None:
        return _clean_names(values, "Allowed branches")

    @field_validator("required_skills")
    @classmethod
    def clean_skills(cls, values: list[str] | None) -> list[str] | None:
        return _clean_names(values, "Required skills")

    @field_validator("application_deadline")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Application deadline must include a timezone.")
        return value

    @model_validator(mode="after")
    def require_update_and_valid_range(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one job drive field to update.")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Job title cannot be empty.")
        if "description" in self.model_fields_set and self.description is None:
            raise ValueError("Description cannot be empty.")
        if "company_id" in self.model_fields_set and self.company_id is None:
            raise ValueError("Company cannot be empty.")
        return self


class JobDriveResponse(BaseModel):
    id: int
    company_id: int
    company_name: str
    title: str
    description: str
    package_min: Decimal | None
    package_max: Decimal | None
    location: str | None
    employment_type: EmploymentType | None
    min_cgpa: Decimal | None
    max_backlogs: int | None
    allowed_branches: list[str] | None
    graduation_year: int | None
    required_skills: list[str]
    application_deadline: datetime | None
    status: DriveStatus
    created_at: datetime
    updated_at: datetime
    is_eligible: bool | None = None
    application_status: Literal["APPLIED", "SHORTLISTED", "REJECTED", "INTERVIEW", "SELECTED", "OFFERED", "JOINED"] | None = None


class EligibleJobDriveResponse(JobDriveResponse):
    eligibility_reasons: list[str] = Field(default_factory=list)


class ApplicantResponse(BaseModel):
    application_id: int
    student_id: int
    student_name: str
    email: str
    roll_number: str | None
    branch: str | None
    cgpa: Decimal | None
    status: str
    applied_at: datetime
