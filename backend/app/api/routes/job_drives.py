from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import Application, Company, JobDrive, User
from app.models import Student
from app.schemas.job_drives import (
    ApplicantResponse,
    EligibleJobDriveResponse,
    DriveStatus,
    EmploymentType,
    JobDriveCreate,
    JobDriveResponse,
    JobDriveUpdate,
)
from app.schemas.eligibility import EligibilityResponse
from app.services.eligibility import evaluate_eligibility
from app.services.job_drives import (
    create_job_drive,
    get_job_drive,
    list_applicants,
    list_job_drives,
    transition_job_drive,
    update_job_drive,
)
from app.services.students import get_student_for_user

router = APIRouter(prefix="/job-drives", tags=["job drives"])
admin_only = require_roles("ADMIN")
drive_readers = require_roles("ADMIN", "STUDENT", "RECRUITER")
student_only = require_roles("STUDENT")


def drive_response(drive: JobDrive) -> JobDriveResponse:
    return JobDriveResponse(
        id=drive.id,
        company_id=drive.company_id,
        company_name=drive.company.name,
        title=drive.title,
        description=drive.description,
        package_min=drive.compensation_min,
        package_max=drive.compensation_max,
        location=drive.location,
        employment_type=drive.employment_type,
        min_cgpa=drive.min_cgpa,
        max_backlogs=drive.max_backlogs,
        allowed_branches=drive.allowed_branches,
        graduation_year=drive.graduation_year,
        required_skills=sorted(link.skill.name for link in drive.skill_links if link.is_required),
        application_deadline=drive.application_deadline,
        status=drive.status.upper(),
        created_at=drive.created_at,
        updated_at=drive.updated_at,
    )


def _get_visible_drive(db: Session, drive_id: int, user: User) -> JobDrive:
    drive = get_job_drive(db, drive_id)
    if drive is None:
        raise HTTPException(status_code=404, detail="Job drive not found.")
    if user.role == "student" and (drive.status != "published" or not drive.company.is_active):
        raise HTTPException(status_code=404, detail="Job drive not found.")
    if user.role == "recruiter" and drive.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Job drive not found.")
    return drive


@router.get("", response_model=list[JobDriveResponse])
def search_job_drives(
    q: str | None = Query(default=None, max_length=160),
    location: str | None = Query(default=None, max_length=200),
    employment_type: EmploymentType | None = None,
    graduation_year: int | None = Query(default=None, ge=2000, le=2100),
    status_filter: DriveStatus | None = Query(default=None, alias="status"),
    company_id: int | None = Query(default=None, gt=0),
    company: str | None = Query(default=None, max_length=120),
    package_min: float | None = Query(default=None, ge=0),
    package_max: float | None = Query(default=None, ge=0),
    eligibility: bool | None = None,
    application_status: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(drive_readers),
    db: Session = Depends(get_db),
) -> list[JobDriveResponse]:
    if package_min is not None and package_max is not None and package_min > package_max:
        raise HTTPException(status_code=422, detail="Minimum package filter cannot exceed maximum package filter.")
    valid_application_status = {"NOT_APPLIED", "APPLIED", "SHORTLISTED", "REJECTED", "INTERVIEW", "SELECTED", "OFFERED", "JOINED"}
    if application_status and (user.role != "student" or application_status.upper() not in valid_application_status):
        raise HTTPException(status_code=422, detail="Invalid application status filter.")
    query_limit, query_offset = (10000, 0) if user.role == "student" and eligibility is not None else (limit, offset)
    drives = list_job_drives(
        db,
        user,
        q=q,
        location=location,
        employment_type=employment_type,
        graduation_year=graduation_year,
        status=status_filter,
        company_id=company_id,
        limit=query_limit,
        offset=query_offset,
        company=company,
        package_min=package_min,
        package_max=package_max,
        application_status=application_status,
    )
    student = get_student_for_user(db, user) if user.role == "student" else None
    if user.role == "student" and eligibility is not None:
        drives = [drive for drive in drives if evaluate_eligibility(student, drive).eligible is eligibility]
        drives = drives[offset : offset + limit]
    responses = [drive_response(drive) for drive in drives]
    if user.role == "student" and drives:
        statuses = dict(db.query(Application.job_drive_id, Application.status)
                        .join(Student, Application.student_id == Student.id)
                        .filter(Student.user_id == user.id, Application.job_drive_id.in_([drive.id for drive in drives])).all())
        for response, drive in zip(responses, drives):
            response.is_eligible = evaluate_eligibility(student, drive).eligible
            response.application_status = statuses.get(drive.id, "").upper() or None
    return responses


