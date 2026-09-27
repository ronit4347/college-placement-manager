from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import User
from app.schemas.admin_users import InterviewerCreate, InterviewerResponse, InterviewerStatusUpdate
from app.services.admin_users import create_interviewer, list_interviewers, update_interviewer_status

router = APIRouter(prefix="/admin/interviewers", tags=["interviewer administration"])
admin_only = require_roles("ADMIN")


def _response(user: User) -> InterviewerResponse:
    return InterviewerResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role="INTERVIEWER",
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("", response_model=list[InterviewerResponse])
def get_interviewers(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [_response(user) for user in list_interviewers(db)]


@router.post("", response_model=InterviewerResponse, status_code=status.HTTP_201_CREATED)
def add_interviewer(payload: InterviewerCreate, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    try:
        return _response(create_interviewer(db, payload))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.") from None


@router.patch("/{user_id}/active", response_model=InterviewerResponse)
def set_interviewer_active(
    user_id: int,
    payload: InterviewerStatusUpdate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    interviewer = update_interviewer_status(db, user_id, payload.is_active)
    if interviewer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interviewer account not found.")
    return _response(interviewer)
