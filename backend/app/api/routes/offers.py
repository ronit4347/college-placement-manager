from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import Application, Company, JobDrive, Offer, Student, User
from app.schemas.offers import OfferCreate, OfferDecision, OfferResponse, OfferStatusUpdate
from app.services.offers import create_offer, get_offer, issue_offer, list_offers, respond_to_offer, update_offer_status

router = APIRouter(prefix="/offers", tags=["offers"])
admin_only = require_roles("ADMIN")
student_only = require_roles("STUDENT")
readers = require_roles("ADMIN", "STUDENT", "RECRUITER")


def _response(offer: Offer) -> OfferResponse:
    application = offer.application
    drive = application.job_drive
    student = application.student
    return OfferResponse(
        id=offer.id, application_id=application.id, student_id=student.id,
        candidate_name=student.user.full_name, candidate_email=student.user.email,
        company_id=drive.company_id, company_name=drive.company.name,
        job_drive_id=drive.id, job_title=drive.title, salary=offer.salary,
        currency=offer.currency, joining_date=offer.joining_date,
        status=offer.status.upper(), offer_letter_reference=offer.offer_letter_reference,
        issued_at=offer.issued_at, expires_at=offer.expires_at,
        created_at=offer.created_at, updated_at=offer.updated_at,
    )


def _visible_offer(db: Session, offer_id: int, user: User) -> Offer:
    offer = get_offer(db, offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found.")
    if user.role == "student" and (offer.application.student.user_id != user.id or offer.status == "draft"):
        raise HTTPException(status_code=404, detail="Offer not found.")
    if user.role == "recruiter" and offer.application.job_drive.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Offer not found.")
    return offer


@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create(payload: OfferCreate, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    application = db.scalar(select(Application).where(Application.id == payload.application_id).options(
        joinedload(Application.offers), joinedload(Application.student).joinedload(Student.user),
        joinedload(Application.job_drive).joinedload(JobDrive.company)))
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    try:
        return _response(create_offer(db, application, payload, admin))
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An active offer already exists for this application.") from None


@router.get("", response_model=list[OfferResponse])
def list_mine_or_scoped(user: User = Depends(readers), db: Session = Depends(get_db)):
    return [_response(offer) for offer in list_offers(db, user)]


@router.get("/{offer_id}", response_model=OfferResponse)
def details(offer_id: int, user: User = Depends(readers), db: Session = Depends(get_db)):
    return _response(_visible_offer(db, offer_id, user))


@router.post("/{offer_id}/issue", response_model=OfferResponse)
def issue(offer_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    offer = _visible_offer(db, offer_id, admin)
    try:
        return _response(issue_offer(db, offer, admin))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.patch("/{offer_id}/status", response_model=OfferResponse)
def update_status(offer_id: int, payload: OfferStatusUpdate, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    offer = _visible_offer(db, offer_id, admin)
    try:
        return _response(update_offer_status(db, offer, payload.status.lower(), admin))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{offer_id}/respond", response_model=OfferResponse)
def respond(offer_id: int, payload: OfferDecision, student: User = Depends(student_only), db: Session = Depends(get_db)):
    offer = _visible_offer(db, offer_id, student)
    try:
        return _response(respond_to_offer(db, offer, student, payload.status.lower()))
    except LookupError:
        raise HTTPException(status_code=404, detail="Offer not found.") from None
    except TimeoutError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
