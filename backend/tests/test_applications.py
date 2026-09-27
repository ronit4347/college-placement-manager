import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.applications import router as applications_router, submission_router as application_submission_router
from app.api.routes.auth import router as auth_router
from app.api.routes.companies import router as companies_router
from app.api.routes.job_drives import router as job_drives_router
from app.api.routes.students import router as students_router
from app.api.routes.interviews import router as interviews_router
from app.api.routes.offers import router as offers_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.resume_analysis import router as resume_analysis_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Application, Offer, Student, User


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
    for router in (auth_router, students_router, companies_router, job_drives_router, applications_router, application_submission_router, interviews_router, offers_router, analytics_router, notifications_router, resume_analysis_router):
        test_app.include_router(router, prefix="/api")
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.state.session_factory = factory
    with TestClient(test_app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)
    engine.dispose()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def add_admin(client: TestClient) -> str:
    with client.app.state.session_factory.begin() as db:
        db.add(User(email="admin@example.edu", full_name="Placement Admin", password_hash=hash_password("Admin-strong-password-123"), role="admin"))
    return login(client, "admin@example.edu", "Admin-strong-password-123")


def add_student(client: TestClient, email: str, name: str, *, eligible: bool = True) -> tuple[str, int]:
    password = "Student-strong-password-123"
    registered = client.post("/api/auth/register", json={"email": email, "full_name": name, "password": password})
    assert registered.status_code == 201, registered.text
    token = login(client, email, password)
    if eligible:
        response = client.patch(
            "/api/students/me",
            headers=auth(token),
            json={"cgpa": 8.4, "backlogs": 0, "branch": "Computer Science", "graduation_year": 2027},
        )
        assert response.status_code == 200, response.text
        response = client.put("/api/students/me/skills", headers=auth(token), json={"skills": ["Python", "SQL"]})
        assert response.status_code == 200, response.text
    with client.app.state.session_factory() as db:
        student_id = db.scalar(select(Student.id).join(User).where(User.email == email))
    return token, student_id


def setup_drive(client: TestClient, admin: str, company_name: str = "Northstar") -> tuple[int, int]:
    company_response = client.post("/api/companies", headers=auth(admin), json={"name": company_name})
    assert company_response.status_code == 201, company_response.text
    company_id = company_response.json()["id"]
    payload = {
        "company_id": company_id,
        "title": "Graduate Engineer",
        "description": "Join a product team building useful technology for customers.",
        "min_cgpa": 7.5,
        "max_backlogs": 1,
        "allowed_branches": ["Computer Science"],
        "graduation_year": 2027,
        "required_skills": ["Python", "SQL"],
        "application_deadline": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
    }
    drive_response = client.post("/api/job-drives", headers=auth(admin), json=payload)
    assert drive_response.status_code == 201, drive_response.text
    drive_id = drive_response.json()["id"]
    return company_id, drive_id


def make_selected_application(client: TestClient, admin: str, email: str, name: str) -> tuple[str, int, int]:
    _, drive_id = setup_drive(client, admin, f"OfferCo {name}")
    publish(client, admin, drive_id)
    student_token, _ = add_student(client, email, name)
    response = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(student_token), json={})
    assert response.status_code == 201, response.text
    application_id = response.json()["id"]
    for target in ("SHORTLISTED", "INTERVIEW", "SELECTED"):
        moved = client.patch(f"/api/applications/{application_id}/status", headers=auth(admin), json={"status": target})
        assert moved.status_code == 200, moved.text
    return student_token, application_id, drive_id


def publish(client: TestClient, admin: str, drive_id: int) -> None:
    response = client.post(f"/api/job-drives/{drive_id}/publish", headers=auth(admin))
    assert response.status_code == 200, response.text


