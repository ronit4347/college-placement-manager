"""implement offer lifecycle and details

Revision ID: ab61c94df823
Revises: 7a84d3b21c90
Create Date: 2026-09-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "ab61c94df823"
down_revision: Union[str, None] = "7a84d3b21c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("offers", sa.Column("joining_date", sa.Date(), nullable=True))
    op.add_column("offers", sa.Column("offer_letter_reference", sa.String(length=2048), nullable=True))
    op.drop_constraint(op.f("ck_offers_status"), "offers", type_="check")
    op.drop_constraint("uq_offers_application_id", "offers", type_="unique")
    op.execute("UPDATE offers SET status = 'issued' WHERE status = 'pending'")
    op.execute("UPDATE offers SET status = 'expired' WHERE status = 'revoked'")
    op.create_check_constraint(op.f("ck_offers_status"), "offers", "status IN ('draft', 'issued', 'accepted', 'declined', 'expired')")
    op.create_index("uq_offers_application_active", "offers", ["application_id"], unique=True,
                    postgresql_where=sa.text("status IN ('draft', 'issued')"),
                    sqlite_where=sa.text("status IN ('draft', 'issued')"))
    op.alter_column("offers", "status", server_default="draft")
    op.alter_column("offers", "issued_at", nullable=True, server_default=None)


def downgrade() -> None:
    op.drop_index("uq_offers_application_active", table_name="offers")
    op.drop_constraint(op.f("ck_offers_status"), "offers", type_="check")
    op.execute("UPDATE offers SET status = 'pending' WHERE status = 'draft'")
    op.execute("UPDATE offers SET status = 'revoked' WHERE status = 'expired'")
    op.create_check_constraint(op.f("ck_offers_status"), "offers", "status IN ('pending', 'accepted', 'declined', 'revoked')")
    op.create_unique_constraint("uq_offers_application_id", "offers", ["application_id"])
    op.alter_column("offers", "status", server_default="pending")
    op.alter_column("offers", "issued_at", nullable=False, server_default=sa.func.now())
    op.drop_column("offers", "offer_letter_reference")
    op.drop_column("offers", "joining_date")
