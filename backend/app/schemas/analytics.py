from datetime import datetime

from pydantic import BaseModel


class CompanyFilterOption(BaseModel):
    id: int
    name: str


class AnalyticsFiltersResponse(BaseModel):
    graduation_years: list[int]
    branches: list[str]
    companies: list[CompanyFilterOption]


class DashboardMetrics(BaseModel):
    total_students: int
    total_companies: int
    active_job_drives: int
    total_applications: int
    shortlisted_candidates: int
    interviews: int
    selected_candidates: int
    offers: int
    placements: int
    placement_rate: float


class ChartDatum(BaseModel):
    name: str
    value: int | float


class FunnelDatum(BaseModel):
    stage: str
    count: int


class MonthlyDatum(BaseModel):
    month: str
    placements: int


class DashboardAnalyticsResponse(BaseModel):
    generated_at: datetime
    metrics: DashboardMetrics
    placement_by_branch: list[ChartDatum]
    application_funnel: list[FunnelDatum]
    company_selections: list[ChartDatum]
    package_distribution: list[ChartDatum]
    monthly_placement_activity: list[MonthlyDatum]
