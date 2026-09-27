from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import User
from app.schemas.resume_analysis import ResumeAnalysisRequest, ResumeAnalysisResponse
from app.services.resume_analyzer import (
    AIProviderError, MalformedAIResponse, ResumeExtractionError,
    extract_resume_text, get_resume_analyzer, minimize_personal_data,
)
from app.services.resume_storage import resume_path
from app.services.students import get_student_for_user
from app.services.job_drives import get_job_drive

router = APIRouter(prefix="/students/me", tags=["resume analysis"])
student_only = require_roles("STUDENT")


@router.post("/resume-analysis", response_model=ResumeAnalysisResponse)
async def analyze_my_resume(
    payload: ResumeAnalysisRequest,
    user: User = Depends(student_only),
    db: Session = Depends(get_db),
) -> ResumeAnalysisResponse:
    student = get_student_for_user(db, user)
    path = resume_path(student.resume_url if student else None)
    if path is None:
        raise HTTPException(status_code=404, detail="Upload a PDF resume before requesting an analysis.")
    drive = get_job_drive(db, payload.job_drive_id)
    if drive is None or drive.status != "published" or not drive.company.is_active:
        raise HTTPException(status_code=404, detail="Published job drive not found.")
    try:
        resume_text = extract_resume_text(path)
        resume_text = minimize_personal_data(resume_text, user.full_name, user.email, student.phone if student else None)
        if not resume_text.strip():
            raise ResumeExtractionError("No analyzable resume text remains after removing personal identifiers.")
        skills = sorted(link.skill.name for link in drive.skill_links if link.is_required)
        return await get_resume_analyzer().analyze(resume_text, drive.title, drive.description, skills)
    except ResumeExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (AIProviderError, MalformedAIResponse) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
