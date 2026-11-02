"""english renderings and supplied english names

Two kinds of English, stored differently on purpose. An approved rendering of
something the user wrote goes in `entry_translation`, with a digest of the
source as it read at approval so staleness is detectable. A name the user
states — a company's or a university's own English name — is a column on the
entry it belongs to, because nothing drafts it.

No backfill. A migration that filled the four name columns by transliterating
the Japanese would be the invention FR-021 forbids, performed once and
invisibly, and the user would never know it had happened.

Revision ID: 0f5c987b01c8
Revises: 9bb1dd002f90
Create Date: 2026-11-02 17:50:26.835465
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0f5c987b01c8"
down_revision: str | None = "9bb1dd002f90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# This feature's own type: created and dropped here, so the migration can be
# run down and up again. Alembic's `drop_table` leaves a PostgreSQL enum
# behind, and the second upgrade then fails on a type that already exists.
TRANSLATABLE_ENTRY = postgresql.ENUM(
    "work_experience",
    "education",
    "career_story",
    "skill",
    name="translatable_entry",
    create_type=False,
)

# Already created by an earlier migration and used by several tables.
# `create_type=False` keeps `create_table` from emitting CREATE TYPE for it,
# which is what made the generated version of this migration fail on a
# database that had ever run the others.
LOCALE = postgresql.ENUM("en", "ja", name="locale", create_type=False)


def upgrade() -> None:
    TRANSLATABLE_ENTRY.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "entry_translation",
        sa.Column("entry_type", TRANSLATABLE_ENTRY, nullable=False),
        # Not a foreign key: it points at one of four tables depending on
        # entry_type, and there is no referential integrity across a
        # discriminated reference. The service removes translations when an
        # entry goes, and a test per entry type stands in for the key.
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("language", LOCALE, nullable=False),
        sa.Column("approved_text", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["career_profile.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "entry_type",
            "entry_id",
            "field",
            "language",
            name="uq_entry_translation_field",
        ),
    )
    op.create_index(
        op.f("ix_entry_translation_profile_id"), "entry_translation", ["profile_id"], unique=False
    )
    op.create_index(
        "ix_entry_translation_profile_language",
        "entry_translation",
        ["profile_id", "language"],
        unique=False,
    )

    # Nullable with no default. Null means the user has not supplied an
    # English name, and a document prints the name as recorded.
    op.add_column("certification", sa.Column("name_english", sa.String(length=255), nullable=True))
    op.add_column(
        "certification", sa.Column("issuer_english", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "education", sa.Column("institution_english", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "work_experience", sa.Column("employer_name_english", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("work_experience", "employer_name_english")
    op.drop_column("education", "institution_english")
    op.drop_column("certification", "issuer_english")
    op.drop_column("certification", "name_english")
    op.drop_index("ix_entry_translation_profile_language", table_name="entry_translation")
    op.drop_index(op.f("ix_entry_translation_profile_id"), table_name="entry_translation")
    op.drop_table("entry_translation")

    # `locale` stays: other tables use it. This feature's own type goes, or
    # the next upgrade fails on a type that already exists.
    TRANSLATABLE_ENTRY.drop(op.get_bind(), checkfirst=True)
