from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Application, Interview, Student, User
from app.services.notifications import notify_interview_recipients


def list_interviews(db: Session, user: User) -> list[Interview]:
    query = select(Interview).options(
        joinedload(Interview.application).joinedload(Application.student).joinedload(Student.user),
        joinedload(Interview.application).joinedload(Application.job_drive),
        joinedload(Interview.interviewer),
    )
    if user.role == "interviewer":
        query = query.where(Interview.interviewer_user_id == user.id)
    elif user.role == "student":
        query = query.join(Interview.application).join(Application.student).where(Application.student.has(user_id=user.id))
    return list(db.scalars(query.order_by(Interview.scheduled_at.desc())).unique())


def get_interview(db: Session, interview_id: int) -> Interview | None:
    return db.scalar(
        select(Interview).options(
            joinedload(Interview.application).joinedload(Application.student).joinedload(Student.user),
            joinedload(Interview.application).joinedload(Application.job_drive),
            joinedload(Interview.interviewer),
        ).where(Interview.id == interview_id)
    )


def ensure_no_conflict(db: Session, interview: Interview | None, interviewer_id: int, start: datetime, duration: int) -> None:
    start_utc = start.astimezone(timezone.utc)
    end_utc = start_utc + timedelta(minutes=duration)
    candidates = db.scalars(select(Interview).where(
        Interview.interviewer_user_id == interviewer_id,
        Interview.status.in_(["scheduled", "rescheduled"]),
        Interview.id != (interview.id if interview else -1),
    )).all()
    for existing in candidates:
        old_start = existing.scheduled_at
        if old_start.tzinfo is None:
            old_start = old_start.replace(tzinfo=timezone.utc)
        old_start = old_start.astimezone(timezone.utc)
        old_end = old_start + timedelta(minutes=existing.duration_minutes)
        if start_utc < old_end and end_utc > old_start:
            raise ValueError("The interviewer already has an interview scheduled during this time.")


def interviewer_user(db: Session, user_id: int) -> User | None:
    user = db.get(User, user_id)
    return user if user and user.role == "interviewer" and user.is_active else None


def schedule_interview(db: Session, application: Application, interviewer: User, round_name: str, when: datetime, duration: int) -> Interview:
    if when <= datetime.now(timezone.utc):
        raise ValueError("Interview date/time must be in the future.")
    ensure_no_conflict(db, None, interviewer.id, when, duration)
    interview = Interview(application=application, interviewer_user_id=interviewer.id,
                          round_name=round_name.lower(), scheduled_at=when, duration_minutes=duration)
    db.add(interview)
    notify_interview_recipients(db, interview, "interview_scheduled", "Interview scheduled",
                                f"{round_name.title()} interview for {application.job_drive.title} is scheduled at {when.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.")
    db.commit()
    return get_interview(db, interview.id)


def reschedule_interview(db: Session, interview: Interview, when: datetime, interviewer: User | None) -> Interview:
    if interview.status in ("completed", "cancelled"):
        raise ValueError("Completed or cancelled interviews cannot be rescheduled.")
    if when <= datetime.now(timezone.utc):
        raise ValueError("Interview date/time must be in the future.")
    assigned_id = interviewer.id if interviewer else interview.interviewer_user_id
    if assigned_id is None:
        raise ValueError("Assign an interviewer before rescheduling.")
    ensure_no_conflict(db, interview, assigned_id, when, interview.duration_minutes)
    interview.scheduled_at = when
    interview.interviewer_user_id = assigned_id
    interview.status = "rescheduled"
    notify_interview_recipients(db, interview, "interview_rescheduled", "Interview rescheduled",
                                f"Your {interview.round_name.title()} interview for {interview.application.job_drive.title} has been rescheduled to {when.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.")
    db.commit()
    return get_interview(db, interview.id)


def cancel_interview(db: Session, interview: Interview) -> Interview:
    if interview.status == "completed":
        raise ValueError("Completed interviews cannot be cancelled.")
    if interview.status == "cancelled":
        raise ValueError("Interview is already cancelled.")
    interview.status = "cancelled"
    db.commit()
    return get_interview(db, interview.id)


def submit_result(db: Session, interview: Interview, result: str, feedback: str | None) -> Interview:
    if interview.status not in ("scheduled", "rescheduled"):
        raise ValueError("A result can only be submitted for an active interview.")
    interview.result = result.lower()
    interview.feedback = feedback
    interview.status = "completed"
    notify_interview_recipients(db, interview, "interview_result", "Interview result available",
                                f"Your {interview.round_name.title()} interview result is {result.upper()}.", include_interviewer=False)
    db.commit()
    return get_interview(db, interview.id)
