from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import Company, User
from app.schemas.companies import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    RecruiterCreate,
    RecruiterSummary,
)
from app.services.companies import (
    assign_recruiter,
    create_company,
    create_recruiter,
    get_company,
    list_companies,
    update_company,
)

router = APIRouter(prefix="/companies", tags=["companies"])
admin_only = require_roles("ADMIN")


def company_response(company: Company) -> CompanyResponse:
    recruiters = sorted(company.recruiters, key=lambda recruiter: recruiter.full_name.casefold())
    return CompanyResponse(
        id=company.id,
        name=company.name,
        industry=company.industry,
        location=company.location,
        website=company.website,
        hr_name=company.hr_name,
        hr_email=company.hr_email,
        description=company.description,
        is_active=company.is_active,
        recruiters=[
            RecruiterSummary(
                user_id=recruiter.id,
                full_name=recruiter.full_name,
                email=recruiter.email,
                is_active=recruiter.is_active,
            )
            for recruiter in recruiters
        ],
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def _handle_integrity_error(db: Session, error: IntegrityError) -> HTTPException:
    db.rollback()
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A company with that name or an account with that email already exists.",
    )


@router.get("", response_model=list[CompanyResponse])
def search_companies(
    q: str | None = Query(default=None, max_length=120),
    name: str | None = Query(default=None, max_length=120),
    industry: str | None = Query(default=None, max_length=120),
    is_active: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> list[CompanyResponse]:
    companies = list_companies(
        db,
        q=q,
        name=name,
        industry=industry,
        is_active=is_active,
        limit=limit,
        offset=offset,
        current_user=admin,
    )
    return [company_response(company) for company in companies]


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def add_company(
    payload: CompanyCreate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    try:
        return company_response(create_company(db, payload, admin))
    except IntegrityError as error:
        raise _handle_integrity_error(db, error) from None


@router.get("/{company_id}", response_model=CompanyResponse)
def company_details(
    company_id: int,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    return company_response(company)


@router.patch("/{company_id}", response_model=CompanyResponse)
def edit_company(
    company_id: int,
    payload: CompanyUpdate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    try:
        return company_response(update_company(db, company, payload))
    except IntegrityError as error:
        raise _handle_integrity_error(db, error) from None


@router.post("/{company_id}/recruiters", response_model=RecruiterSummary, status_code=status.HTTP_201_CREATED)
def add_recruiter(
    company_id: int,
    payload: RecruiterCreate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> RecruiterSummary:
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    if not company.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recruiters can only be added to active companies.")
    try:
        recruiter = create_recruiter(db, company, payload)
    except IntegrityError as error:
        raise _handle_integrity_error(db, error) from None
    return RecruiterSummary(user_id=recruiter.id, full_name=recruiter.full_name, email=recruiter.email, is_active=recruiter.is_active)


@router.put("/{company_id}/recruiters/{recruiter_user_id}", response_model=RecruiterSummary)
def move_recruiter_to_company(
    company_id: int,
    recruiter_user_id: int,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> RecruiterSummary:
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    if not company.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recruiters can only be assigned to active companies.")
    try:
        recruiter = assign_recruiter(db, company, recruiter_user_id)
    except IntegrityError as error:
        raise _handle_integrity_error(db, error) from None
    if recruiter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recruiter account not found.")
    return RecruiterSummary(user_id=recruiter.id, full_name=recruiter.full_name, email=recruiter.email, is_active=recruiter.is_active)
