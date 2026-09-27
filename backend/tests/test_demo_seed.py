import secrets

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import SecretStr

from app.core.config import settings
from app.db.base import Base
from app.db.seed_demo import (
    DEMO_ADMIN_EMAIL,
    DEMO_INTERVIEWER_EMAIL,
    DEMO_RECRUITER_EMAIL,
    DEMO_STUDENT_EMAIL,
    seed_demo_data,
)
from app.db.session import get_db
from app.main import app
from app.models import Application, Company, Interview, JobDrive, Offer, Skill, Student, User


def test_demo_seed_is_repeatable_and_runs_demo_flows(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", secrets.token_hex(32))
    monkeypatch.setattr(settings, "demo_admin_password", SecretStr("Fictional-Admin-Password-2026"))
    monkeypatch.setattr(settings, "demo_student_password", SecretStr("Fictional-Student-Password-2026"))
    monkeypatch.setattr(settings, "demo_recruiter_password", SecretStr("Fictional-Recruiter-Password-2026"))
    monkeypatch.setattr(settings, "demo_interviewer_password", SecretStr("Fictional-Interviewer-Password-2026"))

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    first_run = seed_demo_data(factory)
    second_run = seed_demo_data(factory)

    with factory() as db:
        assert db.scalar(select(func.count(Student.id))) == 30
        assert db.scalar(select(func.count(Company.id))) == 5
        assert db.scalar(select(func.count(JobDrive.id))) == 8
        assert db.scalar(select(func.count(Skill.id))) >= 15
        assert db.scalar(select(func.count(Application.id))) >= 30
        assert db.scalar(select(func.count(Interview.id))) >= 10
        assert db.scalar(select(func.count(Offer.id))) >= 5
        assert db.scalar(select(func.count(User.id)).where(User.email.in_([
            DEMO_ADMIN_EMAIL, DEMO_STUDENT_EMAIL, DEMO_RECRUITER_EMAIL, DEMO_INTERVIEWER_EMAIL,
        ]))) == 4
        assert first_run["applications_created_this_run"] >= 30
        assert second_run["applications_created_this_run"] == 0
        assert first_run["demo_applications"] == second_run["demo_applications"]

    def override_get_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            def login(email: str, password: str) -> dict[str, str]:
                response = client.post("/api/auth/login", json={"email": email, "password": password})
                assert response.status_code == 200, response.text
                return {"Authorization": f"Bearer {response.json()['access_token']}"}

            admin = login(DEMO_ADMIN_EMAIL, "Fictional-Admin-Password-2026")
            student = login(DEMO_STUDENT_EMAIL, "Fictional-Student-Password-2026")
            recruiter = login(DEMO_RECRUITER_EMAIL, "Fictional-Recruiter-Password-2026")
            interviewer = login(DEMO_INTERVIEWER_EMAIL, "Fictional-Interviewer-Password-2026")

            dashboard = client.get("/api/admin/analytics/dashboard", headers=admin)
            assert dashboard.status_code == 200, dashboard.text
            assert dashboard.json()["metrics"]["total_students"] == 30
            assert dashboard.json()["metrics"]["total_companies"] == 5
            assert dashboard.json()["metrics"]["total_applications"] >= 30
            assert dashboard.json()["metrics"]["interviews"] >= 10
            assert dashboard.json()["metrics"]["offers"] >= 5
            assert dashboard.json()["metrics"]["selected_candidates"] > 0
            assert dashboard.json()["metrics"]["placements"] > 0
            assert dashboard.json()["metrics"]["placement_rate"] > 0
            assert sum(row["count"] for row in dashboard.json()["application_funnel"]) > 0
            assert dashboard.json()["package_distribution"]
            assert client.get("/api/companies", headers=admin).status_code == 200
            assert len(client.get("/api/job-drives", headers=admin).json()) == 8
            assert client.get("/api/interviews", headers=admin).json()
            assert client.get("/api/offers", headers=admin).json()

            profile = client.get("/api/students/me", headers=student)
            assert profile.status_code == 200 and profile.json()["profile_completion"] >= 80
            jobs = client.get("/api/job-drives", headers=student)
            assert jobs.status_code == 200 and len(jobs.json()) == 6
            eligible_jobs = client.get("/api/job-drives/eligible", headers=student)
            assert eligible_jobs.status_code == 200 and eligible_jobs.json()
            eligibility = client.get(f"/api/job-drives/{eligible_jobs.json()[0]['id']}/eligibility", headers=student)
            assert eligibility.status_code == 200 and eligibility.json()["eligible"] is True
            assert client.get("/api/applications", headers=student).json()
            assert client.get("/api/interviews", headers=student).json()
            assert client.get("/api/offers", headers=student).json()

            recruiter_jobs = client.get("/api/job-drives", headers=recruiter)
            assert recruiter_jobs.status_code == 200 and recruiter_jobs.json()
            assert all(item["company_name"] == "Blue Oak Robotics" for item in recruiter_jobs.json())
            assert client.get("/api/interviews", headers=interviewer).json()
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
