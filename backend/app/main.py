from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.errors import UploadBodyLimitMiddleware, install_security_error_handlers

from app.core.config import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.applications import router as applications_router, submission_router as application_submission_router
from app.api.routes.companies import router as companies_router
from app.api.routes.health import router as health_router
from app.api.routes.job_drives import router as job_drives_router
from app.api.routes.students import router as students_router
from app.api.routes.interviews import router as interviews_router
from app.api.routes.offers import router as offers_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.resume_analysis import router as resume_analysis_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.admin_users import router as admin_users_router

app = FastAPI(title="College Placement Manager API", version="0.1.0")
install_security_error_handlers(app)

app.add_middleware(
    UploadBodyLimitMiddleware,
    max_file_size_bytes=settings.max_resume_size_bytes,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(students_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
app.include_router(job_drives_router, prefix="/api")
app.include_router(applications_router, prefix="/api")
app.include_router(application_submission_router, prefix="/api")
app.include_router(interviews_router, prefix="/api")
app.include_router(offers_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(resume_analysis_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(admin_users_router, prefix="/api")
