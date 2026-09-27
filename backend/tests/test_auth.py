import secrets

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import require_roles
from app.api.routes.auth import router as auth_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.students import router as students_router
from app.core.config import settings
from app.core.errors import install_security_error_handlers
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Company, User


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "jwt_secret_key", secrets.token_hex(32))
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
    install_security_error_handlers(test_app)
    test_app.include_router(auth_router, prefix="/api")
    test_app.include_router(admin_users_router, prefix="/api")
    test_app.include_router(students_router, prefix="/api")
    authorization_routes = APIRouter(prefix="/api")

    @authorization_routes.get("/admin-only")
    def admin_only(_: User = Depends(require_roles("ADMIN"))):
        return {"allowed": True}

    test_app.include_router(authorization_routes)
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.state.session_factory = test_session_factory

    with TestClient(test_app) as test_client:
        yield test_client

    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client: TestClient, email: str = "student@example.edu") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "  Ada   Student ", "password": "A-strong-password-123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_registration_hashes_password_and_assigns_student_role(client: TestClient):
    created = register(client)

    assert created["role"] == "STUDENT"
    assert created["full_name"] == "Ada Student"
    assert "password" not in created
    assert "password_hash" not in created

    with client.app.state.session_factory() as db:
        user = db.query(User).filter_by(email="student@example.edu").one()
        assert user.password_hash != "A-strong-password-123"
        assert user.password_hash.startswith("$argon2")
        assert user.role == "student"
        assert user.student is not None


def test_duplicate_registration_is_rejected_case_insensitively(client: TestClient):
    register(client, "Student@Example.edu")

    duplicate = client.post(
        "/api/auth/register",
        json={"email": "student@example.edu", "full_name": "Another Student", "password": "A-strong-password-123"},
    )

    assert duplicate.status_code == 409


@pytest.mark.parametrize("role", ["ADMIN", "INTERVIEWER", "RECRUITER"])
def test_public_registration_cannot_choose_a_privileged_role(client: TestClient, role: str):
    response = client.post(
        "/api/auth/register",
        json={"email": f"{role.lower()}@example.edu", "full_name": "Requested Privileged User", "password": "A-strong-password-123", "role": role},
    )

    assert response.status_code == 422
    with client.app.state.session_factory() as db:
        assert db.query(User).filter_by(email=f"{role.lower()}@example.edu").one_or_none() is None


