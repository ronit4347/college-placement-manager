from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

OfferStatus = Literal["DRAFT", "ISSUED", "ACCEPTED", "DECLINED", "EXPIRED"]


class OfferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_id: int = Field(gt=0)
    salary: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3, pattern="^[A-Za-z]{3}$")
    joining_date: date
    expires_at: datetime | None = None
    offer_letter_reference: str | None = Field(default=None, max_length=2048)

    @field_validator("expires_at")
    @classmethod
    def expiry_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Offer expiry must include a timezone.")
        return value

    @field_validator("offer_letter_reference")
    @classmethod
    def clean_reference(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class OfferStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ISSUED", "EXPIRED"]


class OfferDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ACCEPTED", "DECLINED"]


class OfferResponse(BaseModel):
    id: int
    application_id: int
    student_id: int
    candidate_name: str
    candidate_email: str
    company_id: int
    company_name: str
    job_drive_id: int
    job_title: str
    salary: Decimal | None
    currency: str
    joining_date: date | None
    status: OfferStatus
    offer_letter_reference: str | None
    issued_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
