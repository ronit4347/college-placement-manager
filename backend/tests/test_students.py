import secrets
import stat

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import router as auth_router
from app.api.routes.students import router as students_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import User


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr(settings, "jwt_secret_key", secrets.token_hex(32))
    monkeypatch.setattr(settings, "resume_upload_dir", tmp_path / "resumes")
    monkeypatch.setattr(settings, "max_resume_size_bytes", 5 * 1024 * 1024)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with test_session_factory() as db:
            yield db

    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/api")
    test_app.include_router(students_router, prefix="/api")
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.state.session_factory = test_session_factory

    with TestClient(test_app) as test_client:
        yield test_client

    Base.metadata.drop_all(engine)
    engine.dispose()


def register_and_login(client: TestClient, email: str) -> str:
    created = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Taylor Student", "password": "A-strong-password-123"},
    )
    assert created.status_code == 201, created.text
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "A-strong-password-123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def add_admin(client: TestClient) -> str:
    with client.app.state.session_factory.begin() as db:
        db.add(
            User(
                email="placement-admin@example.edu",
                full_name="Placement Admin",
                password_hash=hash_password("An-admin-password-123"),
                role="admin",
            )
        )
    response = client.post(
        "/api/auth/login",
        json={"email": "placement-admin@example.edu", "password": "An-admin-password-123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_student_profile_edit_is_scoped_to_current_user(client: TestClient):
    first_token = register_and_login(client, "first@example.edu")
    second_token = register_and_login(client, "second@example.edu")

    updated = client.patch(
        "/api/students/me",
        headers=auth(first_token),
        json={"full_name": "Taylor A. Student", "phone": "+1 (555) 123-4567", "roll_number": "cs-001", "branch": "Computer Science", "cgpa": 8.75, "graduation_year": 2027, "backlogs": 0},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["roll_number"] == "CS-001"
    student_id = updated.json()["student_id"]
    assert client.patch(f"/api/students/{student_id}", headers=auth(first_token), json={"branch": "Physics"}).status_code == 403

    own_profile = client.get("/api/students/me", headers=auth(second_token))
    assert own_profile.status_code == 200
    assert own_profile.json()["email"] == "second@example.edu"
    assert own_profile.json()["roll_number"] is None
    assert client.get("/api/students", headers=auth(first_token)).status_code == 403


def test_profile_validation_and_unique_roll_number(client: TestClient):
    first_token = register_and_login(client, "first@example.edu")
    second_token = register_and_login(client, "second@example.edu")
    invalid_cgpa = client.patch("/api/students/me", headers=auth(first_token), json={"cgpa": 11})
    invalid_backlogs = client.patch("/api/students/me", headers=auth(first_token), json={"backlogs": -1})
    invalid_phone = client.patch("/api/students/me", headers=auth(first_token), json={"phone": "not-a-phone"})
    assert invalid_cgpa.status_code == 422
    assert invalid_backlogs.status_code == 422
    assert invalid_phone.status_code == 422

    first = client.patch("/api/students/me", headers=auth(first_token), json={"roll_number": "ENG-22"})
    second = client.patch("/api/students/me", headers=auth(second_token), json={"roll_number": "ENG-22"})
    assert first.status_code == 200
    assert second.status_code == 409


def test_student_can_replace_skills_and_reject_duplicate_skills(client: TestClient):
    token = register_and_login(client, "student@example.edu")
    response = client.put("/api/students/me/skills", headers=auth(token), json={"skills": ["Python", "SQL"]})
    assert response.status_code == 200
    assert response.json()["skills"] == ["Python", "SQL"]

    duplicate = client.put("/api/students/me/skills", headers=auth(token), json={"skills": ["Python", "python"]})
    assert duplicate.status_code == 422


def test_resume_upload_checks_pdf_type_size_and_allows_download(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    token = register_and_login(client, "student@example.edu")
    invalid_type = client.post(
        "/api/students/me/resume",
        headers=auth(token),
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )
    assert invalid_type.status_code == 415
    invalid_signature = client.post(
        "/api/students/me/resume",
        headers=auth(token),
        files={"file": ("resume.pdf", b"not actually a PDF", "application/pdf")},
    )
    assert invalid_signature.status_code == 415

    uploaded = client.post(
        "/api/students/me/resume",
        headers=auth(token),
        files={"file": ("resume.pdf", b"%PDF-1.4\nresume-content", "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["resume_filename"].endswith(".pdf")
    resume_dir = settings.resume_upload_dir
    resume_path = resume_dir / uploaded.json()["resume_filename"]
    assert stat.S_IMODE(resume_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(resume_path.stat().st_mode) == 0o600
    downloaded = client.get("/api/students/me/resume", headers=auth(token))
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF-")

    another_student = register_and_login(client, "another@example.edu")
    assert client.get("/api/students/me/resume", headers=auth(another_student)).status_code == 404

    monkeypatch.setattr(settings, "max_resume_size_bytes", 32)
    oversized = client.post(
        "/api/students/me/resume",
        headers=auth(token),
        files={"file": ("large.pdf", b"%PDF-" + b"x" * 64, "application/pdf")},
    )
    assert oversized.status_code == 413


def test_admin_can_create_update_list_and_deactivate_students(client: TestClient):
    admin_token = add_admin(client)
    created = client.post(
        "/api/students",
        headers=auth(admin_token),
        json={
            "full_name": "Jamie Candidate",
            "email": "jamie@example.edu",
            "initial_password": "Initial-password-123",
            "roll_number": "MATH-100",
            "branch": "Mathematics",
            "cgpa": 9.1,
            "graduation_year": 2028,
            "skills": ["Python"],
        },
    )
    assert created.status_code == 201, created.text
    student_id = created.json()["student_id"]

    updated = client.patch(
        f"/api/students/{student_id}",
        headers=auth(admin_token),
        json={"branch": "Applied Mathematics"},
    )
    assert updated.status_code == 200
    assert updated.json()["branch"] == "Applied Mathematics"
    assert len(client.get("/api/students", headers=auth(admin_token)).json()) == 1

    deleted = client.delete(f"/api/students/{student_id}", headers=auth(admin_token))
    assert deleted.status_code == 204
    assert client.get("/api/students", headers=auth(admin_token)).json() == []


def test_admin_student_directory_filters_and_paginates(client: TestClient):
    admin = add_admin(client)
    profiles = [
        ("ada@example.edu", "Ada Lovelace", "CS-01", "Computer Science", 9.2),
        ("grace@example.edu", "Grace Hopper", "IT-02", "Information Technology", 8.1),
    ]
    for email, name, roll, branch, cgpa in profiles:
        token = register_and_login(client, email)
        updated = client.patch("/api/students/me", headers=auth(token), json={
            "full_name": name, "roll_number": roll, "branch": branch, "cgpa": cgpa,
        })
        assert updated.status_code == 200, updated.text
    headers = auth(admin)
    found = client.get("/api/students?q=ada&roll_number=CS&branch=computer&min_cgpa=9&placement_status=NOT_APPLIED", headers=headers)
    assert found.status_code == 200, found.text
    assert len(found.json()) == 1
    assert found.json()[0]["placement_status"] == "NOT_APPLIED"
    assert found.json()[0]["roll_number"] == "CS-01"
    assert client.get("/api/students?min_cgpa=9&max_cgpa=8", headers=headers).status_code == 422
    first_page = client.get("/api/students?limit=1&offset=0", headers=headers).json()
    second_page = client.get("/api/students?limit=1&offset=1", headers=headers).json()
    assert len(first_page) == len(second_page) == 1
    assert first_page[0]["student_id"] != second_page[0]["student_id"]
