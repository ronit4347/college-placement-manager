from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models import User
from app.schemas.analytics import AnalyticsFiltersResponse, DashboardAnalyticsResponse
from app.services.analytics import dashboard_analytics, filter_options

router = APIRouter(prefix="/admin/analytics", tags=["admin analytics"])
admin_only = require_roles("ADMIN")


@router.get("/filters", response_model=AnalyticsFiltersResponse)
def analytics_filter_options(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return filter_options(db)


@router.get("/dashboard", response_model=DashboardAnalyticsResponse)
def admin_dashboard(
    graduation_year: int | None = Query(default=None, ge=2000, le=2200),
    branch: str | None = Query(default=None, min_length=1, max_length=120),
    company_id: int | None = Query(default=None, gt=0),
    date_from: date | None = None,
    date_to: date | None = None,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    try:
        return dashboard_analytics(
            db,
            graduation_year=graduation_year,
            branch=branch,
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
