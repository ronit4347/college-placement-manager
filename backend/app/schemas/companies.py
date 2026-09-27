from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator, model_validator


def _clean_text(value: str | None, min_length: int = 1) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    if len(cleaned) < min_length:
        raise ValueError(f"Value must contain at least {min_length} characters.")
    return cleaned


class CompanyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    industry: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    website: HttpUrl | None = None
    hr_name: str | None = Field(default=None, max_length=160)
    hr_email: EmailStr | None = None
    description: str | None = Field(default=None, max_length=10000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _clean_text(value, 2) or value

    @field_validator("industry", "location", "hr_name", "description")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return _clean_text(value)

    @field_validator("hr_email")
    @classmethod
    def clean_hr_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value

    @field_validator("website")
    @classmethod
    def normalize_website(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is None:
            return None
        if value.scheme not in {"http", "https"}:
            raise ValueError("Website must use HTTP or HTTPS.")
        return value


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=200)
    industry: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    website: HttpUrl | None = None
    hr_name: str | None = Field(default=None, max_length=160)
    hr_email: EmailStr | None = None
    description: str | None = Field(default=None, max_length=10000)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return _clean_text(value, 2) if value is not None else None

    @field_validator("industry", "location", "hr_name", "description")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return _clean_text(value)

    @field_validator("hr_email")
    @classmethod
    def clean_hr_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value

    @field_validator("website")
    @classmethod
    def normalize_website(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is None:
            return None
        if value.scheme not in {"http", "https"}:
            raise ValueError("Website must use HTTP or HTTPS.")
        return value

    @model_validator(mode="after")
    def require_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one company field to update.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Company name cannot be empty.")
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("Active status cannot be empty.")
        return self


class RecruiterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    initial_password: str = Field(min_length=12, max_length=128)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        return _clean_text(value, 2) or value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class RecruiterSummary(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    is_active: bool


class CompanyResponse(BaseModel):
    id: int
    name: str
    industry: str | None
    location: str | None
    website: str | None
    hr_name: str | None
    hr_email: EmailStr | None
    description: str | None
    is_active: bool
    recruiters: list[RecruiterSummary]
    created_at: datetime
    updated_at: datetime
