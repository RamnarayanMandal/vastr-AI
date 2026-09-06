"""initial

Revision ID: 001_initial
Revises:
Create Date: 2026-09-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("mobile", sa.String(20), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_mobile", "users", ["mobile"])

    op.create_table(
        "media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("imagekit_file_id", sa.String(120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_media_assets_user_id", "media_assets", ["user_id"])

    op.create_table(
        "try_on_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("person_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_assets.id"), nullable=False),
        sa.Column("fabric_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_assets.id"), nullable=False),
        sa.Column("garment_type", sa.String(60), nullable=False),
        sa.Column("garment_style", sa.String(60), nullable=False),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),
        sa.Column("provider", sa.String(60), nullable=True),
        sa.Column("model_version", sa.String(120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("max_retries", sa.Integer(), server_default="2"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_try_on_jobs_user_id", "try_on_jobs", ["user_id"])
    op.create_index("ix_try_on_jobs_status", "try_on_jobs", ["status"])

    op.create_table(
        "try_on_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("try_on_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("try_on_jobs.id"), nullable=False),
        sa.Column("result_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_assets.id"), nullable=False),
        sa.Column("result_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_try_on_results_try_on_job_id", "try_on_results", ["try_on_job_id"])


def downgrade() -> None:
    op.drop_table("try_on_results")
    op.drop_table("try_on_jobs")
    op.drop_table("media_assets")
    op.drop_table("users")
