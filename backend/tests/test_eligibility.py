from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.eligibility import evaluate_eligibility


def skill(name: str, *, required: bool = True):
    return SimpleNamespace(skill=SimpleNamespace(name=name), is_required=required)


def drive(**updates):
    values = {
        "min_cgpa": Decimal("7.5"),
        "max_backlogs": 1,
        "allowed_branches": ["Computer Science", "Information Technology"],
        "graduation_year": 2027,
        "skill_links": [skill("Python"), skill("SQL")],
    }
    values.update(updates)
    return SimpleNamespace(**values)


def student(**updates):
    values = {
        "cgpa": Decimal("8.0"),
        "backlogs": 0,
        "branch": "Computer Science",
        "graduation_year": 2027,
        "skill_links": [skill("python"), skill("SQL")],
    }
    values.update(updates)
    return SimpleNamespace(**values)


def test_student_meeting_every_criterion_is_eligible():
    result = evaluate_eligibility(student(), drive())
    assert result.model_dump() == {"eligible": True, "reasons": []}


def test_all_failed_criteria_are_reported_together():
    result = evaluate_eligibility(
        student(
            cgpa=Decimal("6.9"),
            backlogs=2,
            branch="Physics",
            graduation_year=2028,
            skill_links=[skill("Java")],
        ),
        drive(),
    )
    assert result.eligible is False
    assert len(result.reasons) == 5
    assert any("Minimum CGPA required is 7.5" in reason for reason in result.reasons)
    assert any("student has 2 backlogs" in reason for reason in result.reasons)
    assert any("Branch Physics is not allowed" in reason for reason in result.reasons)
    assert any("Graduation year 2027 is required" in reason for reason in result.reasons)
    assert any("Missing required skills: Python, SQL" in reason for reason in result.reasons)


def test_missing_student_profile_fails_closed_when_criteria_exist():
    result = evaluate_eligibility(None, drive())
    assert result.eligible is False
    assert result.reasons == ["Student profile is missing."]


def test_missing_job_requirements_do_not_disqualify_a_student():
    result = evaluate_eligibility(
        None,
        drive(min_cgpa=None, max_backlogs=None, allowed_branches=None, graduation_year=None, skill_links=[]),
    )
    assert result.eligible is True
    assert result.reasons == []


def test_empty_skill_requirements_do_not_require_student_skills():
    result = evaluate_eligibility(student(skill_links=[]), drive(skill_links=[]))
    assert result.eligible is True
    assert result.reasons == []


def test_missing_academic_fields_report_each_configured_requirement():
    result = evaluate_eligibility(
        student(cgpa=None, backlogs=None, branch=None, graduation_year=None, skill_links=[]),
        drive(),
    )
    assert result.eligible is False
    assert result.reasons == [
        "Student CGPA is missing.",
        "Student backlog information is missing.",
        "Student branch is missing.",
        "Student graduation year is missing.",
        "Student skills are missing; required skills: Python, SQL.",
    ]


def test_branch_and_skill_comparisons_ignore_letter_case():
    result = evaluate_eligibility(
        student(branch="computer science", skill_links=[skill("python"), skill("sql")]),
        drive(),
    )
    assert result.eligible is True


@pytest.mark.parametrize(
    ("criteria", "student_changes"),
    [
        ({"min_cgpa": None}, {"cgpa": None}),
        ({"max_backlogs": None}, {"backlogs": 99}),
        ({"allowed_branches": []}, {"branch": None}),
        ({"graduation_year": None}, {"graduation_year": None}),
        ({"skill_links": []}, {"skill_links": []}),
    ],
)
def test_unconfigured_criterion_is_not_evaluated(criteria, student_changes):
    result = evaluate_eligibility(student(**student_changes), drive(**criteria))
    assert result.eligible is True
    assert result.reasons == []
