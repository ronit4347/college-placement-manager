from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User
from app.schemas.admin_users import InterviewerCreate


def list_interviewers(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role == "interviewer").order_by(User.full_name, User.id)))


def create_interviewer(db: Session, payload: InterviewerCreate) -> User:
    interviewer = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.initial_password),
        role="interviewer",
        is_active=True,
    )
    db.add(interviewer)
    db.commit()
    db.refresh(interviewer)
    return interviewer


def update_interviewer_status(db: Session, user_id: int, is_active: bool) -> User | None:
    interviewer = db.scalar(select(User).where(User.id == user_id, User.role == "interviewer"))
    if interviewer is None:
        return None
    interviewer.is_active = is_active
    db.commit()
    db.refresh(interviewer)
    return interviewer
