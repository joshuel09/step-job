"""Career profile and entry snapshot

Revision ID: 0001
Revises:
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "interface_locale",
            sa.Enum("en", "ja", name="locale"),
            nullable=False,
            server_default="en",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # The purge job sweeps by this column; every other read filters on deleted_at.
    op.create_index("ix_career_profile_purge_after", "career_profile", ["purge_after"])

    op.create_table(
        "entry_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("career_profile.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_ref", sa.String(255), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "captured_entry_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_entry_snapshot_profile_id", "entry_snapshot", ["profile_id"])


def downgrade() -> None:
    op.drop_table("entry_snapshot")
    op.drop_table("career_profile")
    sa.Enum(name="locale").drop(op.get_bind(), checkfirst=True)