def test_application_requires_eligibility_published_drive_and_unexpired_deadline(client: TestClient):
    admin = add_admin(client)
    _, drive_id = setup_drive(client, admin)
    ineligible, _ = add_student(client, "low-cgpa@example.edu", "Low CGPA Student", eligible=False)
    client.patch("/api/students/me", headers=auth(ineligible), json={"cgpa": 6.4, "backlogs": 2, "branch": "Physics", "graduation_year": 2028})
    client.put("/api/students/me/skills", headers=auth(ineligible), json={"skills": ["Java"]})
    assert client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(ineligible), json={}).status_code == 409

    eligible, _ = add_student(client, "eligible@example.edu", "Eligible Student")
    draft_attempt = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(eligible), json={})
    assert draft_attempt.status_code == 409
    publish(client, admin, drive_id)

    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    update = client.patch(f"/api/job-drives/{drive_id}", headers=auth(admin), json={"application_deadline": expired})
    assert update.status_code == 200
    deadline_attempt = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(eligible), json={})
    assert deadline_attempt.status_code == 409
    assert deadline_attempt.json()["detail"] == "The application deadline has passed."


def test_student_apply_duplicate_own_applications_and_status_timeline(client: TestClient):
    admin = add_admin(client)
    _, drive_id = setup_drive(client, admin)
    publish(client, admin, drive_id)
    student, student_id = add_student(client, "candidate@example.edu", "Jamie Candidate")

    created = client.post(
        f"/api/job-drives/{drive_id}/applications",
        headers=auth(student),
        json={"cover_letter": "I am interested in this role."},
    )
    assert created.status_code == 201, created.text
    application = created.json()
    application_id = application["id"]
    assert application["status"] == "APPLIED"
    matching_drive = client.get("/api/job-drives?application_status=APPLIED", headers=auth(student))
    assert matching_drive.status_code == 200 and [item["id"] for item in matching_drive.json()] == [drive_id]
    assert [event["to_status"] for event in application["timeline"]] == ["APPLIED"]
    filtered = client.get("/api/applications?company=Northstar&job=Graduate&status=APPLIED&branch=Computer&limit=1", headers=auth(admin))
    assert filtered.status_code == 200 and [item["id"] for item in filtered.json()] == [application_id]
    own_notifications = client.get("/api/notifications", headers=auth(student)).json()
    assert [item["type"] for item in own_notifications] == ["application_submitted"]
    assert client.get("/api/notifications/unread-count", headers=auth(student)).json() == {"unread_count": 1}
    other_student, _ = add_student(client, "other@example.edu", "Other Student")
    assert client.patch(f"/api/notifications/{own_notifications[0]['id']}/read", headers=auth(other_student)).status_code == 404
    read_notification = client.patch(f"/api/notifications/{own_notifications[0]['id']}/read", headers=auth(student))
    assert read_notification.status_code == 200 and read_notification.json()["read_at"] is not None
    assert client.get("/api/notifications/unread-count", headers=auth(student)).json() == {"unread_count": 0}
    duplicate = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(student), json={})
    assert duplicate.status_code == 409

    own_list = client.get("/api/applications", headers=auth(student))
    assert own_list.status_code == 200 and len(own_list.json()) == 1
    assert own_list.json()[0]["student_id"] == student_id
    assert client.get(f"/api/applications/{application_id}", headers=auth(student)).status_code == 200

    assert client.get("/api/applications", headers=auth(other_student)).json() == []
    assert client.get(f"/api/applications/{application_id}", headers=auth(other_student)).status_code == 404

    assert client.patch(f"/api/applications/{application_id}/status", headers=auth(student), json={"status": "REJECTED"}).status_code == 403
    invalid_skip = client.patch(f"/api/applications/{application_id}/status", headers=auth(admin), json={"status": "INTERVIEW"})
    assert invalid_skip.status_code == 409

    for target in ("SHORTLISTED", "INTERVIEW", "SELECTED"):
        changed = client.patch(
            f"/api/applications/{application_id}/status",
            headers=auth(admin),
            json={"status": target, "note": f"Moved to {target.lower()}."},
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["status"] == target
    direct_offer = client.patch(f"/api/applications/{application_id}/status", headers=auth(admin), json={"status": "OFFERED"})
    assert direct_offer.status_code == 409
    created_offer = client.post("/api/offers", headers=auth(admin), json={"application_id": application_id, "salary": "1200000", "joining_date": "2027-07-01"})
    assert created_offer.status_code == 201, created_offer.text
    issued_offer = client.post(f"/api/offers/{created_offer.json()['id']}/issue", headers=auth(admin))
    assert issued_offer.status_code == 200 and issued_offer.json()["status"] == "ISSUED"
    assert {item["type"] for item in client.get("/api/notifications", headers=auth(student)).json()} >= {
        "application_submitted", "application_shortlisted", "candidate_selected", "offer_issued"
    }
    assert client.post(f"/api/offers/{created_offer.json()['id']}/respond", headers=auth(student), json={"status": "ACCEPTED"}).status_code == 200
    joined = client.patch(f"/api/applications/{application_id}/status", headers=auth(admin), json={"status": "JOINED"})
    assert joined.status_code == 200
    final = client.get(f"/api/applications/{application_id}", headers=auth(student)).json()
    assert [event["to_status"] for event in final["timeline"]] == ["APPLIED", "SHORTLISTED", "INTERVIEW", "SELECTED", "OFFERED", "JOINED"]
    assert final["timeline"][-1]["actor_name"] == "Placement Admin"
    assert client.patch(f"/api/applications/{application_id}/status", headers=auth(admin), json={"status": "APPLIED"}).status_code == 409
    with client.app.state.session_factory() as db:
        offer = db.scalar(select(Offer).where(Offer.application_id == application_id))
        assert offer is not None and offer.status == "accepted"


def test_rejection_is_terminal_and_admin_can_manage_all_applications(client: TestClient):
    admin = add_admin(client)
    _, drive_id = setup_drive(client, admin)
    publish(client, admin, drive_id)
    student, _ = add_student(client, "applicant@example.edu", "Applicant")
    application = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(student), json={}).json()
    rejected = client.patch(f"/api/applications/{application['id']}/status", headers=auth(admin), json={"status": "REJECTED", "note": "Does not meet role needs."})
    assert rejected.status_code == 200
    assert rejected.json()["timeline"][-1]["note"] == "Does not meet role needs."
    assert client.get("/api/notifications", headers=auth(student)).json()[0]["type"] == "application_rejected"
    assert client.patch(f"/api/applications/{application['id']}/status", headers=auth(admin), json={"status": "SHORTLISTED"}).status_code == 409
    assert len(client.get("/api/applications", headers=auth(admin)).json()) == 1


