from datetime import datetime, timezone

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Application, Company, JobDrive, JobSkill, Skill, Student, User
from app.schemas.job_drives import JobDriveCreate, JobDriveUpdate


def _load_options():
    return (
        joinedload(JobDrive.company),
        selectinload(JobDrive.skill_links).joinedload(JobSkill.skill),
    )


def _skill_for_name(db: Session, name: str) -> Skill:
    skill = db.scalar(select(Skill).where(func.lower(Skill.name) == name.casefold()).limit(1))
    return skill or Skill(name=name)


def _replace_skills(db: Session, drive: JobDrive, skills: list[str]) -> None:
    drive.skill_links.clear()
    db.flush()
    for name in skills:
        skill = _skill_for_name(db, name)
        db.add(skill)
        drive.skill_links.append(JobSkill(skill=skill, is_required=True))


def list_job_drives(
    db: Session,
    user: User,
    *,
    q: str | None,
    location: str | None,
    employment_type: str | None,
    graduation_year: int | None,
    status: str | None,
    company_id: int | None,
    limit: int,
    offset: int,
    company: str | None = None,
    package_min: float | None = None,
    package_max: float | None = None,
    application_status: str | None = None,
) -> list[JobDrive]:
    statement = select(JobDrive).join(JobDrive.company).options(*_load_options())
    if user.role == "student":
        statement = statement.where(JobDrive.status == "published", Company.is_active.is_(True))
    elif user.role == "recruiter":
        statement = statement.where(JobDrive.company_id == user.company_id)
    elif status:
        statement = statement.where(JobDrive.status == status.lower())
    if user.role == "admin" and company_id:
        statement = statement.where(JobDrive.company_id == company_id)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(JobDrive.title.ilike(pattern), JobDrive.description.ilike(pattern), Company.name.ilike(pattern))
        )
    if company:
        statement = statement.where(Company.name.ilike(f"%{company.strip()}%"))
    if location:
        statement = statement.where(JobDrive.location.ilike(f"%{location.strip()}%"))
    if employment_type:
        statement = statement.where(JobDrive.employment_type == employment_type)
    if graduation_year:
        statement = statement.where(
            or_(JobDrive.graduation_year == graduation_year, JobDrive.graduation_year.is_(None))
        )
    if package_min is not None:
        statement = statement.where(func.coalesce(JobDrive.compensation_max, JobDrive.compensation_min) >= package_min)
    if package_max is not None:
        statement = statement.where(func.coalesce(JobDrive.compensation_min, JobDrive.compensation_max) <= package_max)
    if user.role == "student" and application_status:
        student_id = select(Student.id).where(Student.user_id == user.id).scalar_subquery()
        matching_application = exists(select(Application.id).where(
            Application.student_id == student_id,
            Application.job_drive_id == JobDrive.id,
            Application.status == application_status.lower(),
        ))
        statement = statement.where(~matching_application if application_status.upper() == "NOT_APPLIED" else matching_application)
    return list(
        db.scalars(statement.order_by(JobDrive.application_deadline.asc().nullslast(), JobDrive.id.desc()).offset(offset).limit(limit)).unique().all()
    )


def get_job_drive(db: Session, drive_id: int) -> JobDrive | None:
    return db.scalar(select(JobDrive).where(JobDrive.id == drive_id).options(*_load_options()))


def create_job_drive(db: Session, payload: JobDriveCreate) -> JobDrive | None:
    company = db.get(Company, payload.company_id)
    if company is None or not company.is_active:
        return None
    values = payload.model_dump(exclude={"required_skills"})
    values["compensation_min"] = values.pop("package_min")
    values["compensation_max"] = values.pop("package_max")
    values["status"] = "draft"
    drive = JobDrive(**values)
    db.add(drive)
    _replace_skills(db, drive, payload.required_skills)
    db.commit()
    return get_job_drive(db, drive.id)


def update_job_drive(db: Session, drive: JobDrive, payload: JobDriveUpdate) -> JobDrive:
    changes = payload.model_dump(exclude_unset=True)
    requested_skills = changes.pop("required_skills", None)
    if "package_min" in changes:
        changes["compensation_min"] = changes.pop("package_min")
    if "package_max" in changes:
        changes["compensation_max"] = changes.pop("package_max")
    merged_min = changes.get("compensation_min", drive.compensation_min)
    merged_max = changes.get("compensation_max", drive.compensation_max)
    if merged_min is not None and merged_max is not None and merged_min > merged_max:
        raise ValueError("Minimum package cannot exceed maximum package.")
    if "company_id" in changes and changes["company_id"] != drive.company_id:
        company = db.get(Company, changes["company_id"])
        if company is None or not company.is_active:
            raise LookupError("Company not found or inactive.")
    for field, value in changes.items():
        setattr(drive, field, value)
    if requested_skills is not None:
        _replace_skills(db, drive, requested_skills)
    db.commit()
    return get_job_drive(db, drive.id) or drive


def transition_job_drive(db: Session, drive: JobDrive, target: str) -> JobDrive:
    allowed = {
        "draft": {"published", "cancelled"},
        "published": {"closed", "cancelled"},
        "closed": set(),
        "cancelled": set(),
    }
    if target not in allowed[drive.status]:
        raise ValueError(f"Cannot change a {drive.status.upper()} drive to {target.upper()}.")
    if target == "published":
        if drive.application_deadline is None:
            raise ValueError("Set an application deadline before publishing.")
        deadline = drive.application_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= datetime.now(timezone.utc):
            raise ValueError("Application deadline must be in the future to publish.")
        if not drive.company.is_active:
            raise ValueError("Cannot publish a drive for an inactive company.")
    drive.status = target
    db.commit()
    return get_job_drive(db, drive.id) or drive


def list_applicants(db: Session, drive_id: int) -> list[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.job_drive_id == drive_id)
            .options(joinedload(Application.student).joinedload(Student.user))
            .order_by(Application.applied_at, Application.id)
        ).all()
    )
