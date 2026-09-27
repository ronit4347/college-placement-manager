import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.api.routes.auth import router as auth_router
from app.api.routes.companies import router as companies_router
from app.api.routes.job_drives import router as job_drives_router
from app.api.routes.students import router as students_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Application, Company, Student, User


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "jwt_secret_key", secrets.token_hex(32))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with factory() as db:
            yield db

    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/api")
    test_app.include_router(companies_router, prefix="/api")
    test_app.include_router(job_drives_router, prefix="/api")
    test_app.include_router(students_router, prefix="/api")
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.state.session_factory = factory
    with TestClient(test_app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)
    engine.dispose()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def add_admin(client: TestClient) -> str:
    with client.app.state.session_factory.begin() as db:
        db.add(User(email="admin@example.edu", full_name="Placement Admin", password_hash=hash_password("Strong-admin-password-123"), role="admin"))
    return token_for(client, "admin@example.edu", "Strong-admin-password-123")


def add_student(client: TestClient) -> tuple[str, int]:
    response = client.post("/api/auth/register", json={"email": "student@example.edu", "full_name": "Jamie Student", "password": "Strong-student-password-123"})
    assert response.status_code == 201, response.text
    with client.app.state.session_factory() as db:
        student_id = db.scalar(select(Student.id).join(User).where(User.email == "student@example.edu"))
    return token_for(client, "student@example.edu", "Strong-student-password-123"), student_id


def add_company(client: TestClient, admin: str, name: str = "Northstar Systems") -> int:
    response = client.post("/api/companies", headers=auth(admin), json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def drive_payload(company_id: int, **updates) -> dict:
    payload = {
        "company_id": company_id,
        "title": "Graduate Software Engineer",
        "description": "Build reliable software products with a collaborative engineering team.",
        "package_min": 8.5,
        "package_max": 14,
        "location": "Bengaluru",
        "employment_type": "FULL_TIME",
        "min_cgpa": 7.0,
        "max_backlogs": 0,
        "allowed_branches": ["Computer Science", "Information Technology"],
        "graduation_year": 2027,
        "required_skills": ["Python", "SQL"],
        "application_deadline": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
    }
    payload.update(updates)
    return payload


def test_admin_create_edit_lifecycle_and_student_visibility(client: TestClient):
    admin = add_admin(client)
    student, _ = add_student(client)
    company_id = add_company(client, admin)

    forbidden = client.post("/api/job-drives", headers=auth(student), json=drive_payload(company_id))
    assert forbidden.status_code == 403
    created = client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id))
    assert created.status_code == 201, created.text
    drive = created.json()
    drive_id = drive["id"]
    assert drive["status"] == "DRAFT"
    assert drive["company_name"] == "Northstar Systems"
    assert drive["required_skills"] == ["Python", "SQL"]
    assert client.get("/api/job-drives", headers=auth(student)).json() == []
    assert client.get(f"/api/job-drives/{drive_id}", headers=auth(student)).status_code == 404

    edited = client.patch(f"/api/job-drives/{drive_id}", headers=auth(admin), json={"title": "Software Engineer I", "required_skills": ["Python", "PostgreSQL"]})
    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "Software Engineer I"
    assert edited.json()["required_skills"] == ["PostgreSQL", "Python"]

    published = client.post(f"/api/job-drives/{drive_id}/publish", headers=auth(admin))
    assert published.status_code == 200 and published.json()["status"] == "PUBLISHED"
    assert client.get("/api/job-drives?q=Software&location=ben&employment_type=FULL_TIME&graduation_year=2027", headers=auth(student)).json()[0]["id"] == drive_id
    assert client.get(f"/api/job-drives/{drive_id}", headers=auth(student)).status_code == 200
    assert client.get("/api/job-drives?eligibility=true", headers=auth(student)).json() == []
    student_profile = client.patch("/api/students/me", headers=auth(student), json={"cgpa": 8.4, "backlogs": 0, "branch": "Computer Science", "graduation_year": 2027})
    assert student_profile.status_code == 200
    assert client.put("/api/students/me/skills", headers=auth(student), json={"skills": ["Python", "PostgreSQL"]}).status_code == 200
    filtered = client.get("/api/job-drives?company=Northstar&location=Beng&package_min=10&eligibility=true&application_status=NOT_APPLIED&limit=1", headers=auth(student))
    assert filtered.status_code == 200, filtered.text
    assert len(filtered.json()) == 1 and filtered.json()[0]["is_eligible"] is True
    assert filtered.json()[0]["application_status"] is None
    assert client.post(f"/api/job-drives/{drive_id}/publish", headers=auth(admin)).status_code == 409
    assert client.post(f"/api/job-drives/{drive_id}/close", headers=auth(admin)).json()["status"] == "CLOSED"
    assert client.post(f"/api/job-drives/{drive_id}/cancel", headers=auth(admin)).status_code == 409
    assert client.patch(f"/api/job-drives/{drive_id}", headers=auth(admin), json={"title": "Closed role"}).status_code == 409
    assert client.get("/api/job-drives?status=DRAFT", headers=auth(admin)).json() == []


