"""add application workflow and status history

Revision ID: 3c7a1b9e5d21
Revises: 868f83a9e574
Create Date: 2026-09-25 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c7a1b9e5d21"
down_revision: Union[str, None] = "868f83a9e574"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_applications_status"), "applications", type_="check")
    op.execute("UPDATE applications SET status = 'shortlisted' WHERE status = 'under_review'")
    op.execute("UPDATE applications SET status = 'rejected' WHERE status = 'withdrawn'")
    op.create_check_constraint(
        op.f("ck_applications_status"),
        "applications",
        "status IN ('applied', 'shortlisted', 'rejected', 'interview', 'selected', 'offered', 'joined')",
    )
    op.create_table(
        "application_status_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status IN ('applied', 'shortlisted', 'rejected', 'interview', 'selected', 'offered', 'joined')",
            name=op.f("ck_application_status_events_from_status"),
        ),
        sa.CheckConstraint(
            "to_status IN ('applied', 'shortlisted', 'rejected', 'interview', 'selected', 'offered', 'joined')",
            name=op.f("ck_application_status_events_to_status"),
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name=op.f("fk_application_status_events_application_id_applications"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name=op.f("fk_application_status_events_actor_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_status_events")),
    )
    op.create_index(
        "ix_application_status_events_application_created",
        "application_status_events",
        ["application_id", "created_at"],
        unique=False,
    )
    op.execute(
        """INSERT INTO application_status_events (application_id, from_status, to_status, actor_user_id, note, created_at)
           SELECT id, NULL, status, NULL, 'Status recorded during application workflow migration.', applied_at
           FROM applications"""
    )


def downgrade() -> None:
    op.drop_index("ix_application_status_events_application_created", table_name="application_status_events")
    op.drop_table("application_status_events")
    op.drop_constraint(op.f("ck_applications_status"), "applications", type_="check")
    op.execute("UPDATE applications SET status = 'under_review' WHERE status = 'interview'")
    op.execute("UPDATE applications SET status = 'selected' WHERE status IN ('offered', 'joined')")
    op.create_check_constraint(
        op.f("ck_applications_status"),
        "applications",
        "status IN ('applied', 'under_review', 'shortlisted', 'rejected', 'selected', 'withdrawn')",
    )
