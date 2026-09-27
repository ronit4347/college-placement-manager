"""Core placement domain tables and their relational constraints."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('student', 'admin', 'recruiter', 'interviewer')", name="role"),
        CheckConstraint("role != 'recruiter' OR company_id IS NOT NULL", name="recruiter_company_required"),
        Index("ix_users_role", "role"),
        Index("ix_users_company_id", "company_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_users_company_id_companies",
        )
    )

    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    created_companies: Mapped[list["Company"]] = relationship(
        back_populates="created_by", foreign_keys="Company.created_by_user_id"
    )
    company: Mapped["Company | None"] = relationship(back_populates="recruiters", foreign_keys=[company_id])
    assigned_interviews: Mapped[list["Interview"]] = relationship(back_populates="interviewer")
    application_status_events: Mapped[list["ApplicationStatusEvent"]] = relationship(back_populates="actor")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("type IN ('application_submitted', 'application_shortlisted', 'application_rejected', 'interview_scheduled', 'interview_rescheduled', 'interview_result', 'candidate_selected', 'offer_issued')", name="type"),
        Index("ix_notifications_user_read_created", "user_id", "read_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    link: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="notifications")


class Student(TimestampMixin, Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_students_user_id"),
        UniqueConstraint("student_number", name="uq_students_student_number"),
        CheckConstraint("cgpa >= 0 AND cgpa <= 10", name="cgpa_range"),
        CheckConstraint("backlogs >= 0", name="backlogs_nonnegative"),
        CheckConstraint("graduation_year >= 2000", name="graduation_year"),
        Index("ix_students_graduation_year_branch", "graduation_year", "branch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_number: Mapped[str | None] = mapped_column(String(40))
    branch: Mapped[str | None] = mapped_column(String(120))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    cgpa: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    backlogs: Mapped[int | None] = mapped_column(Integer)
    phone: Mapped[str | None] = mapped_column(String(32))
    resume_url: Mapped[str | None] = mapped_column(String(2048))

    user: Mapped[User] = relationship(back_populates="student")
    applications: Mapped[list["Application"]] = relationship(back_populates="student")
    skill_links: Mapped[list["StudentSkill"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("name", name="uq_companies_name"),
        Index("ix_companies_is_active", "is_active"),
        Index("ix_companies_industry", "industry"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str | None] = mapped_column(String(2048))
    industry: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(200))
    hr_name: Mapped[str | None] = mapped_column(String(160))
    hr_email: Mapped[str | None] = mapped_column(String(320))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_by: Mapped[User | None] = relationship(
        back_populates="created_companies", foreign_keys=[created_by_user_id]
    )
    job_drives: Mapped[list["JobDrive"]] = relationship(back_populates="company")
    recruiters: Mapped[list[User]] = relationship(back_populates="company", foreign_keys="User.company_id")


class JobDrive(TimestampMixin, Base):
    __tablename__ = "job_drives"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'closed', 'cancelled')", name="status"),
        CheckConstraint("min_cgpa IS NULL OR (min_cgpa >= 0 AND min_cgpa <= 10)", name="min_cgpa"),
        CheckConstraint("max_backlogs IS NULL OR max_backlogs >= 0", name="max_backlogs"),
        CheckConstraint("graduation_year IS NULL OR graduation_year >= 2000", name="graduation_year"),
        CheckConstraint("compensation_min IS NULL OR compensation_min >= 0", name="compensation_min_nonnegative"),
        CheckConstraint("compensation_max IS NULL OR compensation_max >= 0", name="compensation_max_nonnegative"),
        CheckConstraint(
            "compensation_min IS NULL OR compensation_max IS NULL OR compensation_min <= compensation_max",
            name="compensation_range",
        ),
        Index("ix_job_drives_status_deadline", "status", "application_deadline"),
        Index("ix_job_drives_company_id", "company_id"),
        Index("ix_job_drives_company_status", "company_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    employment_type: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    min_cgpa: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    max_backlogs: Mapped[int | None] = mapped_column(Integer)
    allowed_branches: Mapped[list[str] | None] = mapped_column(JSON)
    compensation_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    compensation_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    company: Mapped[Company] = relationship(back_populates="job_drives")
    applications: Mapped[list["Application"]] = relationship(back_populates="job_drive")
    skill_links: Mapped[list["JobSkill"]] = relationship(back_populates="job_drive", cascade="all, delete-orphan")


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("student_id", "job_drive_id", name="uq_applications_student_job_drive"),
        CheckConstraint(
            "status IN ('applied', 'shortlisted', 'rejected', 'interview', 'selected', 'offered', 'joined')",
            name="status",
        ),
        Index("ix_applications_job_drive_status", "job_drive_id", "status"),
        Index("ix_applications_student_created", "student_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    job_drive_id: Mapped[int] = mapped_column(ForeignKey("job_drives.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="applied", server_default="applied")
    cover_letter: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    student: Mapped[Student] = relationship(back_populates="applications")
    job_drive: Mapped[JobDrive] = relationship(back_populates="applications")
    interviews: Mapped[list["Interview"]] = relationship(back_populates="application")
    offers: Mapped[list["Offer"]] = relationship(back_populates="application", order_by="Offer.created_at")
    status_events: Mapped[list["ApplicationStatusEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by=lambda: (ApplicationStatusEvent.created_at, ApplicationStatusEvent.id),
    )


class ApplicationStatusEvent(Base):
    __tablename__ = "application_status_events"
    __table_args__ = (
        CheckConstraint(
            "from_status IS NULL OR from_status IN ('applied', 'shortlisted', 'rejected', 'interview', 'selected', 'offered', 'joined')",
            name="from_status",
        ),
        CheckConstraint(
            "to_status IN ('applied', 'shortlisted', 'rejected', 'interview', 'selected', 'offered', 'joined')",
            name="to_status",
        ),
        Index("ix_application_status_events_application_created", "application_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="status_events")
    actor: Mapped[User | None] = relationship(back_populates="application_status_events")


class Interview(TimestampMixin, Base):
    __tablename__ = "interviews"
    __table_args__ = (
        CheckConstraint("round_name IN ('aptitude', 'technical', 'managerial', 'hr')", name="round_name"),
        CheckConstraint("status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')", name="status"),
        CheckConstraint("result IN ('pending', 'passed', 'failed')", name="result"),
        CheckConstraint("duration_minutes BETWEEN 15 AND 240", name="duration_range"),
        Index("ix_interviews_interviewer_schedule", "interviewer_user_id", "scheduled_at"),
        Index("ix_interviews_application_schedule", "application_id", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="RESTRICT"), nullable=False)
    round_name: Mapped[str] = mapped_column(String(24), nullable=False, default="technical", server_default="technical")
    interviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60, server_default="60")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled", server_default="scheduled")
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    feedback: Mapped[str | None] = mapped_column(Text)

    application: Mapped[Application] = relationship(back_populates="interviews")
    interviewer: Mapped[User | None] = relationship(back_populates="assigned_interviews")


class Offer(TimestampMixin, Base):
    __tablename__ = "offers"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'issued', 'accepted', 'declined', 'expired')", name="status"),
        CheckConstraint("salary IS NULL OR salary >= 0", name="salary_nonnegative"),
        Index("ix_offers_status", "status"),
        Index("uq_offers_application_active", "application_id", unique=True,
              postgresql_where=text("status IN ('draft', 'issued')"),
              sqlite_where=text("status IN ('draft', 'issued')")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="RESTRICT"), nullable=False)
    salary: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    joining_date: Mapped[date | None] = mapped_column(Date)
    offer_letter_reference: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    application: Mapped[Application] = relationship(back_populates="offers")


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("name", name="uq_skills_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    student_links: Mapped[list["StudentSkill"]] = relationship(back_populates="skill", cascade="all, delete-orphan")
    job_links: Mapped[list["JobSkill"]] = relationship(back_populates="skill", cascade="all, delete-orphan")


class StudentSkill(TimestampMixin, Base):
    __tablename__ = "student_skills"
    __table_args__ = (
        UniqueConstraint("student_id", "skill_id", name="uq_student_skills_student_skill"),
        Index("ix_student_skills_skill_id", "skill_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    proficiency: Mapped[str | None] = mapped_column(String(40))

    student: Mapped[Student] = relationship(back_populates="skill_links")
    skill: Mapped[Skill] = relationship(back_populates="student_links")


class JobSkill(TimestampMixin, Base):
    __tablename__ = "job_skills"
    __table_args__ = (
        UniqueConstraint("job_drive_id", "skill_id", name="uq_job_skills_job_skill"),
        Index("ix_job_skills_skill_id", "skill_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_drive_id: Mapped[int] = mapped_column(ForeignKey("job_drives.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    job_drive: Mapped[JobDrive] = relationship(back_populates="skill_links")
    skill: Mapped[Skill] = relationship(back_populates="job_links")
