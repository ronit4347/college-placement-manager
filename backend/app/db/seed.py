"""Seed a small, repeatable set of common skills for local development."""

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models import Skill

DEVELOPMENT_SKILLS = (
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "SQL",
    "PostgreSQL",
    "React",
    "FastAPI",
    "Communication",
)


def seed_development_data() -> int:
    """Insert missing development skills and return the number added."""
    session_factory = get_session_factory()
    inserted = 0
    with session_factory.begin() as session:
        present = set(session.scalars(select(Skill.name)).all())
        new_skills = [Skill(name=name) for name in DEVELOPMENT_SKILLS if name not in present]
        session.add_all(new_skills)
        inserted = len(new_skills)
    return inserted


if __name__ == "__main__":
    print(f"Inserted {seed_development_data()} development skills.")
