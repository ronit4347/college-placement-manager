import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import router as auth_router
from app.api.routes.companies import router as companies_router
from app.api.routes.job_drives import router as job_drives_router
from app.api.routes import resume_analysis as analysis_route
from app.api.routes.resume_analysis import router as analysis_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Company, Student, User
from app.services import resume_analyzer


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", secrets.token_hex(32))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    def override_db():
        with factory() as db:
            yield db
    app = FastAPI()
    for router in (auth_router, companies_router, job_drives_router, analysis_router):
        app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = override_db
    app.state.session_factory = factory
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_mock_analyzer_returns_structured_skill_match():
    import asyncio
    result = asyncio.run(resume_analyzer.MockResumeAnalyzer().analyze(
        "Built Python APIs and studied computer science", "Engineer",
        "Computer science degree and software engineering role", ["Python", "SQL"],
    ))
    assert result.analysis_mode == "MOCK"
    assert result.overall_match_percentage == 50
    assert result.matching_skills == ["Python"]
    assert result.missing_skills == ["SQL"]
    assert result.improvement_suggestions


def test_personal_identifiers_are_removed_before_provider_call():
    cleaned = resume_analyzer.minimize_personal_data("Alex Student alex@school.edu +1 555-111-2222 skills", "Alex Student", "alex@school.edu", "+1 555-111-2222")
    assert "Alex Student" not in cleaned
    assert "alex@school.edu" not in cleaned
    assert "555-111-2222" not in cleaned
    assert "skills" in cleaned


def test_bad_pdf_extraction_is_a_controlled_failure(tmp_path):
    from app.services.resume_analyzer import ResumeExtractionError
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a pdf")
    with pytest.raises(ResumeExtractionError):
        resume_analyzer.extract_resume_text(bad)


def test_provider_malformed_response_is_controlled(monkeypatch):
    import asyncio
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "{not-json"}}]}
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr(resume_analyzer.httpx, "AsyncClient", FakeClient)
    with pytest.raises(resume_analyzer.MalformedAIResponse):
        asyncio.run(resume_analyzer.OpenAIResumeAnalyzer("test", "model", 2).analyze("resume", "role", "description", []))


def test_provider_failure_is_controlled(monkeypatch):
    import asyncio
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): raise resume_analyzer.httpx.ConnectError("secret network detail")
    monkeypatch.setattr(resume_analyzer.httpx, "AsyncClient", FakeClient)
    with pytest.raises(resume_analyzer.AIProviderError):
        asyncio.run(resume_analyzer.OpenAIResumeAnalyzer("test", "model", 2).analyze("resume", "role", "description", []))


def setup_student_and_drive(client, with_resume=True):
    reg = client.post("/api/auth/register", json={"email":"student@example.edu", "full_name":"Jamie Student", "password":"Strong-student-password-123"})
    token = client.post("/api/auth/login", json={"email":"student@example.edu", "password":"Strong-student-password-123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    with client.app.state.session_factory.begin() as db:
        db.add(User(email="admin@example.edu", full_name="Admin", password_hash=hash_password("Strong-admin-password-123"), role="admin"))
    admin_token = client.post("/api/auth/login", json={"email":"admin@example.edu", "password":"Strong-admin-password-123"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    company = client.post("/api/companies", headers=admin_headers, json={"name":"Northstar Systems"}).json()
    drive = client.post("/api/job-drives", headers=admin_headers, json={
        "company_id": company["id"], "title":"Software Engineer", "description":"Build APIs and services with a product team.",
        "required_skills":["Python", "SQL"], "application_deadline":(datetime.now(timezone.utc)+timedelta(days=4)).isoformat()
    }).json()
    client.post(f"/api/job-drives/{drive['id']}/publish", headers=admin_headers)
    if with_resume:
        with client.app.state.session_factory.begin() as db:
            student = db.scalar(select(Student).join(User).where(User.email == "student@example.edu"))
            student.resume_url = "resume.pdf"
        path = settings.resume_upload_dir
        if not path.is_absolute():
            from app.services.resume_storage import get_resume_directory
            path = get_resume_directory()
        path.mkdir(parents=True, exist_ok=True)
        (path / "resume.pdf").write_bytes(b"%PDF-test")
    return headers, drive["id"]


def test_analysis_endpoint_returns_decision_support_only(client, monkeypatch):
    headers, drive_id = setup_student_and_drive(client)
    monkeypatch.setattr(analysis_route, "extract_resume_text", lambda _path: "Jamie Student jamie@example.edu Python API developer")
    response = client.post("/api/students/me/resume-analysis", headers=headers, json={"job_drive_id": drive_id})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["analysis_mode"] == "MOCK"
    assert data["matching_skills"] == ["Python"]
    assert "SQL" in data["missing_skills"]
    assert "selected" not in str(data).lower()


def test_analysis_requires_student_role_and_resume(client):
    headers, drive_id = setup_student_and_drive(client, with_resume=False)
    denied = client.post("/api/students/me/resume-analysis", headers={"Authorization":"Bearer invalid"}, json={"job_drive_id":drive_id})
    assert denied.status_code == 401
    assert client.post("/api/students/me/resume-analysis", headers=headers, json={"job_drive_id":drive_id}).status_code == 404


def test_ai_failure_and_malformed_result_return_safe_503(client, monkeypatch):
    headers, drive_id = setup_student_and_drive(client)
    monkeypatch.setattr(analysis_route, "extract_resume_text", lambda _path: "Python developer")
    async def unavailable(*args): raise resume_analyzer.AIProviderError("AI analysis is temporarily unavailable. Please try again later.")
    monkeypatch.setattr(analysis_route, "get_resume_analyzer", lambda: type("Provider", (), {"analyze": unavailable})())
    response = client.post("/api/students/me/resume-analysis", headers=headers, json={"job_drive_id":drive_id})
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
    async def malformed(*args): raise resume_analyzer.MalformedAIResponse("AI analysis returned an invalid response. Please try again later.")
    monkeypatch.setattr(analysis_route, "get_resume_analyzer", lambda: type("Provider", (), {"analyze": malformed})())
    response = client.post("/api/students/me/resume-analysis", headers=headers, json={"job_drive_id":drive_id})
    assert response.status_code == 503
    assert "invalid response" in response.json()["detail"]
