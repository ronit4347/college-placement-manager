from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Application, Notification, User


def add_notification(db: Session, user_id: int | None, kind: str, title: str, message: str, link: str | None) -> None:
    if user_id is not None:
        db.add(Notification(user_id=user_id, type=kind, title=title, message=message, link=link))


def notify_application_student(db: Session, application: Application, kind: str, title: str, message: str) -> None:
    add_notification(db, application.student.user_id, kind, title, message, f"/applications/{application.id}")


def notify_application_staff(db: Session, application: Application) -> None:
    """Notify placement admins and recruiters for the drive's company of a new application."""
    recipients = db.scalars(select(User.id).where(User.is_active.is_(True), User.role == "admin")).all()
    recruiters = db.scalars(select(User.id).where(
        User.is_active.is_(True), User.role == "recruiter", User.company_id == application.job_drive.company_id
    )).all()
    title = "New placement application"
    message = f"{application.student.user.full_name} applied for {application.job_drive.title}."
    for user_id in set(recipients + recruiters):
        add_notification(db, user_id, "application_submitted", title, message, f"/applications/{application.id}")


def notify_interview_recipients(db: Session, interview, kind: str, title: str, message: str, *, include_interviewer: bool = True) -> None:
    student_user_id = interview.application.student.user_id
    add_notification(db, student_user_id, kind, title, message, "/student/interviews")
    if include_interviewer and interview.interviewer_user_id:
        add_notification(db, interview.interviewer_user_id, kind, title, message, "/interviewer/interviews")


def list_notifications(db: Session, user: User, limit: int, offset: int) -> list[Notification]:
    return list(db.scalars(select(Notification).where(Notification.user_id == user.id)
                           .order_by(Notification.created_at.desc(), Notification.id.desc())
                           .offset(offset).limit(limit)).all())


def unread_count(db: Session, user: User) -> int:
    return db.scalar(select(func.count(Notification.id)).where(
        Notification.user_id == user.id, Notification.read_at.is_(None)
    )) or 0


def mark_notification_read(db: Session, user: User, notification_id: int) -> Notification | None:
    notification = db.scalar(select(Notification).where(
        Notification.id == notification_id, Notification.user_id == user.id
    ))
    if notification is None:
        return None
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification
