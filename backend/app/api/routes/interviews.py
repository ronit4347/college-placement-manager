from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import Application, Interview, User
from app.schemas.interviews import (
    InterviewResponse, InterviewResultUpdate, InterviewReschedule, InterviewSchedule,
    InterviewerOption, StudentInterviewResponse,
)
from app.services.interviews import (
    cancel_interview, get_interview, interviewer_user, list_interviews,
    reschedule_interview, schedule_interview, submit_result,
)

router = APIRouter(prefix="/interviews", tags=["interviews"])
admin_only = require_roles("ADMIN")
interviewer_only = require_roles("INTERVIEWER")
readers = require_roles("ADMIN", "INTERVIEWER", "STUDENT")


def _response(interview: Interview, student_view: bool = False):
    app = interview.application
    data = dict(id=interview.id, application_id=app.id, drive_title=app.job_drive.title,
                company_name=app.job_drive.company.name, round=interview.round_name.upper(),
                scheduled_at=interview.scheduled_at, duration_minutes=interview.duration_minutes,
                status=interview.status.upper())
    if student_view:
        return StudentInterviewResponse(**data)
    student = app.student
    return InterviewResponse(**data, interviewer_user_id=interview.interviewer_user_id,
        interviewer_name=interview.interviewer.full_name if interview.interviewer else None,
        result=interview.result.upper(), feedback=interview.feedback,
        student_name=student.user.full_name, student_email=student.user.email,
        roll_number=student.student_number, branch=student.branch,
        cgpa=float(student.cgpa) if student.cgpa is not None else None)


def _get_or_404(db: Session, interview_id: int) -> Interview:
    interview = get_interview(db, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return interview


@router.get("/interviewers", response_model=list[InterviewerOption])
def get_interviewers(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    users = db.scalars(select(User).where(User.role == "interviewer", User.is_active).order_by(User.full_name)).all()
    return [InterviewerOption(id=user.id, full_name=user.full_name, email=user.email) for user in users]


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def create_interview(payload: InterviewSchedule, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    application = db.get(Application, payload.application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    if application.status not in ("shortlisted", "interview"):
        raise HTTPException(status_code=409, detail="Only shortlisted applications can be scheduled for interview.")
    interviewer = interviewer_user(db, payload.interviewer_user_id)
    if not interviewer:
        raise HTTPException(status_code=422, detail="Select an active user with the INTERVIEWER role.")
    try:
        return _response(schedule_interview(db, application, interviewer, payload.round, payload.scheduled_at, payload.duration_minutes))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.get("", response_model=list[InterviewResponse | StudentInterviewResponse])
def interviews(user: User = Depends(readers), db: Session = Depends(get_db)):
    return [_response(item, user.role == "student") for item in list_interviews(db, user)]


@router.get("/{interview_id}", response_model=InterviewResponse | StudentInterviewResponse)
def interview_detail(interview_id: int, user: User = Depends(readers), db: Session = Depends(get_db)):
    interview = _get_or_404(db, interview_id)
    if user.role == "student" and interview.application.student.user_id != user.id:
        raise HTTPException(status_code=404, detail="Interview not found.")
    if user.role == "interviewer" and interview.interviewer_user_id != user.id:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return _response(interview, user.role == "student")


@router.patch("/{interview_id}/reschedule", response_model=InterviewResponse)
def reschedule(interview_id: int, payload: InterviewReschedule, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    interview = _get_or_404(db, interview_id)
    new_interviewer = None
    if payload.interviewer_user_id:
        new_interviewer = interviewer_user(db, payload.interviewer_user_id)
        if not new_interviewer:
            raise HTTPException(status_code=422, detail="Select an active user with the INTERVIEWER role.")
    try:
        return _response(reschedule_interview(db, interview, payload.scheduled_at, new_interviewer))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{interview_id}/cancel", response_model=InterviewResponse)
def cancel(interview_id: int, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    try:
        return _response(cancel_interview(db, _get_or_404(db, interview_id)))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.patch("/{interview_id}/result", response_model=InterviewResponse)
def result(interview_id: int, payload: InterviewResultUpdate, user: User = Depends(interviewer_only), db: Session = Depends(get_db)):
    interview = _get_or_404(db, interview_id)
    if interview.interviewer_user_id != user.id:
        raise HTTPException(status_code=404, detail="Interview not found.")
    try:
        return _response(submit_result(db, interview, payload.result, payload.feedback))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
