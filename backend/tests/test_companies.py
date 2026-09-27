import secrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import router as auth_router
from app.api.routes.companies import router as companies_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import User


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
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.state.session_factory = factory
    with TestClient(test_app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_admin(client: TestClient) -> str:
    with client.app.state.session_factory.begin() as db:
        db.add(User(email="admin@example.edu", full_name="Placement Admin", password_hash=hash_password("Strong-admin-password-123"), role="admin"))
    response = client.post("/api/auth/login", json={"email": "admin@example.edu", "password": "Strong-admin-password-123"})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def add_student(client: TestClient) -> str:
    response = client.post("/api/auth/register", json={"email": "student@example.edu", "full_name": "Test Student", "password": "Strong-student-password-123"})
    assert response.status_code == 201, response.text
    response = client.post("/api/auth/login", json={"email": "student@example.edu", "password": "Strong-student-password-123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def company_payload(name: str = "Northstar Systems") -> dict[str, str]:
    return {"name": name, "industry": "Technology", "location": "Pune, India", "website": "https://northstar.example", "hr_name": "Morgan Lee", "hr_email": "MORGAN@NORTHSTAR.EXAMPLE", "description": "A software engineering employer."}


def test_admin_company_crud_search_filters_and_status(client: TestClient):
    admin = add_admin(client)
    student = add_student(client)
    assert client.post("/api/companies", headers=auth(student), json=company_payload()).status_code == 403
    created = client.post("/api/companies", headers=auth(admin), json=company_payload())
    assert created.status_code == 201, created.text
    assert created.json()["hr_email"] == "morgan@northstar.example"
    company_id = created.json()["id"]
    assert client.get(f"/api/companies/{company_id}", headers=auth(student)).status_code == 403
    assert client.get("/api/companies?q=northstar&industry=technology&is_active=true", headers=auth(admin)).json()[0]["id"] == company_id
    assert client.get("/api/companies?name=northstar&industry=tech&limit=1&offset=0", headers=auth(admin)).json()[0]["id"] == company_id
    assert client.get("/api/companies?industry=finance", headers=auth(admin)).json() == []
    edited = client.patch(f"/api/companies/{company_id}", headers=auth(admin), json={"location": "Remote", "is_active": False})
    assert edited.status_code == 200
    assert edited.json()["location"] == "Remote" and not edited.json()["is_active"]
    assert client.get("/api/companies?is_active=false", headers=auth(admin)).json()[0]["id"] == company_id
    assert client.get("/api/companies?is_active=true", headers=auth(admin)).json() == []
    reactivated = client.patch(f"/api/companies/{company_id}", headers=auth(admin), json={"is_active": True})
    assert reactivated.json()["is_active"] is True


def test_company_validation_duplicate_and_not_found(client: TestClient):
    admin = add_admin(client)
    assert client.post("/api/companies", headers=auth(admin), json=company_payload("A")).status_code == 422
    invalid = company_payload()
    invalid["website"] = "javascript:alert(1)"
    assert client.post("/api/companies", headers=auth(admin), json=invalid).status_code == 422
    invalid = company_payload()
    invalid["hr_email"] = "not-an-email"
    assert client.post("/api/companies", headers=auth(admin), json=invalid).status_code == 422
    assert client.post("/api/companies", headers=auth(admin), json=company_payload()).status_code == 201
    duplicate = client.post("/api/companies", headers=auth(admin), json=company_payload())
    assert duplicate.status_code == 409
    assert client.get("/api/companies/999", headers=auth(admin)).status_code == 404
    assert client.patch("/api/companies/1", headers=auth(admin), json={}).status_code == 422


def test_recruiters_are_created_and_assigned_to_companies(client: TestClient):
    admin = add_admin(client)
    company = client.post("/api/companies", headers=auth(admin), json=company_payload()).json()
    created = client.post(f"/api/companies/{company['id']}/recruiters", headers=auth(admin), json={"full_name": "Recruiter One", "email": "recruiter@example.edu", "initial_password": "Recruiter-initial-123"})
    assert created.status_code == 201, created.text
    recruiter_id = created.json()["user_id"]
    with client.app.state.session_factory() as db:
        recruiter = db.scalar(select(User).where(User.id == recruiter_id))
        assert recruiter.role == "recruiter" and recruiter.company_id == company["id"]

    second = client.post("/api/companies", headers=auth(admin), json=company_payload("Lumen Works")).json()
    moved = client.put(f"/api/companies/{second['id']}/recruiters/{recruiter_id}", headers=auth(admin))
    assert moved.status_code == 200
    assert client.get(f"/api/companies/{company['id']}", headers=auth(admin)).json()["recruiters"] == []
    assert client.get(f"/api/companies/{second['id']}", headers=auth(admin)).json()["recruiters"][0]["user_id"] == recruiter_id
    student = add_student(client)
    assert client.post(f"/api/companies/{company['id']}/recruiters", headers=auth(student), json={"full_name": "X Recruiter", "email": "x@example.edu", "initial_password": "Recruiter-initial-123"}).status_code == 403
    assert client.put(f"/api/companies/{company['id']}/recruiters/999", headers=auth(admin)).status_code == 404


def test_database_rejects_recruiter_without_company(client: TestClient):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with client.app.state.session_factory.begin() as db:
            db.add(User(email="orphan@example.edu", full_name="Orphan Recruiter", password_hash="not-used", role="recruiter"))
