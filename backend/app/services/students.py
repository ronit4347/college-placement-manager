from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import hash_password
from app.models import Application, Skill, Student, StudentSkill, User
from app.schemas.students import (
    StudentAdminCreate,
    StudentProfileResponse,
    AdminStudentResponse,
    StudentProfileUpdate,
    StudentSkillsUpdate,
)


def get_student_for_user(db: Session, user: User) -> Student | None:
    return db.scalar(
        select(Student)
        .where(Student.user_id == user.id)
        .options(selectinload(Student.skill_links).selectinload(StudentSkill.skill))
    )


def get_or_create_student(db: Session, user: User) -> Student:
    student = get_student_for_user(db, user)
    if student is None:
        student = Student(user=user)
        db.add(student)
        db.flush()
    return student


def profile_response(user: User, student: Student | None) -> StudentProfileResponse:
    skills = sorted((link.skill.name for link in student.skill_links), key=str.casefold) if student else []
    fields = [
        bool(user.full_name),
        bool(user.email),
        bool(student and student.phone),
        bool(student and student.student_number),
        bool(student and student.branch),
        bool(student and student.cgpa is not None),
        bool(student and student.graduation_year is not None),
        bool(student and student.backlogs is not None),
        bool(skills),
        bool(student and student.resume_url),
    ]
    return StudentProfileResponse(
        student_id=student.id if student else None,
        full_name=user.full_name,
        email=user.email,
        phone=student.phone if student else None,
        roll_number=student.student_number if student else None,
        branch=student.branch if student else None,
        cgpa=student.cgpa if student else None,
        graduation_year=student.graduation_year if student else None,
        backlogs=student.backlogs if student else None,
        skills=skills,
        resume_filename=student.resume_url if student else None,
        resume_max_size_bytes=settings.max_resume_size_bytes,
        profile_completion=round(sum(fields) / len(fields) * 100),
        created_at=student.created_at if student else None,
        updated_at=student.updated_at if student else None,
    )


def _apply_profile_values(user: User, student: Student, values: dict) -> None:
    if "full_name" in values:
        user.full_name = values["full_name"]
    if "email" in values:
        user.email = values["email"]
    for field, column in (
        ("phone", "phone"),
        ("roll_number", "student_number"),
        ("branch", "branch"),
        ("cgpa", "cgpa"),
        ("graduation_year", "graduation_year"),
        ("backlogs", "backlogs"),
    ):
        if field in values:
            setattr(student, column, values[field])