@router.get("/eligible", response_model=list[EligibleJobDriveResponse])
def eligible_job_drives(
    q: str | None = Query(default=None, max_length=160),
    location: str | None = Query(default=None, max_length=200),
    employment_type: EmploymentType | None = None,
    graduation_year: int | None = Query(default=None, ge=2000, le=2100),
    student_user: User = Depends(student_only),
    db: Session = Depends(get_db),
) -> list[EligibleJobDriveResponse]:
    student = get_student_for_user(db, student_user)
    if student is None:
        return []
    drives = list_job_drives(
        db, student_user, q=q, location=location, employment_type=employment_type,
        graduation_year=graduation_year, status=None, company_id=None, limit=100, offset=0,
    )
    now = datetime.now(timezone.utc)
    eligible: list[EligibleJobDriveResponse] = []
    for drive in drives:
        deadline = drive.application_deadline
        if deadline is None:
            continue
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= now:
            continue
        result = evaluate_eligibility(student, drive)
        if result.eligible:
            eligible.append(EligibleJobDriveResponse(**drive_response(drive).model_dump(), eligibility_reasons=result.reasons))
    return eligible


@router.post("", response_model=JobDriveResponse, status_code=status.HTTP_201_CREATED)
def add_job_drive(
    payload: JobDriveCreate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> JobDriveResponse:
    company = db.get(Company, payload.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found.")
    if not company.is_active:
        raise HTTPException(status_code=409, detail="Job drives require an active company.")
    try:
        drive = create_job_drive(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Job drive values violate a database constraint.") from None
    if drive is None:
        raise HTTPException(status_code=404, detail="Company not found.")
    return drive_response(drive)


@router.get("/{drive_id}", response_model=JobDriveResponse)
def job_drive_details(
    drive_id: int,
    user: User = Depends(drive_readers),
    db: Session = Depends(get_db),
) -> JobDriveResponse:
    return drive_response(_get_visible_drive(db, drive_id, user))


@router.get("/{drive_id}/eligibility", response_model=EligibilityResponse)
def check_job_drive_eligibility(
    drive_id: int,
    student_user: User = Depends(student_only),
    db: Session = Depends(get_db),
) -> EligibilityResponse:
    drive = _get_visible_drive(db, drive_id, student_user)
    student = get_student_for_user(db, student_user)
    return evaluate_eligibility(student, drive)


@router.patch("/{drive_id}", response_model=JobDriveResponse)
def edit_job_drive(
    drive_id: int,
    payload: JobDriveUpdate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> JobDriveResponse:
    drive = get_job_drive(db, drive_id)
    if drive is None:
        raise HTTPException(status_code=404, detail="Job drive not found.")
    if drive.status in {"closed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Closed or cancelled drives cannot be edited.")
    try:
        return drive_response(update_job_drive(db, drive, payload))
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from None
    except LookupError as error:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Job drive values violate a database constraint.") from None


def _change_status(drive_id: int, target: str, db: Session) -> JobDriveResponse:
    drive = get_job_drive(db, drive_id)
    if drive is None:
        raise HTTPException(status_code=404, detail="Job drive not found.")
    try:
        return drive_response(transition_job_drive(db, drive, target))
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{drive_id}/publish", response_model=JobDriveResponse)
def publish_job_drive(
    drive_id: int, _: User = Depends(admin_only), db: Session = Depends(get_db)
) -> JobDriveResponse:
    return _change_status(drive_id, "published", db)


@router.post("/{drive_id}/close", response_model=JobDriveResponse)
def close_job_drive(
    drive_id: int, _: User = Depends(admin_only), db: Session = Depends(get_db)
) -> JobDriveResponse:
    return _change_status(drive_id, "closed", db)


@router.post("/{drive_id}/cancel", response_model=JobDriveResponse)
def cancel_job_drive(
    drive_id: int, _: User = Depends(admin_only), db: Session = Depends(get_db)
) -> JobDriveResponse:
    return _change_status(drive_id, "cancelled", db)


@router.get("/{drive_id}/applicants", response_model=list[ApplicantResponse])
def view_applicants(
    drive_id: int,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> list[ApplicantResponse]:
    if get_job_drive(db, drive_id) is None:
        raise HTTPException(status_code=404, detail="Job drive not found.")
    return [
        ApplicantResponse(
            application_id=application.id,
            student_id=application.student_id,
            student_name=application.student.user.full_name,
            email=application.student.user.email,
            roll_number=application.student.student_number,
            branch=application.student.branch,
            cgpa=application.student.cgpa,
            status=application.status.upper(),
            applied_at=application.applied_at,
        )
        for application in list_applicants(db, drive_id)
    ]
