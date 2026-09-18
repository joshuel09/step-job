"""user story 1 sections

Revision ID: e541dac9bd2f
Revises: 0001
Create Date: 2026-09-18 20:29:35.592515
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e541dac9bd2f'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The 'locale' type is created by revision 0001, so every column that uses it
    # references it with create_type=False rather than creating it again.
    op.create_table('career_preference',
    sa.Column('desired_roles', postgresql.ARRAY(sa.String()), nullable=False),
    sa.Column('desired_locations', postgresql.ARRAY(sa.String()), nullable=False),
    sa.Column('working_arrangement', sa.Enum('onsite', 'hybrid', 'remote', name='working_arrangement'), nullable=True),
    sa.Column('salary_min', sa.Integer(), nullable=True),
    sa.Column('salary_max', sa.Integer(), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('source_language', postgresql.ENUM('en', 'ja', name='locale', create_type=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_career_preference_profile_id'), 'career_preference', ['profile_id'], unique=False)
    op.create_table('certification',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('issuer', sa.String(length=255), nullable=True),
    sa.Column('issued_on', sa.Date(), nullable=True),
    sa.Column('expires_on', sa.Date(), nullable=True),
    sa.Column('source_language', postgresql.ENUM('en', 'ja', name='locale', create_type=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_certification_profile_id'), 'certification', ['profile_id'], unique=False)
    op.create_table('education',
    sa.Column('institution', sa.String(length=255), nullable=False),
    sa.Column('qualification', sa.String(length=255), nullable=True),
    sa.Column('field_of_study', sa.String(length=255), nullable=True),
    sa.Column('started_on', sa.Date(), nullable=True),
    sa.Column('ended_on', sa.Date(), nullable=True),
    sa.Column('source_language', postgresql.ENUM('en', 'ja', name='locale', create_type=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_education_profile_id'), 'education', ['profile_id'], unique=False)
    op.create_table('identity',
    sa.Column('full_name_latin', sa.String(length=255), nullable=False),
    sa.Column('full_name_japanese', sa.String(length=255), nullable=True),
    sa.Column('furigana', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_identity_profile_id'), 'identity', ['profile_id'], unique=False)
    op.create_table('japan_profile',
    sa.Column('residence_status', sa.String(length=255), nullable=True),
    sa.Column('nationality', sa.String(length=255), nullable=True),
    sa.Column('visa_type', sa.String(length=255), nullable=True),
    sa.Column('visa_expires_on', sa.Date(), nullable=True),
    sa.Column('work_authorisation', sa.Boolean(), nullable=True),
    sa.Column('japanese_qualification', sa.String(length=255), nullable=True),
    sa.Column('disclose_residence_status', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('disclose_nationality', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('disclose_visa', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('disclose_work_authorisation', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('disclose_japanese_qualification', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_japan_profile_profile_id'), 'japan_profile', ['profile_id'], unique=False)
    op.create_table('language',
    sa.Column('language', sa.String(length=100), nullable=False),
    sa.Column('proficiency', sa.Enum('native', 'business', 'conversational', 'basic', name='language_proficiency'), nullable=False),
    sa.Column('qualification', sa.String(length=255), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_language_profile_id'), 'language', ['profile_id'], unique=False)
    op.create_table('skill',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('level', sa.Enum('beginner', 'intermediate', 'advanced', 'expert', name='skill_level'), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skill_profile_id'), 'skill', ['profile_id'], unique=False)
    op.create_table('work_experience',
    sa.Column('employer_name', sa.String(length=255), nullable=False),
    sa.Column('employer_name_normalised', sa.String(length=255), nullable=False),
    sa.Column('job_title', sa.String(length=255), nullable=False),
    sa.Column('employment_type', sa.Enum('permanent', 'contract', 'part_time', 'internship', 'freelance', name='employment_type'), nullable=True),
    sa.Column('started_on', sa.Date(), nullable=False),
    sa.Column('ended_on', sa.Date(), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('source_language', postgresql.ENUM('en', 'ja', name='locale', create_type=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_experience_employer_name_normalised'), 'work_experience', ['employer_name_normalised'], unique=False)
    op.create_index(op.f('ix_work_experience_profile_id'), 'work_experience', ['profile_id'], unique=False)
    op.create_table('career_story',
    sa.Column('work_experience_id', sa.Uuid(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('challenge', sa.Text(), nullable=False),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('result', sa.Text(), nullable=False),
    sa.Column('source_language', postgresql.ENUM('en', 'ja', name='locale', create_type=False), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['career_profile.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['work_experience_id'], ['work_experience.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_career_story_profile_id'), 'career_story', ['profile_id'], unique=False)
    op.create_index(op.f('ix_career_story_work_experience_id'), 'career_story', ['work_experience_id'], unique=False)
    op.create_table('skill_experience',
    sa.Column('skill_id', sa.Uuid(), nullable=False),
    sa.Column('work_experience_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['skill_id'], ['skill.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['work_experience_id'], ['work_experience.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('skill_id', 'work_experience_id')
    )
    op.alter_column('career_profile', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('career_profile', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('entry_snapshot', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('entry_snapshot', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('entry_snapshot', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('entry_snapshot', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('career_profile', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('career_profile', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_table('skill_experience')
    op.drop_index(op.f('ix_career_story_work_experience_id'), table_name='career_story')
    op.drop_index(op.f('ix_career_story_profile_id'), table_name='career_story')
    op.drop_table('career_story')
    op.drop_index(op.f('ix_work_experience_profile_id'), table_name='work_experience')
    op.drop_index(op.f('ix_work_experience_employer_name_normalised'), table_name='work_experience')
    op.drop_table('work_experience')
    op.drop_index(op.f('ix_skill_profile_id'), table_name='skill')
    op.drop_table('skill')
    op.drop_index(op.f('ix_language_profile_id'), table_name='language')
    op.drop_table('language')
    op.drop_index(op.f('ix_japan_profile_profile_id'), table_name='japan_profile')
    op.drop_table('japan_profile')
    op.drop_index(op.f('ix_identity_profile_id'), table_name='identity')
    op.drop_table('identity')
    op.drop_index(op.f('ix_education_profile_id'), table_name='education')
    op.drop_table('education')
    op.drop_index(op.f('ix_certification_profile_id'), table_name='certification')
    op.drop_table('certification')
    op.drop_index(op.f('ix_career_preference_profile_id'), table_name='career_preference')
    op.drop_table('career_preference')
