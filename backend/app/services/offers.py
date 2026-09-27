from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Application, ApplicationStatusEvent, Company, JobDrive, Offer, Student, User
from app.services.notifications import notify_application_student


def _options():
    return (joinedload(Offer.application).joinedload(Application.student).joinedload(Student.user),
            joinedload(Offer.application).joinedload(Application.job_drive).joinedload(JobDrive.company))


def get_offer(db: Session, offer_id: int) -> Offer | None:
    return db.scalar(select(Offer).where(Offer.id == offer_id).options(*_options()))


def list_offers(db: Session, user: User) -> list[Offer]:
    query = select(Offer).join(Offer.application).join(Application.job_drive).options(*_options())
    if user.role == "student":
        query = query.join(Application.student).where(Student.user_id == user.id, Offer.status != "draft")
    elif user.role == "recruiter":
        query = query.join(JobDrive.company).where(Company.id == user.company_id)
    offers = list(db.scalars(query.order_by(Offer.created_at.desc())).unique())
    if _expire_overdue(db, offers):
        db.commit()
    return offers


def _expire_overdue(db: Session, offers: list[Offer]) -> bool:
    now = datetime.now(timezone.utc)
    changed = False
    for offer in offers:
        expiration = offer.expires_at
        if offer.status == "issued" and expiration is not None:
            if expiration.tzinfo is None:
                expiration = expiration.replace(tzinfo=timezone.utc)
            if expiration <= now:
                offer.status = "expired"
                changed = True
    return changed


def create_offer(db: Session, application: Application, payload, actor: User) -> Offer:
    if application.status != "selected":
        raise ValueError("An offer can only be created for a SELECTED candidate.")
    if any(offer.status in ("draft", "issued") for offer in application.offers):
        raise FileExistsError("An active offer already exists for this application.")
    if payload.expires_at and payload.expires_at <= datetime.now(timezone.utc):
        raise ValueError("Offer expiry must be in the future.")
    offer = Offer(application_id=application.id, salary=payload.salary, currency=payload.currency.upper(),
                  joining_date=payload.joining_date, expires_at=payload.expires_at,
                  offer_letter_reference=payload.offer_letter_reference, status="draft")
    db.add(offer)
    db.commit()
    return get_offer(db, offer.id)


def _mark_application_offered(db: Session, offer: Offer, actor: User) -> None:
    application = offer.application
    if application.status == "selected":
        application.status = "offered"
        db.add(ApplicationStatusEvent(application_id=application.id, from_status="selected", to_status="offered",
                                      actor_user_id=actor.id, note="Offer issued to candidate."))


def issue_offer(db: Session, offer: Offer, actor: User) -> Offer:
    if offer.status != "draft":
        raise ValueError("Only draft offers can be issued.")
    if offer.application.status != "selected":
        raise ValueError("An offer can only be issued to a SELECTED candidate.")
    if offer.expires_at:
        expiration = offer.expires_at
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)
        if expiration <= datetime.now(timezone.utc):
            offer.status = "expired"
            db.commit()
            raise ValueError("This offer has expired and cannot be issued.")
    offer.status = "issued"
    offer.issued_at = datetime.now(timezone.utc)
    _mark_application_offered(db, offer, actor)
    notify_application_student(db, offer.application, "offer_issued", "A placement offer was issued",
                               f"A placement offer for {offer.application.job_drive.title} is ready for your response.")
    db.commit()
    return get_offer(db, offer.id)


def update_offer_status(db: Session, offer: Offer, target: str, actor: User) -> Offer:
    if target == "issued":
        return issue_offer(db, offer, actor)
    if target != "expired":
        raise ValueError("Administrators can issue or expire offers; candidates respond to issued offers.")
    _expire_overdue(db, [offer])
    if offer.status not in ("draft", "issued"):
        raise ValueError("Only active offers can be expired.")
    offer.status = "expired"
    db.commit()
    return get_offer(db, offer.id)


def respond_to_offer(db: Session, offer: Offer, user: User, decision: str) -> Offer:
    if offer.application.student.user_id != user.id:
        raise LookupError("Offer not found.")
    _expire_overdue(db, [offer])
    if offer.status == "expired":
        db.commit()
        raise TimeoutError("This offer has expired.")
    if offer.status != "issued":
        raise ValueError("Only issued offers can be accepted or declined.")
    offer.status = decision.lower()
    db.commit()
    return get_offer(db, offer.id)
