"""add interview round and rescheduled status

Revision ID: 7a84d3b21c90
Revises: 3c7a1b9e5d21
Create Date: 2026-09-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7a84d3b21c90"
down_revision: Union[str, None] = "3c7a1b9e5d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("interviews", sa.Column("round_name", sa.String(length=24), server_default="technical", nullable=False))
    op.drop_constraint(op.f("ck_interviews_status"), "interviews", type_="check")
    op.drop_constraint(op.f("ck_interviews_result"), "interviews", type_="check")
    op.drop_constraint(op.f("ck_interviews_duration_positive"), "interviews", type_="check")
    op.execute("UPDATE interviews SET result = 'failed' WHERE result = 'no_show'")
    op.create_check_constraint(op.f("ck_interviews_round_name"), "interviews", "round_name IN ('aptitude', 'technical', 'managerial', 'hr')")
    op.create_check_constraint(op.f("ck_interviews_status"), "interviews", "status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')")
    op.create_check_constraint(op.f("ck_interviews_result"), "interviews", "result IN ('pending', 'passed', 'failed')")
    op.create_check_constraint(op.f("ck_interviews_duration_range"), "interviews", "duration_minutes BETWEEN 15 AND 240")
    op.alter_column("interviews", "round_name", server_default=None)


def downgrade() -> None:
    op.drop_constraint(op.f("ck_interviews_duration_range"), "interviews", type_="check")
    op.drop_constraint(op.f("ck_interviews_result"), "interviews", type_="check")
    op.drop_constraint(op.f("ck_interviews_status"), "interviews", type_="check")
    op.drop_constraint(op.f("ck_interviews_round_name"), "interviews", type_="check")
    op.execute("UPDATE interviews SET result = 'no_show' WHERE result = 'failed'")
    op.create_check_constraint(op.f("ck_interviews_duration_positive"), "interviews", "duration_minutes > 0")
    op.create_check_constraint(op.f("ck_interviews_status"), "interviews", "status IN ('scheduled', 'completed', 'cancelled')")
    op.create_check_constraint(op.f("ck_interviews_result"), "interviews", "result IN ('pending', 'passed', 'failed', 'no_show')")
    op.drop_column("interviews", "round_name")