def test_recruiter_applications_are_company_scoped_and_other_roles_are_denied(client: TestClient):
    admin = add_admin(client)
    first_company, first_drive = setup_drive(client, admin, "Northstar")
    _, second_drive = setup_drive(client, admin, "Lumen")
    publish(client, admin, first_drive)
    publish(client, admin, second_drive)
    student_one, _ = add_student(client, "first-candidate@example.edu", "First Candidate")
    student_two, _ = add_student(client, "second-candidate@example.edu", "Second Candidate")
    first_application = client.post(f"/api/job-drives/{first_drive}/applications", headers=auth(student_one), json={}).json()
    second_application = client.post(f"/api/job-drives/{second_drive}/applications", headers=auth(student_two), json={}).json()
    with client.app.state.session_factory.begin() as db:
        db.add(User(email="recruiter@example.edu", full_name="Northstar Recruiter", password_hash=hash_password("Recruiter-strong-password-123"), role="recruiter", company_id=first_company))
        db.add(User(email="interviewer@example.edu", full_name="Interviewer", password_hash=hash_password("Interviewer-strong-password-123"), role="interviewer"))
    recruiter = login(client, "recruiter@example.edu", "Recruiter-strong-password-123")
    interviewer = login(client, "interviewer@example.edu", "Interviewer-strong-password-123")

    recruiter_list = client.get("/api/applications", headers=auth(recruiter))
    assert [record["id"] for record in recruiter_list.json()] == [first_application["id"]]
    assert client.get(f"/api/applications/{second_application['id']}", headers=auth(recruiter)).status_code == 404
    assert client.get("/api/applications", headers=auth(interviewer)).status_code == 403
    assert client.post(f"/api/job-drives/{first_drive}/applications", headers=auth(recruiter), json={}).status_code == 403
    assert client.patch(f"/api/applications/{first_application['id']}/status", headers=auth(recruiter), json={"status": "SHORTLISTED"}).status_code == 403