def test_drive_validation_deadline_and_cancel_lifecycle(client: TestClient):
    admin = add_admin(client)
    company_id = add_company(client, admin)
    assert client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id, min_cgpa=12)).status_code == 422
    assert client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id, max_backlogs=-1)).status_code == 422
    assert client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id, package_min=15, package_max=8)).status_code == 422
    assert client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id, required_skills=["Python", " python "])).status_code == 422
    assert client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id, employment_type="PERMANENT")).status_code == 422
    naive_deadline = (datetime.now(timezone.utc) + timedelta(days=3)).replace(tzinfo=None).isoformat()
    assert client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id, application_deadline=naive_deadline)).status_code == 422
    assert client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id, application_deadline=None)).status_code == 201

    expired = client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id, application_deadline=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat())).json()
    assert client.post(f"/api/job-drives/{expired['id']}/publish", headers=auth(admin)).status_code == 409
    assert client.post(f"/api/job-drives/{expired['id']}/cancel", headers=auth(admin)).json()["status"] == "CANCELLED"

    unpublished = client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id)).json()
    assert client.post(f"/api/job-drives/{unpublished['id']}/close", headers=auth(admin)).status_code == 409
    assert client.post(f"/api/job-drives/{unpublished['id']}/publish", headers=auth(admin)).status_code == 200


def test_recruiters_are_scoped_and_admin_can_view_applicants(client: TestClient):
    admin = add_admin(client)
    company_id = add_company(client, admin, "Northstar")
    another_company_id = add_company(client, admin, "Lumen")
    first_drive = client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id)).json()
    second_drive = client.post("/api/job-drives", headers=auth(admin), json=drive_payload(another_company_id, title="Data Engineer")).json()
    with client.app.state.session_factory.begin() as db:
        recruiter = User(email="recruiter@example.edu", full_name="Company Recruiter", password_hash=hash_password("Strong-recruiter-password-123"), role="recruiter", company_id=company_id)
        db.add(recruiter)
    recruiter_token = token_for(client, "recruiter@example.edu", "Strong-recruiter-password-123")
    assert [drive["id"] for drive in client.get("/api/job-drives", headers=auth(recruiter_token)).json()] == [first_drive["id"]]
    assert client.get(f"/api/job-drives/{second_drive['id']}", headers=auth(recruiter_token)).status_code == 404
    assert client.post(f"/api/job-drives/{first_drive['id']}/publish", headers=auth(recruiter_token)).status_code == 403

    assert client.get(f"/api/job-drives/{first_drive['id']}/applicants", headers=auth(recruiter_token)).status_code == 403
    assert client.get(f"/api/job-drives/{first_drive['id']}/applicants", headers=auth(admin)).json() == []

    student_token, student_id = add_student(client)
    with client.app.state.session_factory.begin() as db:
        db.add(Application(student_id=student_id, job_drive_id=first_drive["id"], status="applied"))
    applicants = client.get(f"/api/job-drives/{first_drive['id']}/applicants", headers=auth(admin))
    assert applicants.status_code == 200
    assert applicants.json()[0]["email"] == "student@example.edu"
    assert client.get(f"/api/job-drives/{first_drive['id']}/applicants", headers=auth(student_token)).status_code == 403


def test_inactive_company_cannot_receive_or_publish_a_drive(client: TestClient):
    admin = add_admin(client)
    company_id = add_company(client, admin)
    client.patch(f"/api/companies/{company_id}", headers=auth(admin), json={"is_active": False})
    assert client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id)).status_code == 409
    with client.app.state.session_factory.begin() as db:
        company = db.get(Company, company_id)
        company.is_active = True
    created = client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id)).json()
    client.patch(f"/api/companies/{company_id}", headers=auth(admin), json={"is_active": False})
    assert client.post(f"/api/job-drives/{created['id']}/publish", headers=auth(admin)).status_code == 409


def test_student_eligibility_endpoint_uses_saved_profile_and_is_student_only(client: TestClient):
    admin = add_admin(client)
    student_token, _ = add_student(client)
    company_id = add_company(client, admin)
    drive = client.post("/api/job-drives", headers=auth(admin), json=drive_payload(company_id)).json()
    endpoint = f"/api/job-drives/{drive['id']}/eligibility"
    assert client.get(endpoint, headers=auth(student_token)).status_code == 404
    assert client.get(endpoint, headers=auth(admin)).status_code == 403

    assert client.post(f"/api/job-drives/{drive['id']}/publish", headers=auth(admin)).status_code == 200
    result = client.get(endpoint, headers=auth(student_token))
    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert "Student CGPA is missing." in result.json()["reasons"]
    assert any("Student skills are missing" in reason for reason in result.json()["reasons"])

    profile = client.patch(
        "/api/students/me",
        headers=auth(student_token),
        json={"cgpa": 8.2, "backlogs": 0, "branch": "Computer Science", "graduation_year": 2027},
    )
    assert profile.status_code == 200, profile.text
    skills = client.put("/api/students/me/skills", headers=auth(student_token), json={"skills": ["Python", "SQL"]})
    assert skills.status_code == 200, skills.text
    eligible = client.get(endpoint, headers=auth(student_token))
    assert eligible.json() == {"eligible": True, "reasons": []}
