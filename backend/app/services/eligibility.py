"""Reusable placement eligibility evaluation for a student and job drive."""

from decimal import Decimal

from app.models import JobDrive, Student
from app.schemas.eligibility import EligibilityResponse


def evaluate_eligibility(student: Student | None, job_drive: JobDrive) -> EligibilityResponse:
    """Evaluate every configured criterion and return all failures.

    Missing criteria impose no restriction. When criteria exist, missing student
    data fails closed with a field-specific reason so incomplete profiles cannot
    be presented as eligible.
    """
    required_skills = sorted(
        (link.skill.name.strip() for link in (job_drive.skill_links or []) if link.is_required),
        key=str.casefold,
    )
    branches = [branch.strip() for branch in (job_drive.allowed_branches or []) if branch.strip()]
    has_requirements = any(
        (
            job_drive.min_cgpa is not None,
            job_drive.max_backlogs is not None,
            bool(branches),
            job_drive.graduation_year is not None,
            bool(required_skills),
        )
    )
    if student is None:
        return EligibilityResponse(
            eligible=not has_requirements,
            reasons=["Student profile is missing."] if has_requirements else [],
        )

    reasons: list[str] = []
    if job_drive.min_cgpa is not None:
        if student.cgpa is None:
            reasons.append("Student CGPA is missing.")
        elif Decimal(str(student.cgpa)) < Decimal(str(job_drive.min_cgpa)):
            reasons.append(f"Minimum CGPA required is {job_drive.min_cgpa}; student has {student.cgpa}.")

    if job_drive.max_backlogs is not None:
        if student.backlogs is None:
            reasons.append("Student backlog information is missing.")
        elif student.backlogs > job_drive.max_backlogs:
            reasons.append(
                f"Maximum backlogs allowed is {job_drive.max_backlogs}; student has {student.backlogs} backlogs."
            )

    if branches:
        if not student.branch or not student.branch.strip():
            reasons.append("Student branch is missing.")
        elif student.branch.strip().casefold() not in {branch.casefold() for branch in branches}:
            reasons.append(f"Branch {student.branch.strip()} is not allowed.")

    if job_drive.graduation_year is not None:
        if student.graduation_year is None:
            reasons.append("Student graduation year is missing.")
        elif student.graduation_year != job_drive.graduation_year:
            reasons.append(f"Graduation year {job_drive.graduation_year} is required.")

    if required_skills:
        student_skills = {
            link.skill.name.strip().casefold()
            for link in (student.skill_links or [])
            if link.skill and link.skill.name.strip()
        }
        if not student_skills:
            reasons.append(f"Student skills are missing; required skills: {', '.join(required_skills)}.")
        else:
            missing = [skill for skill in required_skills if skill.casefold() not in student_skills]
            if missing:
                reasons.append(f"Missing required skills: {', '.join(missing)}.")

    return EligibilityResponse(eligible=not reasons, reasons=reasons)