def test_role_matrix_denies_each_nonmatching_role(client: TestClient):
    admin = add_admin(client)
    company_id, drive_id = setup_drive(client, admin, "RBAC matrix")
    publish(client, admin, drive_id)
    student, _ = add_student(client, "rbac-student@example.edu", "RBAC Student")
    with client.app.state.session_factory.begin() as db:
        db.add_all([
            User(email="rbac-recruiter@example.edu", full_name="RBAC Recruiter", password_hash=hash_password("Recruiter-strong-password-123"), role="recruiter", company_id=company_id),
            User(email="rbac-interviewer@example.edu", full_name="RBAC Interviewer", password_hash=hash_password("Interviewer-strong-password-123"), role="interviewer"),
        ])
    recruiter = login(client, "rbac-recruiter@example.edu", "Recruiter-strong-password-123")
    interviewer = login(client, "rbac-interviewer@example.edu", "Interviewer-strong-password-123")
    role_tokens = {"ADMIN": admin, "STUDENT": student, "RECRUITER": recruiter, "INTERVIEWER": interviewer}

    # Every non-student role is denied student profile, application, and AI operations.
    for role, token in role_tokens.items():
        if role != "STUDENT":
            assert client.get("/api/students/me", headers=auth(token)).status_code == 403, role
            assert client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(token), json={}).status_code == 403, role
            assert client.post("/api/students/me/resume-analysis", headers=auth(token), json={"job_drive_id": drive_id}).status_code == 403, role

    # Every non-admin role is denied company administration and analytics.
    for role, token in role_tokens.items():
        if role != "ADMIN":
            assert client.get("/api/companies", headers=auth(token)).status_code == 403, role
            assert client.get("/api/admin/analytics/dashboard", headers=auth(token)).status_code == 403, role

    # Only the assigned-interviewer role may invoke the interview result operation.
    for role, token in role_tokens.items():
        expected = 404 if role == "INTERVIEWER" else 403
        response = client.patch("/api/interviews/999/result", headers=auth(token), json={"result": "PASSED"})
        assert response.status_code == expected, (role, response.text)


def test_application_input_validation(client: TestClient):
    admin = add_admin(client)
    _, drive_id = setup_drive(client, admin)
    publish(client, admin, drive_id)
    student, _ = add_student(client, "validation@example.edu", "Validation Student")
    too_long = {"cover_letter": "x" * 5001}
    assert client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(student), json=too_long).status_code == 422
    assert client.patch("/api/applications/999/status", headers=auth(admin), json={"status": "APPLIED"}).status_code == 404


