from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import User
from app.schemas.students import (
    StudentAdminCreate,
    AdminStudentResponse,
    StudentProfileResponse,
    StudentProfileUpdate,
    StudentSkillsUpdate,
)
from app.services.resume_storage import remove_resume, resume_path, save_resume_upload
from app.services.students import (
    attach_resume,
    create_student,
    deactivate_student,
    get_or_create_student,
    get_student_by_id,
    get_student_for_user,
    list_students,
    profile_response,
    replace_student_skills,
    update_own_profile,
    update_student,
)

router = APIRouter(prefix="/students", tags=["students"])
student_only = require_roles("STUDENT")
admin_only = require_roles("ADMIN")


def _commit_profile_update(db: Session, operation) -> StudentProfileResponse:
    try:
        return operation()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or roll number is already in use.",
        ) from None


@router.get("/me", response_model=StudentProfileResponse)
def get_my_profile(
    user: User = Depends(student_only), db: Session = Depends(get_db)
) -> StudentProfileResponse:
    return profile_response(user, get_student_for_user(db, user))


@router.patch("/me", response_model=StudentProfileResponse)
def update_my_profile(
    payload: StudentProfileUpdate,
    user: User = Depends(student_only),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    return _commit_profile_update(db, lambda: update_own_profile(db, user, payload))


@router.put("/me/skills", response_model=StudentProfileResponse)
def update_my_skills(
    payload: StudentSkillsUpdate,
    user: User = Depends(student_only),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    return _commit_profile_update(db, lambda: replace_student_skills(db, user, payload))


@router.post("/me/resume", response_model=StudentProfileResponse)
async def upload_my_resume(
    file: UploadFile = File(...),
    user: User = Depends(student_only),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    student = get_or_create_student(db, user)
    filename = await save_resume_upload(file)
    old_filename = student.resume_url
    try:
        old_filename = attach_resume(db, student, filename)
    except Exception:
        db.rollback()
        remove_resume(filename)
        raise
    remove_resume(old_filename)
    return profile_response(user, get_student_for_user(db, user))


@router.get("/me/resume")
def download_my_resume(
    user: User = Depends(student_only), db: Session = Depends(get_db)
) -> FileResponse:
    student = get_student_for_user(db, user)
    path = resume_path(student.resume_url if student else None)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return FileResponse(path, media_type="application/pdf", filename="resume.pdf")


@router.get("", response_model=list[AdminStudentResponse])
def admin_list_students(
    q: str | None = Query(default=None, max_length=160),
    roll_number: str | None = Query(default=None, max_length=40),
    branch: str | None = Query(default=None, max_length=120),
    min_cgpa: float | None = Query(default=None, ge=0, le=10),
    max_cgpa: float | None = Query(default=None, ge=0, le=10),
    placement_status: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> list[AdminStudentResponse]:
    if min_cgpa is not None and max_cgpa is not None and min_cgpa > max_cgpa:
        raise HTTPException(status_code=422, detail="Minimum CGPA cannot exceed maximum CGPA.")
    allowed_statuses = {"NOT_APPLIED", "APPLIED", "SHORTLISTED", "INTERVIEW", "SELECTED", "OFFERED", "REJECTED", "JOINED", "PLACED"}
    if placement_status and placement_status.upper() not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Invalid placement status filter.")
    return list_students(db, limit, offset, q=q, roll_number=roll_number, branch=branch,
                         min_cgpa=min_cgpa, max_cgpa=max_cgpa, placement_status=placement_status)


@router.post("", response_model=StudentProfileResponse, status_code=status.HTTP_201_CREATED)
def admin_create_student(
    payload: StudentAdminCreate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    return _commit_profile_update(db, lambda: create_student(db, payload))


@router.get("/{student_id}", response_model=StudentProfileResponse)
def admin_get_student(
    student_id: int,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return profile_response(student.user, student)


@router.patch("/{student_id}", response_model=StudentProfileResponse)
def admin_update_student(
    student_id: int,
    payload: StudentProfileUpdate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return _commit_profile_update(db, lambda: update_student(db, student, payload))


@router.put("/{student_id}/skills", response_model=StudentProfileResponse)
def admin_update_student_skills(
    student_id: int,
    payload: StudentSkillsUpdate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    try:
        replace_skills_for_student(db, student, payload)
        db.commit()
        db.refresh(student)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to update skills.") from None
    return profile_response(student.user, get_student_by_id(db, student.id))


@router.post("/{student_id}/resume", response_model=StudentProfileResponse)
async def admin_upload_student_resume(
    student_id: int,
    file: UploadFile = File(...),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    filename = await save_resume_upload(file)
    try:
        old_filename = attach_resume(db, student, filename)
    except Exception:
        db.rollback()
        remove_resume(filename)
        raise
    remove_resume(old_filename)
    return profile_response(student.user, get_student_by_id(db, student.id))


@router.get("/{student_id}/resume")
def admin_download_student_resume(
    student_id: int,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> FileResponse:
    student = get_student_by_id(db, student_id)
    path = resume_path(student.resume_url if student else None)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return FileResponse(path, media_type="application/pdf", filename="resume.pdf")


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_deactivate_student(
    student_id: int,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> None:
    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    deactivate_student(db, student)
