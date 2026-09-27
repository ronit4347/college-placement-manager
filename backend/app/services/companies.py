from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password
from app.models import Company, User
from app.schemas.companies import CompanyCreate, CompanyUpdate, RecruiterCreate


def list_companies(
    db: Session,
    *,
    q: str | None,
    industry: str | None,
    is_active: bool | None,
    limit: int,
    offset: int,
    current_user: User,
    name: str | None = None,
) -> list[Company]:
    statement = select(Company).options(selectinload(Company.recruiters))
    if current_user.role == "recruiter":
        statement = statement.where(Company.id == current_user.company_id)
    elif current_user.role != "admin":
        statement = statement.where(Company.is_active.is_(True))
    elif is_active is not None:
        statement = statement.where(Company.is_active.is_(is_active))

    if name:
        statement = statement.where(Company.name.ilike(f"%{name.strip()}%"))
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Company.name.ilike(pattern),
                Company.industry.ilike(pattern),
                Company.location.ilike(pattern),
            )
        )
    if industry:
        statement = statement.where(Company.industry.ilike(f"%{industry.strip()}%"))

    return list(
        db.scalars(statement.order_by(func.lower(Company.name), Company.id).offset(offset).limit(limit)).all()
    )


def get_company(db: Session, company_id: int) -> Company | None:
    return db.scalar(
        select(Company)
        .where(Company.id == company_id)
        .options(selectinload(Company.recruiters))
    )


def create_company(db: Session, payload: CompanyCreate, creator: User) -> Company:
    values = payload.model_dump()
    values["website"] = str(values["website"]) if values["website"] else None
    company = Company(**values, created_by_user_id=creator.id)
    db.add(company)
    db.commit()
    db.refresh(company)
    return get_company(db, company.id) or company


def update_company(db: Session, company: Company, payload: CompanyUpdate) -> Company:
    changes = payload.model_dump(exclude_unset=True)
    if "website" in changes and changes["website"] is not None:
        changes["website"] = str(changes["website"])
    for field, value in changes.items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return get_company(db, company.id) or company


def create_recruiter(db: Session, company: Company, payload: RecruiterCreate) -> User:
    recruiter = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.initial_password),
        role="recruiter",
        company_id=company.id,
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)
    return recruiter


def assign_recruiter(db: Session, company: Company, recruiter_user_id: int) -> User | None:
    recruiter = db.scalar(select(User).where(User.id == recruiter_user_id))
    if recruiter is None or recruiter.role != "recruiter":
        return None
    recruiter.company_id = company.id
    db.commit()
    db.refresh(recruiter)
    return recruiter