def test_interview_schedule_access_result_reschedule_and_cancel(client: TestClient):
    admin = add_admin(client)
    _, drive_id = setup_drive(client, admin)
    publish(client, admin, drive_id)
    student, _ = add_student(client, "interview-candidate@example.edu", "Interview Candidate")
    app_record = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(student), json={}).json()
    assert client.patch(f"/api/applications/{app_record['id']}/status", headers=auth(admin), json={"status": "SHORTLISTED"}).status_code == 200
    with client.app.state.session_factory.begin() as db:
        db.add(User(email="round-interviewer@example.edu", full_name="Round Interviewer", password_hash=hash_password("Interviewer-strong-password-123"), role="interviewer"))
        db.add(User(email="other-interviewer@example.edu", full_name="Other Interviewer", password_hash=hash_password("Other-strong-password-123"), role="interviewer"))
    interviewer = login(client, "round-interviewer@example.edu", "Interviewer-strong-password-123")
    other_interviewer = login(client, "other-interviewer@example.edu", "Other-strong-password-123")
    with client.app.state.session_factory() as db:
        interviewer_id = db.scalar(select(User.id).where(User.email == "round-interviewer@example.edu"))
    when = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    payload = {"application_id": app_record["id"], "round": "TECHNICAL", "interviewer_user_id": interviewer_id, "scheduled_at": when}
    assert client.post("/api/interviews", headers=auth(student), json=payload).status_code == 403
    created = client.post("/api/interviews", headers=auth(admin), json=payload)
    assert created.status_code == 201, created.text
    interview_id = created.json()["id"]
    assert created.json()["round"] == "TECHNICAL"
    assert client.get("/api/notifications", headers=auth(student)).json()[0]["type"] == "interview_scheduled"
    assert client.get("/api/notifications", headers=auth(interviewer)).json()[0]["type"] == "interview_scheduled"
    assert client.get("/api/interviews", headers=auth(interviewer)).json()[0]["student_name"] == "Interview Candidate"
    student_view = client.get("/api/interviews", headers=auth(student))
    assert student_view.status_code == 200 and "feedback" not in student_view.json()[0]
    assert client.get(f"/api/interviews/{interview_id}", headers=auth(other_interviewer)).status_code == 404
    assert client.get(f"/api/interviews/{interview_id}", headers=auth(student)).status_code == 200
    assert client.patch(f"/api/interviews/{interview_id}/result", headers=auth(other_interviewer), json={"result": "PASSED"}).status_code == 404
    result = client.patch(f"/api/interviews/{interview_id}/result", headers=auth(interviewer), json={"result": "PASSED", "feedback": "Strong problem solving."})
    assert result.status_code == 200 and result.json()["status"] == "COMPLETED"
    assert result.json()["feedback"] == "Strong problem solving."
    assert client.get("/api/notifications", headers=auth(student)).json()[0]["type"] == "interview_result"
    assert client.patch(f"/api/interviews/{interview_id}/reschedule", headers=auth(admin), json={"scheduled_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()}).status_code == 409


def test_interview_validation_conflicts_reschedule_and_cancel(client: TestClient):
    admin = add_admin(client)
    _, drive_id = setup_drive(client, admin)
    publish(client, admin, drive_id)
    candidate, _ = add_student(client, "schedule-candidate@example.edu", "Schedule Candidate")
    application = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(candidate), json={}).json()
    client.patch(f"/api/applications/{application['id']}/status", headers=auth(admin), json={"status": "SHORTLISTED"})
    with client.app.state.session_factory.begin() as db:
        user = User(email="schedule-interviewer@example.edu", full_name="Schedule Interviewer", password_hash=hash_password("Interview-strong-password-123"), role="interviewer")
        db.add(user)
    with client.app.state.session_factory() as db:
        interviewer_id = db.scalar(select(User.id).where(User.email == "schedule-interviewer@example.edu"))
    future = datetime.now(timezone.utc) + timedelta(days=4)
    payload = {"application_id": application["id"], "round": "APTITUDE", "interviewer_user_id": interviewer_id, "scheduled_at": future.isoformat()}
    assert client.post("/api/interviews", headers=auth(admin), json={**payload, "round": "OTHER"}).status_code == 422
    assert client.post("/api/interviews", headers=auth(admin), json={**payload, "scheduled_at": datetime.now().isoformat()}).status_code == 422
    first = client.post("/api/interviews", headers=auth(admin), json=payload)
    assert first.status_code == 201, first.text
    second_app = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(add_student(client, "second-schedule@example.edu", "Second Candidate")[0]), json={}).json()
    client.patch(f"/api/applications/{second_app['id']}/status", headers=auth(admin), json={"status": "SHORTLISTED"})
    conflict = client.post("/api/interviews", headers=auth(admin), json={**payload, "application_id": second_app["id"], "scheduled_at": (future + timedelta(minutes=30)).isoformat()})
    assert conflict.status_code == 409
    interview_id = first.json()["id"]
    rescheduled = client.patch(f"/api/interviews/{interview_id}/reschedule", headers=auth(admin), json={"scheduled_at": (future + timedelta(days=2)).isoformat()})
    assert rescheduled.status_code == 200 and rescheduled.json()["status"] == "RESCHEDULED"
    assert client.get("/api/notifications", headers=auth(candidate)).json()[0]["type"] == "interview_rescheduled"
    assert client.post(f"/api/interviews/{interview_id}/cancel", headers=auth(admin)).json()["status"] == "CANCELLED"
    assert client.post(f"/api/interviews/{interview_id}/cancel", headers=auth(admin)).status_code == 409


