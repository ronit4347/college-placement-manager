"""Create a repeatable, fictional placement dataset for local demonstrations.

Run only against a development database. Credentials are supplied via environment
settings and only password hashes are persisted.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.session import get_session_factory
from app.models import (
    Application,
    Company,
    Interview,
    JobDrive,
    JobSkill,
    Offer,
    Skill,
    Student,
    StudentSkill,
    User,
)
from app.schemas.applications import ApplicationStatusUpdate, ApplicationSubmit
from app.schemas.interviews import InterviewResultUpdate
from app.schemas.job_drives import JobDriveCreate
from app.schemas.offers import OfferCreate
from app.services.applications import apply_to_job_drive, transition_application_status
from app.services.companies import create_company
from app.services.eligibility import evaluate_eligibility
from app.services.interviews import schedule_interview, submit_result
from app.services.job_drives import create_job_drive, transition_job_drive
from app.services.offers import create_offer, issue_offer, respond_to_offer
from app.schemas.companies import CompanyCreate


DEMO_ADMIN_EMAIL = "admin@demo.college-placement.example.edu"
DEMO_STUDENT_EMAIL = "student01@demo.college-placement.example.edu"
DEMO_RECRUITER_EMAIL = "recruiter@demo.college-placement.example.edu"
DEMO_INTERVIEWER_EMAIL = "interviewer@demo.college-placement.example.edu"

SKILL_NAMES = (
    "Python", "Java", "JavaScript", "TypeScript", "SQL", "PostgreSQL", "React",
    "FastAPI", "Docker", "AWS", "Linux", "Git", "Tableau", "Selenium",
    "Communication", "Leadership", "Problem Solving", "Data Analysis", "Figma",
    "Networking", "Power BI", "Software Testing",
)
CORE_ELIGIBILITY_SKILLS = (
    "Python", "SQL", "TypeScript", "React", "Tableau", "Selenium", "Java",
    "AWS", "Linux", "Networking",
)
BRANCHES = ("Computer Science", "Information Technology", "Computer Engineering")
COMPANY_DATA = (
    ("Blue Oak Robotics", "Industrial Automation", "Pune, India", "Aster Vale", "hr@blueoak.example"),
    ("Northstar Analytics", "Data & Analytics", "Bengaluru, India", "Mira Sol", "talent@northstar.example"),
    ("Copperleaf Systems", "Enterprise Software", "Hyderabad, India", "Arin Moss", "careers@copperleaf.example"),
    ("Juniper Cloud Works", "Cloud Services", "Remote, India", "Nia Rowan", "people@junipercloud.example"),
    ("Harborlight Digital", "Product Technology", "Chennai, India", "Dev Ellis", "hiring@harborlight.example"),
)
JOB_DATA = (
    (0, "Graduate Software Engineer", "Build and maintain dependable services for business customers.", 7.0, 1, BRANCHES, ("Python", "SQL"), 12, 18),
    (1, "Frontend Engineer Associate", "Create accessible product interfaces with a collaborative engineering team.", 7.3, 1, BRANCHES, ("TypeScript", "React"), 10, 16),
    (2, "Junior Data Analyst", "Translate operational data into useful, well-explained business insights.", 7.0, 2, BRANCHES, ("Python", "SQL", "Tableau"), 9, 14),
    (2, "Quality Engineering Associate", "Improve product reliability with thoughtful test automation.", 6.8, 2, BRANCHES, ("Java", "Selenium"), 8, 12),
    (3, "Cloud Operations Associate", "Support secure deployments and reliable cloud infrastructure.", 7.5, 0, BRANCHES[:2], ("AWS", "Linux"), 13, 20),
    (4, "Network Security Analyst", "Help monitor and improve security controls for internal systems.", 7.7, 0, BRANCHES, ("Linux", "Networking"), 14, 22),
    (1, "Applied AI Intern", "Prototype practical machine learning features with a product team.", 8.2, 0, BRANCHES[:2], ("Python", "Data Analysis"), 6, 9),
    (4, "Product Design Intern", "Partner with product and engineering to improve everyday user journeys.", 6.5, 2, BRANCHES, ("Figma", "Communication"), 5, 8),
)
STUDENT_NAMES = (
    "Aanya Mehta", "Kabir Nair", "Ira Kapoor", "Rohan Iyer", "Tara Menon", "Neel Shah",
    "Maya Kulkarni", "Arjun Rao", "Diya Sen", "Vihaan Das", "Anika Bose", "Reyansh Pillai",
    "Sara Thomas", "Advik Joshi", "Myra Reddy", "Ishaan Verma", "Kiara Sethi", "Dev Malhotra",
    "Navya Rao", "Aarav Bhat", "Sana Dutta", "Kian Fernandes", "Riya Sood", "Om Prakash",
    "Leela Anand", "Yuvan Gill", "Mira Chawla", "Aadi Khanna", "Nisha George", "Veer Patil",
)
INTERVIEW_ROUNDS = ("aptitude", "technical", "managerial", "hr")


def _configured_password(name: str) -> str:
    configured = getattr(settings, name)
    value = configured.get_secret_value() if configured is not None else ""
    if len(value) < 12 or len(value) > 128:
        raise RuntimeError(f"{name.upper()} must be configured with 12 to 128 characters.")
    return value


def _upsert_user(db: Session, email: str, name: str, role: str, password: str, company_id: int | None = None) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, full_name=name, role=role, password_hash=hash_password(password), company_id=company_id)
        db.add(user)
        db.flush()
    elif user.role != role:
        raise RuntimeError(f"Existing demo account {email} has unexpected role {user.role!r}.")
    else:
        user.full_name = name
        user.is_active = True
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
        if company_id is not None:
            user.company_id = company_id
    return user


def _upsert_company(db: Session, admin: User, item: tuple[str, str, str, str, str]) -> Company:
    name, industry, location, hr_name, hr_email = item
    company = db.scalar(select(Company).where(Company.name == name))
    if company is None:
        company = create_company(db, CompanyCreate(
            name=name, industry=industry, location=location, website=f"https://{name.split()[0].lower()}.example",
            hr_name=hr_name, hr_email=hr_email, description=f"Fictional {industry.lower()} employer included for local placement demonstrations.",
        ), admin)
    else:
        company.industry = industry
        company.location = location
        company.hr_name = hr_name
        company.hr_email = hr_email
        company.is_active = True
        db.commit()
        db.refresh(company)
    return company


def _upsert_student(db: Session, index: int, student_password: str, skills: dict[str, Skill]) -> tuple[User, Student]:
    email = f"student{index + 1:02d}@demo.college-placement.example.edu"
    user = _upsert_user(db, email, STUDENT_NAMES[index], "student", student_password)
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        student = Student(user_id=user.id)
        db.add(student)
        db.flush()

    is_academic_match = index < 20
    student.student_number = f"DEMO-27-{index + 1:03d}"
    student.branch = BRANCHES[index % len(BRANCHES)] if is_academic_match else ("Architecture" if index % 2 else "Electronics Engineering")
    student.graduation_year = 2027 if index < 24 else 2028
    student.cgpa = Decimal(str(round(7.2 + (index % 9) * 0.31, 2) if is_academic_match else 5.9 + (index % 4) * 0.35))
    student.backlogs = (index % 2) if is_academic_match else 2 + index % 3
    student.phone = f"+1-202-555-{100 + index:04d}"

    current_links = {link.skill.name.casefold(): link for link in student.skill_links}
    chosen = SKILL_NAMES if is_academic_match else tuple(SKILL_NAMES[(index + step * 3) % len(SKILL_NAMES)] for step in range(6))
    for name in chosen:
        canonical = name.casefold()
        if canonical not in current_links:
            db.add(StudentSkill(student=student, skill=skills[canonical], proficiency="Working knowledge"))
    return user, student


def _upsert_drive(db: Session, company: Company, index: int, now: datetime) -> JobDrive:
    _, title, description, cgpa, backlogs, branches, required_skills, low_package, high_package = JOB_DATA[index]
    drive = db.scalar(select(JobDrive).where(JobDrive.company_id == company.id, JobDrive.title == title))
    if drive is None:
        payload = JobDriveCreate(
            company_id=company.id, title=title, description=description,
            package_min=Decimal(low_package * 100_000), package_max=Decimal(high_package * 100_000),
            location=company.location, employment_type="INTERNSHIP" if "Intern" in title else "FULL_TIME",
            min_cgpa=Decimal(str(cgpa)), max_backlogs=backlogs, allowed_branches=list(branches),
            graduation_year=2027, required_skills=list(required_skills),
            application_deadline=now + timedelta(days=75),
        )
        drive = create_job_drive(db, payload)
        if drive is None:
            raise RuntimeError(f"Could not create demo job drive {title}.")
    return drive


def _application_for(db: Session, student: Student, drive: JobDrive, user: User) -> Application | None:
    existing = db.scalar(select(Application).where(Application.student_id == student.id, Application.job_drive_id == drive.id))
    if existing is not None:
        return existing
    if not evaluate_eligibility(student, drive).eligible:
        return None
    try:
        return apply_to_job_drive(db, user, drive, ApplicationSubmit(cover_letter="I am interested in contributing to this team's work and learning from its engineers."))
    except FileExistsError:
        return db.scalar(select(Application).where(Application.student_id == student.id, Application.job_drive_id == drive.id))


def _move(db: Session, application: Application, admin: User, target: str) -> Application:
    return transition_application_status(db, application, admin, ApplicationStatusUpdate(
        status=target, note="Progressed as part of the fictional development demo dataset.",
    ))


def _ensure_interview(db: Session, application: Application, interviewer: User, ordinal: int, result: str | None) -> Interview:
    interview = db.scalar(select(Interview).where(
        Interview.application_id == application.id,
        Interview.round_name == INTERVIEW_ROUNDS[ordinal % len(INTERVIEW_ROUNDS)],
    ).order_by(Interview.id).limit(1))
    if interview is None:
        interview = schedule_interview(
            db, application, interviewer, INTERVIEW_ROUNDS[ordinal % len(INTERVIEW_ROUNDS)],
            datetime.now(timezone.utc) + timedelta(days=2 + ordinal * 2, hours=9 + ordinal % 6), 60,
        )
    if result and interview.status in ("scheduled", "rescheduled"):
        submit_result(db, interview, result, "Fictional demo feedback: clear communication and a structured approach.")
    return interview


def _ensure_offer(db: Session, application: Application, admin: User, student_user: User, ordinal: int, join: bool) -> Offer:
    offer = db.scalar(select(Offer).where(Offer.application_id == application.id).order_by(Offer.id).limit(1))
    if offer is None:
        offer = create_offer(db, application, OfferCreate(
            application_id=application.id,
            salary=Decimal(1_000_000 + (ordinal % 8) * 175_000), currency="INR",
            joining_date=date.today() + timedelta(days=180 + ordinal),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            offer_letter_reference=f"demo://offer/{application.id}",
        ), admin)
    if offer.status == "draft" and application.status == "selected":
        offer = issue_offer(db, offer, admin)
    if join and offer.status == "issued":
        offer = respond_to_offer(db, offer, student_user, "accepted")
    if join and offer.status == "accepted" and application.status == "offered":
        db.expire(application, ["offers"])
        _move(db, application, admin, "JOINED")
    return offer


def _seed_application_progress(db: Session, application: Application, student_user: User, admin: User,
                               interviewer: User, ordinal: int) -> None:
    stage = ordinal % 10
    requires_interview = stage in {1, 2, 4, 5, 6, 7, 9}
    interview_result = "FAILED" if stage == 9 else ("PASSED" if stage in {2, 4, 5, 6} else None)

    if application.status == "applied":
        if stage in {0, 8}:
            return
        if stage == 3:
            _move(db, application, admin, "REJECTED")
            return
        _move(db, application, admin, "SHORTLISTED")

    if requires_interview:
        _ensure_interview(db, application, interviewer, ordinal, interview_result)

    if stage in {1, 7}:
        return
    if stage == 9:
        if application.status == "shortlisted":
            _move(db, application, admin, "INTERVIEW")
        if application.status == "interview":
            _move(db, application, admin, "REJECTED")
        return
    if stage == 2:
        if application.status == "shortlisted":
            _move(db, application, admin, "INTERVIEW")
        return

    if application.status == "shortlisted":
        _move(db, application, admin, "INTERVIEW")
    if application.status == "interview":
        _move(db, application, admin, "SELECTED")
    if stage == 4:
        return
    if application.status == "selected":
        _ensure_offer(db, application, admin, student_user, ordinal, join=(stage == 6))
    elif application.status in {"offered", "joined"}:
        _ensure_offer(db, application, admin, student_user, ordinal, join=(stage == 6))


def seed_demo_data(session_factory: sessionmaker | Callable[[], Session] | None = None) -> dict[str, int]:
    """Upsert fictional demo records without deleting or resetting existing data."""
    passwords = {
        "admin": _configured_password("demo_admin_password"),
        "student": _configured_password("demo_student_password"),
        "recruiter": _configured_password("demo_recruiter_password"),
        "interviewer": _configured_password("demo_interviewer_password"),
    }
    factory = session_factory or get_session_factory()
    now = datetime.now(timezone.utc)

    with factory() as db:
        admin = _upsert_user(db, DEMO_ADMIN_EMAIL, "Demo Placement Administrator", "admin", passwords["admin"])
        db.commit()

        companies = [_upsert_company(db, admin, data) for data in COMPANY_DATA]
        db.commit()
        recruiter = _upsert_user(db, DEMO_RECRUITER_EMAIL, "Jordan Park (Demo Recruiter)", "recruiter", passwords["recruiter"], companies[0].id)
        interviewer = _upsert_user(db, DEMO_INTERVIEWER_EMAIL, "Casey Morgan (Demo Interviewer)", "interviewer", passwords["interviewer"])

        skills: dict[str, Skill] = {}
        for name in SKILL_NAMES:
            skill = db.scalar(select(Skill).where(Skill.name.ilike(name)))
            if skill is None:
                skill = Skill(name=name)
                db.add(skill)
                db.flush()
            skills[name.casefold()] = skill
        db.commit()

        students: list[tuple[User, Student]] = []
        for index in range(30):
            students.append(_upsert_student(db, index, passwords["student"], skills))
        db.commit()

        drives = [_upsert_drive(db, companies[data[0]], index, now) for index, data in enumerate(JOB_DATA)]
        db.commit()
        for index, drive in enumerate(drives):
            if index < 6 and drive.status == "draft":
                transition_job_drive(db, drive, "published")
            elif index == 7 and drive.status == "draft":
                transition_job_drive(db, drive, "published")
                drive = db.get(JobDrive, drive.id)
                transition_job_drive(db, drive, "closed")

        applications_created = 0
        applications_seen = 0
        for student_index, (student_user, student) in enumerate(students):
            if student_index >= 20:
                continue
            assigned_drive_indices = (student_index % 6, (student_index + 3) % 6)
            for drive_index in assigned_drive_indices:
                drive = drives[drive_index]
                existing = db.scalar(select(Application).where(
                    Application.student_id == student.id, Application.job_drive_id == drive.id,
                ))
                application = _application_for(db, student, drive, student_user)
                if application is None:
                    continue
                applications_seen += 1
                if existing is None:
                    applications_created += 1
                _seed_application_progress(db, application, student_user, admin, interviewer, applications_seen + 4)

        db.commit()
        return {
            "students": len(students), "companies": len(companies), "job_drives": len(drives),
            "skills": len(SKILL_NAMES), "applications_created_this_run": applications_created,
            "demo_applications": applications_seen,
            "interviews": db.scalar(select(func.count(Interview.id))) or 0,
            "offers": db.scalar(select(func.count(Offer.id))) or 0,
        }


def main() -> None:
    if not settings.demo_seed_enabled:
        raise SystemExit("Demo seeding is disabled. Set DEMO_SEED_ENABLED=true in your local environment first.")
    counts = seed_demo_data()
    print("Demo data is ready (all people, employers, roles, and records are fictional).")
    for name, value in counts.items():
        print(f"{name}: {value}")
    print("Demo login emails:")
    print(f"  ADMIN: {DEMO_ADMIN_EMAIL} (password from DEMO_ADMIN_PASSWORD)")
    print(f"  STUDENT: {DEMO_STUDENT_EMAIL} (password from DEMO_STUDENT_PASSWORD)")
    print(f"  RECRUITER: {DEMO_RECRUITER_EMAIL} (password from DEMO_RECRUITER_PASSWORD)")
    print(f"  INTERVIEWER: {DEMO_INTERVIEWER_EMAIL} (password from DEMO_INTERVIEWER_PASSWORD)")


if __name__ == "__main__":
    main()
