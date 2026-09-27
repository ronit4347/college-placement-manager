from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import Application, User
from app.schemas.applications import (
    ApplicationResponse,
    ApplicationStatus,
    ApplicationStatusEventResponse,
    ApplicationStatusUpdate,
    ApplicationSubmit,
)
from app.services.applications import (
    IneligibleApplicationError,
    apply_to_job_drive,
    get_application,
    list_applications,
    transition_application_status,
)
from app.services.job_drives import get_job_drive

router = APIRouter(prefix="/applications", tags=["applications"])
submission_router = APIRouter(prefix="/job-drives", tags=["applications"])
application_readers = require_roles("ADMIN", "STUDENT", "RECRUITER")
student_only = require_roles("STUDENT")
admin_only = require_roles("ADMIN")


def application_response(application: Application) -> ApplicationResponse:
    student = application.student
    return ApplicationResponse(
        id=application.id,
        job_drive_id=application.job_drive_id,
        drive_title=application.job_drive.title,
        company_name=application.job_drive.company.name,
        student_id=student.id,
        student_name=student.user.full_name,
        student_email=student.user.email,
        roll_number=student.student_number,
        branch=student.branch,
        cgpa=student.cgpa,
        status=application.status.upper(),
        cover_letter=application.cover_letter,
        applied_at=application.applied_at,
        updated_at=application.updated_at,
        timeline=[
            ApplicationStatusEventResponse(
                id=event.id,
                from_status=event.from_status.upper() if event.from_status else None,
                to_status=event.to_status.upper(),
                actor_name=event.actor.full_name if event.actor else None,
                note=event.note,
                created_at=event.created_at,
            )
            for event in application.status_events
        ],
    )


def _check_application_access(application: Application, user: User) -> None:
    if user.role == "student" and application.student.user_id != user.id:
        raise HTTPException(status_code=404, detail="Application not found.")
    if user.role == "recruiter" and application.job_drive.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Application not found.")


@submission_router.post(
    "/{job_drive_id}/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_application(
    job_drive_id: int,
    payload: ApplicationSubmit,
    student: User = Depends(student_only),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    drive = get_job_drive(db, job_drive_id)
    if drive is None:
        raise HTTPException(status_code=404, detail="Job drive not found.")
    if drive.status != "published":
        raise HTTPException(status_code=409, detail="Only published job drives accept applications.")
    try:
        application = apply_to_job_drive(db, student, drive, payload)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except IneligibleApplicationError as error:
        raise HTTPException(
            status_code=409,
            detail={"message": str(error), "eligible": False, "reasons": error.reasons},
        ) from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already applied to this job drive.") from None
    return application_response(application)


@router.get("", response_model=list[ApplicationResponse])
def my_or_scoped_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    job_drive_id: int | None = Query(default=None, gt=0),
    company: str | None = Query(default=None, max_length=120),
    job: str | None = Query(default=None, max_length=160),
    branch: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(application_readers),
    db: Session = Depends(get_db),
) -> list[ApplicationResponse]:
    records = list_applications(
        db,
        user,
        status=status_filter,
        job_drive_id=job_drive_id,
        limit=limit,
        offset=offset,
        company=company if user.role in ("admin", "recruiter") else None,
        job=job if user.role in ("admin", "recruiter") else None,
        branch=branch if user.role in ("admin", "recruiter") else None,
    )
    return [application_response(application) for application in records]


@router.get("/{application_id}", response_model=ApplicationResponse)
def application_details(
    application_id: int,
    user: User = Depends(application_readers),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    application = get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    _check_application_access(application, user)
    return application_response(application)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    application = get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    try:
        return application_response(transition_application_status(db, application, admin, payload))
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from None