def test_offer_selection_duplicate_accept_decline_and_expiration(client: TestClient):
    admin = add_admin(client)
    _, drive_id = setup_drive(client, admin, "Offer eligibility")
    publish(client, admin, drive_id)
    not_selected_token, _ = add_student(client, "not-selected-offer@example.edu", "Not Selected")
    not_selected_app = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(not_selected_token), json={}).json()
    offer_payload = {"application_id": not_selected_app["id"], "salary": "1500000", "joining_date": "2027-07-15", "offer_letter_reference": "https://example.test/letter/1"}
    assert client.post("/api/offers", headers=auth(admin), json=offer_payload).status_code == 409
    assert client.post("/api/offers", headers=auth(not_selected_token), json=offer_payload).status_code == 403

    candidate, selected_id, _ = make_selected_application(client, admin, "accepted-offer@example.edu", "Accepted Candidate")
    created = client.post("/api/offers", headers=auth(admin), json={**offer_payload, "application_id": selected_id})
    assert created.status_code == 201, created.text
    offer_id = created.json()["id"]
    assert created.json()["status"] == "DRAFT"
    assert created.json()["candidate_name"] == "Accepted Candidate"
    assert created.json()["company_name"] == "OfferCo Accepted Candidate"
    assert created.json()["job_title"] == "Graduate Engineer"
    assert client.post("/api/offers", headers=auth(admin), json={**offer_payload, "application_id": selected_id}).status_code == 409
    issued = client.post(f"/api/offers/{offer_id}/issue", headers=auth(admin))
    assert issued.status_code == 200 and issued.json()["status"] == "ISSUED"
    assert client.get(f"/api/applications/{selected_id}", headers=auth(admin)).json()["status"] == "OFFERED"
    assert client.post(f"/api/offers/{offer_id}/respond", headers=auth(candidate), json={"status": "ACCEPTED"}).json()["status"] == "ACCEPTED"

    decliner, decline_app_id, _ = make_selected_application(client, admin, "declined-offer@example.edu", "Declined Candidate")
    declined_offer = client.post("/api/offers", headers=auth(admin), json={**offer_payload, "application_id": decline_app_id}).json()
    assert client.post(f"/api/offers/{declined_offer['id']}/issue", headers=auth(admin)).status_code == 200
    assert client.post(f"/api/offers/{declined_offer['id']}/respond", headers=auth(decliner), json={"status": "DECLINED"}).json()["status"] == "DECLINED"

    expiring_candidate, expiring_app_id, _ = make_selected_application(client, admin, "expired-offer@example.edu", "Expired Candidate")
    expires = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    expiring = client.post("/api/offers", headers=auth(admin), json={**offer_payload, "application_id": expiring_app_id, "expires_at": expires}).json()
    assert client.post(f"/api/offers/{expiring['id']}/issue", headers=auth(admin)).status_code == 200
    with client.app.state.session_factory.begin() as db:
        db.get(Offer, expiring["id"]).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired_response = client.post(f"/api/offers/{expiring['id']}/respond", headers=auth(expiring_candidate), json={"status": "ACCEPTED"})
    assert expired_response.status_code == 409
    assert client.get(f"/api/offers/{expiring['id']}", headers=auth(expiring_candidate)).json()["status"] == "EXPIRED"


def test_offer_student_ownership_and_recruiter_company_scope(client: TestClient):
    admin = add_admin(client)
    own_student, own_application, own_drive = make_selected_application(client, admin, "own-offer@example.edu", "Own Offer")
    other_student, other_application, other_drive = make_selected_application(client, admin, "other-offer@example.edu", "Other Offer")
    payload = {"salary": "1000000", "joining_date": "2027-07-01"}
    own_offer = client.post("/api/offers", headers=auth(admin), json={**payload, "application_id": own_application}).json()
    other_offer = client.post("/api/offers", headers=auth(admin), json={**payload, "application_id": other_application}).json()
    # Students can see issued offers; draft terms remain private until issued.
    assert client.get("/api/offers", headers=auth(own_student)).json() == []
    assert client.post(f"/api/offers/{own_offer['id']}/issue", headers=auth(admin)).status_code == 200
    assert client.post(f"/api/offers/{other_offer['id']}/issue", headers=auth(admin)).status_code == 200
    assert [item["id"] for item in client.get("/api/offers", headers=auth(own_student)).json()] == [own_offer["id"]]
    assert client.get(f"/api/offers/{other_offer['id']}", headers=auth(own_student)).status_code == 404
    with client.app.state.session_factory.begin() as db:
        own_company_id = db.scalar(select(Application).where(Application.id == own_application)).job_drive.company_id
        db.add(User(email="offer-recruiter@example.edu", full_name="Offer Recruiter", password_hash=hash_password("Recruiter-strong-password-123"), role="recruiter", company_id=own_company_id))
    recruiter = login(client, "offer-recruiter@example.edu", "Recruiter-strong-password-123")
    assert [item["id"] for item in client.get("/api/offers", headers=auth(recruiter)).json()] == [own_offer["id"]]
    assert client.get(f"/api/offers/{other_offer['id']}", headers=auth(recruiter)).status_code == 404
    assert client.get("/api/offers", headers=auth(add_student(client, "no-offer@example.edu", "No Offers")[0])).json() == []
    assert client.post(f"/api/offers/{own_offer['id']}/issue", headers=auth(recruiter)).status_code == 403


