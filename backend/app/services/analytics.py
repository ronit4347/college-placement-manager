from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import distinct, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationStatusEvent,
    Company,
    Interview,
    JobDrive,
    Offer,
    Student,
)
from app.schemas.analytics import (
    AnalyticsFiltersResponse,
    ChartDatum,
    CompanyFilterOption,
    DashboardAnalyticsResponse,
    DashboardMetrics,
    FunnelDatum,
    MonthlyDatum,
)


def filter_options(db: Session) -> AnalyticsFiltersResponse:
    years = db.scalars(select(Student.graduation_year).distinct().where(Student.graduation_year.is_not(None)).order_by(Student.graduation_year)).all()
    branches = db.scalars(select(Student.branch).distinct().where(Student.branch.is_not(None), Student.branch != "").order_by(Student.branch)).all()
    companies = db.scalars(select(Company).order_by(Company.name)).all()
    return AnalyticsFiltersResponse(
        graduation_years=[int(year) for year in years],
        branches=[str(branch) for branch in branches],
        companies=[CompanyFilterOption(id=company.id, name=company.name) for company in companies],
    )


def _application_ids(db: Session, graduation_year: int | None, branch: str | None,
                     company_id: int | None, date_from: date | None, date_to: date | None):
    query = select(Application.id).join(Application.student).join(Application.job_drive)
    if graduation_year is not None:
        query = query.where(Student.graduation_year == graduation_year)
    if branch:
        query = query.where(func.lower(Student.branch) == branch.lower())
    if company_id is not None:
        query = query.where(JobDrive.company_id == company_id)
    if date_from is not None:
        query = query.where(Application.applied_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to is not None:
        next_day = date_to + timedelta(days=1)
        query = query.where(Application.applied_at < datetime.combine(next_day, time.min, tzinfo=timezone.utc))
    return query.subquery()


def _count(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


def dashboard_analytics(db: Session, *, graduation_year: int | None = None, branch: str | None = None,
                        company_id: int | None = None, date_from: date | None = None,
                        date_to: date | None = None) -> DashboardAnalyticsResponse:
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from cannot be after date_to.")

    app_ids = _application_ids(db, graduation_year, branch, company_id, date_from, date_to)
    id_filter = Application.id.in_(select(app_ids.c.id))
    cohort = select(Student.id)
    if graduation_year is not None:
        cohort = cohort.where(Student.graduation_year == graduation_year)
    if branch:
        cohort = cohort.where(func.lower(Student.branch) == branch.lower())
    total_students = _count(db, select(func.count()).select_from(cohort.subquery()))
    companies_query = select(func.count(Company.id))
    if company_id is not None:
        companies_query = companies_query.where(Company.id == company_id)
    total_companies = _count(db, companies_query)

    now = datetime.now(timezone.utc)
    active_drives_query = select(func.count(JobDrive.id)).where(JobDrive.status == "published")
    if company_id is not None:
        active_drives_query = active_drives_query.where(JobDrive.company_id == company_id)
    active_drives_query = active_drives_query.where(JobDrive.application_deadline > now)
    active_drives = _count(db, active_drives_query)
    total_applications = _count(db, select(func.count(distinct(Application.id))).where(id_filter))

    shortlisted_condition = or_(
        Application.status.in_(["shortlisted", "interview", "selected", "offered", "joined"]),
        exists(select(ApplicationStatusEvent.id).where(
            ApplicationStatusEvent.application_id == Application.id,
            ApplicationStatusEvent.to_status == "shortlisted",
        )),
    )
    interview_condition = or_(
        Application.status.in_(["interview", "selected", "offered", "joined"]),
        exists(select(Interview.id).where(Interview.application_id == Application.id, Interview.status != "cancelled")),
        exists(select(ApplicationStatusEvent.id).where(
            ApplicationStatusEvent.application_id == Application.id,
            ApplicationStatusEvent.to_status == "interview",
        )),
    )
    selected_condition = Application.status.in_(["selected", "offered", "joined"])
    placed_condition = or_(
        Application.status == "joined",
        exists(select(ApplicationStatusEvent.id).where(
            ApplicationStatusEvent.application_id == Application.id,
            ApplicationStatusEvent.to_status == "joined",
        )),
    )

    def count_stage(condition) -> int:
        return _count(db, select(func.count(distinct(Application.id))).where(id_filter, condition))

    shortlisted = count_stage(shortlisted_condition)
    interviews_count = _count(db, select(func.count(Interview.id)).where(
        Interview.application_id.in_(select(app_ids.c.id)), Interview.status != "cancelled"))
    interviewed_candidates = count_stage(interview_condition)
    selected = count_stage(selected_condition)
    offers_query = select(func.count(Offer.id)).join(Offer.application).where(
        Application.id.in_(select(app_ids.c.id)), Offer.status != "draft")
    offers_count = _count(db, offers_query)
    applications_with_offers = _count(db, select(func.count(distinct(Offer.application_id)))
        .join(Offer.application).where(Application.id.in_(select(app_ids.c.id)), Offer.status != "draft"))
    placements = _count(db, select(func.count(distinct(Application.student_id))).where(id_filter, placed_condition))
    placement_rate = round((placements / total_students * 100), 1) if total_students else 0.0

    branch_rows = db.execute(
        select(Student.branch, func.count(distinct(Application.student_id)))
        .join(Application, Application.student_id == Student.id)
        .where(id_filter, placed_condition)
        .group_by(Student.branch)
        .order_by(func.count(distinct(Application.student_id)).desc(), Student.branch)
    ).all()
    placement_by_branch = [ChartDatum(name=branch_name or "Not specified", value=int(count)) for branch_name, count in branch_rows]

    funnel = [
        FunnelDatum(stage="Applied", count=total_applications),
        FunnelDatum(stage="Shortlisted", count=shortlisted),
        FunnelDatum(stage="Interviewed", count=interviewed_candidates),
        FunnelDatum(stage="Selected", count=selected),
        FunnelDatum(stage="Offers issued", count=applications_with_offers),
        FunnelDatum(stage="Placed", count=placements),
    ]

    company_rows = db.execute(
        select(Company.name, func.count(distinct(Application.id)))
        .join(JobDrive, JobDrive.company_id == Company.id)
        .join(Application, Application.job_drive_id == JobDrive.id)
        .where(id_filter, selected_condition)
        .group_by(Company.id, Company.name)
        .order_by(func.count(distinct(Application.id)).desc(), Company.name)
        .limit(10)
    ).all()
    company_selections = [ChartDatum(name=name, value=int(count)) for name, count in company_rows]

    salary_rows = db.scalars(
        select(Offer.salary).join(Offer.application)
        .where(Application.id.in_(select(app_ids.c.id)), Offer.status != "draft", Offer.salary.is_not(None), Offer.currency == "INR")
    ).all()
    salary_bands = ((0, 500_000, "Under ₹5L"), (500_000, 1_000_000, "₹5L–₹10L"),
                    (1_000_000, 1_500_000, "₹10L–₹15L"), (1_500_000, 2_500_000, "₹15L–₹25L"),
                    (2_500_000, None, "₹25L+"))
    package_distribution = [ChartDatum(name=label, value=sum(1 for salary in salary_rows
        if salary >= lower and (upper is None or salary < upper))) for lower, upper, label in salary_bands]

    current_month = date(now.year, now.month, 1)
    months: list[date] = []
    cursor = current_month
    for _ in range(12):
        months.append(cursor)
        cursor = date(cursor.year - 1, 12, 1) if cursor.month == 1 else date(cursor.year, cursor.month - 1, 1)
    months.reverse()
    window_start = datetime.combine(months[0], time.min, tzinfo=timezone.utc)
    window_end_month = date(current_month.year + 1, 1, 1) if current_month.month == 12 else date(current_month.year, current_month.month + 1, 1)
    monthly_events = db.execute(
        select(ApplicationStatusEvent.created_at)
        .join(Application, Application.id == ApplicationStatusEvent.application_id)
        .where(id_filter, ApplicationStatusEvent.to_status == "joined",
               ApplicationStatusEvent.created_at >= window_start,
               ApplicationStatusEvent.created_at < datetime.combine(window_end_month, time.min, tzinfo=timezone.utc))
    ).scalars().all()
    monthly_counts: Counter[tuple[int, int]] = Counter()
    for occurred_at in monthly_events:
        monthly_counts[(occurred_at.year, occurred_at.month)] += 1
    monthly_activity = [MonthlyDatum(month=month.strftime("%b %Y"), placements=monthly_counts[(month.year, month.month)]) for month in months]

    return DashboardAnalyticsResponse(
        generated_at=now,
        metrics=DashboardMetrics(
            total_students=total_students, total_companies=total_companies,
            active_job_drives=active_drives, total_applications=total_applications,
            shortlisted_candidates=shortlisted, interviews=interviews_count,
            selected_candidates=selected, offers=offers_count, placements=placements,
            placement_rate=placement_rate,
        ),
        placement_by_branch=placement_by_branch,
        application_funnel=funnel,
        company_selections=company_selections,
        package_distribution=package_distribution,
        monthly_placement_activity=monthly_activity,
    )