def update_own_profile(db: Session, user: User, payload: StudentProfileUpdate) -> StudentProfileResponse:
    student = get_or_create_student(db, user)
    _apply_profile_values(user, student, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(user)
    db.refresh(student)
    return profile_response(user, student)


def list_students(
    db: Session,
    limit: int,
    offset: int,
    *,
    q: str | None = None,
    roll_number: str | None = None,
    branch: str | None = None,
    min_cgpa: float | None = None,
    max_cgpa: float | None = None,
    placement_status: str | None = None,
) -> list[AdminStudentResponse]:
    statement = select(User).join(Student, isouter=True).where(User.role == "student", User.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if roll_number:
        statement = statement.where(Student.student_number.ilike(f"%{roll_number.strip()}%"))
    if branch:
        statement = statement.where(Student.branch.ilike(f"%{branch.strip()}%"))
    if min_cgpa is not None:
        statement = statement.where(Student.cgpa >= min_cgpa)
    if max_cgpa is not None:
        statement = statement.where(Student.cgpa <= max_cgpa)
    if placement_status:
        status_map = {"PLACED": "joined", "JOINED": "joined", "OFFERED": "offered", "SELECTED": "selected",
                      "INTERVIEW": "interview", "SHORTLISTED": "shortlisted", "APPLIED": "applied", "REJECTED": "rejected"}
        status = status_map.get(placement_status.upper())
        if placement_status.upper() == "NOT_APPLIED":
            statement = statement.where(~exists(select(Application.id).where(Application.student_id == Student.id)))
        elif status:
            statement = statement.where(exists(select(Application.id).where(
                Application.student_id == Student.id, Application.status == status
            )))
    users = db.scalars(
        statement
        .order_by(User.id)
        .offset(offset)
        .limit(limit)
        .options(
            selectinload(User.student)
            .selectinload(Student.skill_links)
            .selectinload(StudentSkill.skill)
        )
    ).all()
    student_ids = [user.student.id for user in users if user.student]
    rank = case((Application.status == "joined", 0), (Application.status == "offered", 1),
                (Application.status == "selected", 2), (Application.status == "interview", 3),
                (Application.status == "shortlisted", 4), (Application.status == "applied", 5),
                else_=6)
    applications = db.scalars(select(Application).where(Application.student_id.in_(student_ids))
                              .order_by(rank, Application.created_at.desc())).all() if student_ids else []
    statuses: dict[int, str] = {}
    for application in applications:
        statuses.setdefault(application.student_id, "PLACED" if application.status == "joined" else application.status.upper())
    return [AdminStudentResponse(**profile_response(user, user.student).model_dump(),
                                 placement_status=statuses.get(user.student.id, "NOT_APPLIED") if user.student else "NOT_APPLIED")
            for user in users]


def get_student_by_id(db: Session, student_id: int) -> Student | None:
    return db.scalar(
        select(Student)
        .join(Student.user)
        .where(Student.id == student_id, User.is_active.is_(True))
        .options(selectinload(Student.user), selectinload(Student.skill_links).selectinload(StudentSkill.skill))
    )


def _get_or_create_skills(db: Session, names: list[str]) -> list[Skill]:
    if not names:
        return []
    folded_names = [name.casefold() for name in names]
    existing = db.scalars(select(Skill).where(func.lower(Skill.name).in_(folded_names))).all()
    by_name = {skill.name.casefold(): skill for skill in existing}
    result: list[Skill] = []
    for name in names:
        skill = by_name.get(name.casefold())
        if skill is None:
            skill = Skill(name=name)
            db.add(skill)
            by_name[name.casefold()] = skill
        result.append(skill)
    db.flush()
    return result


def replace_student_skills(
    db: Session, user: User, payload: StudentSkillsUpdate
) -> StudentProfileResponse:
    student = get_or_create_student(db, user)
    replace_skills_for_student(db, student, payload)
    db.commit()
    db.refresh(student)
    return profile_response(user, get_student_for_user(db, user))


def replace_skills_for_student(db: Session, student: Student, payload: StudentSkillsUpdate) -> None:
    student.skill_links = [StudentSkill(skill=skill) for skill in _get_or_create_skills(db, payload.skills)]


def create_student(db: Session, payload: StudentAdminCreate) -> StudentProfileResponse:
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.initial_password),
        role="student",
    )
    student = Student(
        user=user,
        student_number=payload.roll_number,
        branch=payload.branch,
        cgpa=payload.cgpa,
        graduation_year=payload.graduation_year,
        backlogs=payload.backlogs,
        phone=payload.phone,
    )
    db.add(student)
    student.skill_links = [StudentSkill(skill=skill) for skill in _get_or_create_skills(db, payload.skills)]
    db.commit()
    db.refresh(user)
    db.refresh(student)
    return profile_response(user, get_student_for_user(db, user))


def update_student(
    db: Session, student: Student, payload: StudentProfileUpdate
) -> StudentProfileResponse:
    _apply_profile_values(student.user, student, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(student.user)
    db.refresh(student)
    return profile_response(student.user, get_student_by_id(db, student.id))


def deactivate_student(db: Session, student: Student) -> None:
    student.user.is_active = False
    db.commit()


def attach_resume(db: Session, student: Student, filename: str) -> str | None:
    old_filename = student.resume_url
    student.resume_url = filename
    db.commit()
    return old_filename