def test_admin_analytics_uses_persisted_workflow_data_and_filters(client: TestClient):
    admin = add_admin(client)
    company_id, drive_id = setup_drive(client, admin, "Analytics Employer")
    publish(client, admin, drive_id)
    student, _ = add_student(client, "analytics-candidate@example.edu", "Analytics Candidate")
    application = client.post(f"/api/job-drives/{drive_id}/applications", headers=auth(student), json={}).json()
    client.patch(f"/api/applications/{application['id']}/status", headers=auth(admin), json={"status": "SHORTLISTED"})
    with client.app.state.session_factory.begin() as db:
        interviewer_user = User(email="analytics-interviewer@example.edu", full_name="Analytics Interviewer", password_hash=hash_password("Analytics-strong-password-123"), role="interviewer")
        db.add(interviewer_user)
    with client.app.state.session_factory() as db:
        interviewer_id = db.scalar(select(User.id).where(User.email == "analytics-interviewer@example.edu"))
    scheduled = client.post("/api/interviews", headers=auth(admin), json={
        "application_id": application["id"], "round": "TECHNICAL", "interviewer_user_id": interviewer_id,
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    })
    assert scheduled.status_code == 201, scheduled.text
    for target in ("INTERVIEW", "SELECTED"):
        assert client.patch(f"/api/applications/{application['id']}/status", headers=auth(admin), json={"status": target}).status_code == 200
    offer = client.post("/api/offers", headers=auth(admin), json={"application_id": application["id"], "salary": "1200000", "joining_date": "2027-07-01"}).json()
    assert client.post(f"/api/offers/{offer['id']}/issue", headers=auth(admin)).status_code == 200
    assert client.post(f"/api/offers/{offer['id']}/respond", headers=auth(student), json={"status": "ACCEPTED"}).status_code == 200
    assert client.patch(f"/api/applications/{application['id']}/status", headers=auth(admin), json={"status": "JOINED"}).status_code == 200

    headers = auth(admin)
    response = client.get("/api/admin/analytics/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["metrics"] == {
        "total_students": 1, "total_companies": 1, "active_job_drives": 1,
        "total_applications": 1, "shortlisted_candidates": 1, "interviews": 1,
        "selected_candidates": 1, "offers": 1, "placements": 1, "placement_rate": 100.0,
    }
    assert body["placement_by_branch"] == [{"name": "Computer Science", "value": 1}]
    assert [item["count"] for item in body["application_funnel"]] == [1, 1, 1, 1, 1, 1]
    assert body["company_selections"] == [{"name": "Analytics Employer", "value": 1}]
    assert body["package_distribution"][2] == {"name": "₹10L–₹15L", "value": 1}
    assert len(body["monthly_placement_activity"]) == 12
    assert sum(item["placements"] for item in body["monthly_placement_activity"]) == 1

    filtered = client.get(f"/api/admin/analytics/dashboard?graduation_year=2027&branch=computer%20science&company_id={company_id}&date_from={(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()}", headers=headers)
    assert filtered.status_code == 200
    assert filtered.json()["metrics"]["placements"] == 1
    empty = client.get("/api/admin/analytics/dashboard?graduation_year=2028", headers=headers).json()
    assert empty["metrics"]["total_students"] == 0 and empty["metrics"]["total_applications"] == 0
    assert client.get("/api/admin/analytics/filters", headers=headers).json()["companies"] == [{"id": company_id, "name": "Analytics Employer"}]
    assert client.get("/api/admin/analytics/dashboard", headers=auth(student)).status_code == 403
    assert client.get("/api/admin/analytics/dashboard?date_from=2026-09-30&date_to=2026-09-01", headers=headers).status_code == 422
