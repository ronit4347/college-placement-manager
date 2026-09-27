"""backfill student profiles for existing student accounts

Revision ID: 5ac0f4e73b12
Revises: 2b7b3cbf2421
Create Date: 2026-09-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5ac0f4e73b12"
down_revision: Union[str, None] = "2b7b3cbf2421"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO students (user_id)
            SELECT users.id
            FROM users
            LEFT JOIN students ON students.user_id = users.id
            WHERE users.role = 'student' AND students.id IS NULL
            """
        )
    )


def downgrade() -> None:
    # The rows may have been completed with real profile information after upgrade.
    pass