def test_login_returns_jwt_and_current_user(client: TestClient):
    register(client)
    response = client.post(
        "/api/auth/login",
        json={"email": "STUDENT@example.edu", "password": "A-strong-password-123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"

    current_user = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "student@example.edu"
    assert current_user.json()["role"] == "STUDENT"


def test_invalid_password_is_rejected(client: TestClient):
    register(client)

    response = client.post(
        "/api/auth/login",
        json={"email": "student@example.edu", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_invalid_token_is_rejected(client: TestClient):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt"})

    assert response.status_code == 401


def test_validation_errors_never_reflect_submitted_password(client: TestClient):
    secret_value = "private-password-value-123"
    response = client.post("/api/auth/register", json={
        "email": "malformed@example.edu", "full_name": "Malformed User", "password": [secret_value],
    })
    assert response.status_code == 422
    assert secret_value not in response.text
    assert "password" in response.text


def test_missing_jwt_secret_returns_generic_server_error(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    register(client)
    monkeypatch.setattr(settings, "jwt_secret_key", None)
    response = client.post("/api/auth/login", json={
        "email": "student@example.edu", "password": "A-strong-password-123",
    })
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
    assert "JWT_SECRET_KEY" not in response.text


def test_role_authorization_blocks_students_and_allows_admins(client: TestClient):
    register(client)
    student_token = client.post(
        "/api/auth/login",
        json={"email": "student@example.edu", "password": "A-strong-password-123"},
    ).json()["access_token"]
    denied = client.get("/api/admin-only", headers={"Authorization": f"Bearer {student_token}"})
    assert denied.status_code == 403

    with client.app.state.session_factory.begin() as db:  # type: Session
        company = Company(name="RBAC Example Company")
        db.add(company)
        db.flush()
        db.add(
            User(
                email="admin@example.edu",
                full_name="Placement Admin",
                password_hash=hash_password("Another-strong-password-123"),
                role="admin",
            )
        )
        db.add_all([
            User(email="recruiter@example.edu", full_name="Approved Recruiter", password_hash=hash_password("Recruiter-strong-password-123"), role="recruiter", company_id=company.id),
            User(email="interviewer@example.edu", full_name="Approved Interviewer", password_hash=hash_password("Interviewer-strong-password-123"), role="interviewer"),
        ])
    admin_token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.edu", "password": "Another-strong-password-123"},
    ).json()["access_token"]
    allowed = client.get("/api/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
    assert allowed.status_code == 200

    recruiter_token = client.post("/api/auth/login", json={"email": "recruiter@example.edu", "password": "Recruiter-strong-password-123"}).json()["access_token"]
    interviewer_token = client.post("/api/auth/login", json={"email": "interviewer@example.edu", "password": "Interviewer-strong-password-123"}).json()["access_token"]
    for role, token in (("STUDENT", student_token), ("RECRUITER", recruiter_token), ("INTERVIEWER", interviewer_token)):
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/admin-only", headers=headers).status_code == 403, role
        assert client.get("/api/admin/interviewers", headers=headers).status_code == 403, role
        assert client.post("/api/admin/interviewers", headers=headers, json={
            "email": f"unauthorized-{role.lower()}@example.edu",
            "full_name": "Unauthorized User",
            "initial_password": "A-strong-password-123",
        }).status_code == 403, role


def test_student_profile_update_cannot_change_role(client: TestClient):
    register(client)
    token = client.post("/api/auth/login", json={"email": "student@example.edu", "password": "A-strong-password-123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch("/api/students/me", headers=headers, json={"role": "ADMIN", "branch": "Computer Science"})
    assert response.status_code == 422
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "STUDENT"


def test_admin_can_provision_manage_and_suspend_interviewers(client: TestClient):
    with client.app.state.session_factory.begin() as db:
        db.add(User(email="admin@example.edu", full_name="Placement Admin", password_hash=hash_password("Admin-strong-password-123"), role="admin"))
    admin_token = client.post("/api/auth/login", json={"email": "admin@example.edu", "password": "Admin-strong-password-123"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    role_escalation = client.post("/api/admin/interviewers", headers=admin_headers, json={
        "email": "not-an-admin@example.edu", "full_name": "Attempted Admin", "initial_password": "Interviewer-strong-password-123", "role": "ADMIN",
    })
    assert role_escalation.status_code == 422

    created = client.post("/api/admin/interviewers", headers=admin_headers, json={
        "email": "managed-interviewer@example.edu", "full_name": "  Taylor   Reviewer ", "initial_password": "Interviewer-strong-password-123",
    })
    assert created.status_code == 201, created.text
    interviewer = created.json()
    assert interviewer["role"] == "INTERVIEWER" and interviewer["full_name"] == "Taylor Reviewer"
    assert "password" not in interviewer and "password_hash" not in interviewer and "initial_password" not in interviewer
    assert client.post("/api/admin/interviewers", headers=admin_headers, json={
        "email": "managed-interviewer@example.edu", "full_name": "Taylor Reviewer", "initial_password": "Interviewer-strong-password-123",
    }).status_code == 409

    interviewer_token_response = client.post("/api/auth/login", json={"email": "managed-interviewer@example.edu", "password": "Interviewer-strong-password-123"})
    assert interviewer_token_response.status_code == 200
    interviewer_headers = {"Authorization": f"Bearer {interviewer_token_response.json()['access_token']}"}
    suspended = client.patch(f"/api/admin/interviewers/{interviewer['id']}/active", headers=admin_headers, json={"is_active": False})
    assert suspended.status_code == 200 and suspended.json()["is_active"] is False
    assert client.get("/api/auth/me", headers=interviewer_headers).status_code == 401
    assert client.post("/api/auth/login", json={"email": "managed-interviewer@example.edu", "password": "Interviewer-strong-password-123"}).status_code == 401
    reactivated = client.patch(f"/api/admin/interviewers/{interviewer['id']}/active", headers=admin_headers, json={"is_active": True})
    assert reactivated.status_code == 200 and reactivated.json()["is_active"] is True
    assert client.post("/api/auth/login", json={"email": "managed-interviewer@example.edu", "password": "Interviewer-strong-password-123"}).status_code == 200

    with client.app.state.session_factory() as db:
        user = db.query(User).filter_by(email="managed-interviewer@example.edu").one()
        assert user.role == "interviewer" and user.password_hash.startswith("$argon2")
