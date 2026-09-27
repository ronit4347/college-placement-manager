from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Application,
    ApplicationStatusEvent,
    Company,
    JobDrive,
    Student,
    User,
)
from app.schemas.applications import ApplicationSubmit, ApplicationStatusUpdate
from app.services.eligibility import evaluate_eligibility
from app.services.students import get_student_for_user
from app.services.notifications import notify_application_staff, notify_application_student


class IneligibleApplicationError(Exception):
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("Student is not eligible to apply.")


def _application_options():
    return (
        joinedload(Application.student).joinedload(Student.user),
        joinedload(Application.job_drive).joinedload(JobDrive.company),
        selectinload(Application.status_events).joinedload(ApplicationStatusEvent.actor),
        selectinload(Application.offers),
    )


def get_application(db: Session, application_id: int) -> Application | None:
    return db.scalar(
        select(Application)
        .where(Application.id == application_id)
        .options(*_application_options())
    )


def list_applications(
    db: Session,
    user: User,
    *,
    status: str | None,
    job_drive_id: int | None,
    limit: int,
    offset: int,
    company: str | None = None,
    job: str | None = None,
    branch: str | None = None,
) -> list[Application]:
    statement = select(Application).join(Application.job_drive).options(*_application_options())
    if user.role == "student":
        student_id = db.scalar(select(Student.id).where(Student.user_id == user.id))
        if student_id is None:
            return []
        statement = statement.where(Application.student_id == student_id)
    elif user.role == "recruiter":
        statement = statement.join(JobDrive.company).where(Company.id == user.company_id)
    if status:
        statement = statement.where(Application.status == status.lower())
    if job_drive_id:
        statement = statement.where(Application.job_drive_id == job_drive_id)
    if company:
        statement = statement.where(JobDrive.company.has(Company.name.ilike(f"%{company.strip()}%")))
    if job:
        statement = statement.where(JobDrive.title.ilike(f"%{job.strip()}%"))
    if branch:
        statement = statement.where(Application.student.has(Student.branch.ilike(f"%{branch.strip()}%")))
    return list(
        db.scalars(
            statement.order_by(Application.applied_at.desc(), Application.id.desc())
            .offset(offset)
            .limit(limit)
        ).unique().all()
    )


def apply_to_job_drive(
    db: Session,
    user: User,
    drive: JobDrive,
    payload: ApplicationSubmit,
) -> Application:
    student = get_student_for_user(db, user)
    if student is None:
        raise ValueError("Complete your student profile before applying.")
    if drive.status != "published":
        raise ValueError("Only published job drives accept applications.")
    if not drive.company.is_active:
        raise ValueError("This company's job drives are not accepting applications.")
    if drive.application_deadline is None:
        raise ValueError("This job drive has no application deadline and is not accepting applications.")
    deadline = drive.application_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline <= datetime.now(timezone.utc):
        raise ValueError("The application deadline has passed.")
    existing = db.scalar(
        select(Application.id).where(
            Application.student_id == student.id,
            Application.job_drive_id == drive.id,
        )
    )
    if existing is not None:
        raise FileExistsError("You have already applied to this job drive.")
    eligibility = evaluate_eligibility(student, drive)
    if not eligibility.eligible:
        raise IneligibleApplicationError(eligibility.reasons)

    application = Application(
        student_id=student.id,
        job_drive_id=drive.id,
        status="applied",
        cover_letter=payload.cover_letter,
    )
    db.add(application)
    db.flush()
    db.add(
        ApplicationStatusEvent(
            application_id=application.id,
            from_status=None,
            to_status="applied",
            actor_user_id=user.id,
            note="Application submitted.",
        )
    )
    notify_application_student(
        db, application, "application_submitted", "Application submitted",
        f"Your application for {drive.title} was submitted successfully.",
    )
    notify_application_staff(db, application)
    db.commit()
    db.expire(application, ["status_events", "offers"])
    return get_application(db, application.id) or application


def transition_application_status(
    db: Session,
    application: Application,
    actor: User,
    payload: ApplicationStatusUpdate,
) -> Application:
    db.scalar(select(Application.id).where(Application.id == application.id).with_for_update())
    db.refresh(application, attribute_names=["status"])
    target = payload.status.lower()
    transitions = {
        "applied": {"shortlisted", "rejected"},
        "shortlisted": {"interview", "rejected"},
        "interview": {"selected", "rejected"},
        "selected": set(),
        "offered": {"joined"},
        "rejected": set(),
        "joined": set(),
    }
    current = application.status
    if target not in transitions[current]:
        raise ValueError(f"Cannot change an application from {current.upper()} to {target.upper()}.")

    application.status = target
    if target == "offered":
        raise ValueError("An offer must be issued by the offer management workflow.")
    if target == "joined" and not any(offer.status == "accepted" for offer in application.offers):
        raise ValueError("A candidate must accept an issued offer before being marked JOINED.")
    db.add(
        ApplicationStatusEvent(
            application_id=application.id,
            from_status=current,
            to_status=target,
            actor_user_id=actor.id,
            note=payload.note,
        )
    )
    if target == "shortlisted":
        notify_application_student(db, application, "application_shortlisted", "You were shortlisted", f"You were shortlisted for {application.job_drive.title}.")
    elif target == "rejected":
        notify_application_student(db, application, "application_rejected", "Application update", f"Your application for {application.job_drive.title} was not selected to continue.")
    elif target == "selected":
        notify_application_student(db, application, "candidate_selected", "You were selected", f"You were selected for {application.job_drive.title}.")
    db.commit()
    db.expire(application, ["status_events", "offers"])
    return get_application(db, application.id) or application
