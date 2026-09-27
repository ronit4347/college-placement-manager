import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_roll_number(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9/-]{1,39}", normalized):
        raise ValueError("Roll number must be 2–40 letters, digits, slashes, or hyphens.")
    return normalized


def validate_phone(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    digits = sum(character.isdigit() for character in normalized)
    if not re.fullmatch(r"\+?[0-9().\-\s]{7,32}", normalized) or not 7 <= digits <= 15:
        raise ValueError("Enter a valid phone number with 7 to 15 digits.")
    return normalized


class StudentProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    roll_number: str | None = Field(default=None, max_length=40)
    branch: str | None = Field(default=None, min_length=2, max_length=120)
    cgpa: Decimal | None = Field(default=None, ge=0, le=10, max_digits=4, decimal_places=2)
    graduation_year: int | None = Field(default=None, ge=2000, le=2100)
    backlogs: int | None = Field(default=None, ge=0)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str | None) -> str | None:
        return normalize_email(value) if value is not None else None

    @field_validator("full_name", "branch")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Value must contain at least two characters.")
        return cleaned

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return validate_phone(value)

    @field_validator("roll_number")
    @classmethod
    def clean_roll_number(cls, value: str | None) -> str | None:
        return normalize_roll_number(value)

    @model_validator(mode="after")
    def require_an_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one profile field to update.")
        if "full_name" in self.model_fields_set and self.full_name is None:
            raise ValueError("Full name cannot be empty.")
        if "email" in self.model_fields_set and self.email is None:
            raise ValueError("Email cannot be empty.")
        if "backlogs" in self.model_fields_set and self.backlogs is None:
            raise ValueError("Backlogs cannot be empty.")
        return self


class StudentSkillsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[str] = Field(max_length=50)

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        normalized = [" ".join(value.split()) for value in values]
        if any(not value or len(value) > 100 for value in normalized):
            raise ValueError("Each skill must contain between 1 and 100 characters.")
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("Skills cannot contain duplicates.")
        return normalized


class StudentAdminCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    initial_password: str = Field(min_length=12, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    roll_number: str = Field(min_length=2, max_length=40)
    branch: str = Field(min_length=2, max_length=120)
    cgpa: Decimal = Field(ge=0, le=10, max_digits=4, decimal_places=2)
    graduation_year: int = Field(ge=2000, le=2100)
    backlogs: int = Field(default=0, ge=0)
    skills: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("full_name", "branch")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Value must contain at least two characters.")
        return cleaned

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return validate_phone(value)

    @field_validator("roll_number")
    @classmethod
    def clean_roll_number(cls, value: str) -> str:
        return normalize_roll_number(value) or value

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        return StudentSkillsUpdate(skills=values).skills


class StudentProfileResponse(BaseModel):
    student_id: int | None
    full_name: str
    email: EmailStr
    phone: str | None
    roll_number: str | None
    branch: str | None
    cgpa: Decimal | None
    graduation_year: int | None
    backlogs: int | None
    skills: list[str]
    resume_filename: str | None
    resume_max_size_bytes: int = Field(ge=1024)
    profile_completion: int = Field(ge=0, le=100)
    created_at: datetime | None
    updated_at: datetime | None


class AdminStudentResponse(StudentProfileResponse):
    placement_status: str
