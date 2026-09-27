from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

NotificationType = Literal[
    "application_submitted", "application_shortlisted", "application_rejected",
    "interview_scheduled", "interview_rescheduled", "interview_result",
    "candidate_selected", "offer_issued",
]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: NotificationType
    title: str
    message: str
    link: str | None
    created_at: datetime
    read_at: datetime | None


class UnreadCountResponse(BaseModel):
    unread_count: int
