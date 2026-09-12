"""create integrations table

Revision ID: b3883f5336cd
Revises:
Create Date: 2026-09-12 14:09:49.587598

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3883f5336cd"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column(
            "auth_type",
            sa.Enum(
                "NONE",
                "API_KEY",
                "BEARER_TOKEN",
                "OAUTH2_CLIENT_CREDENTIALS",
                name="authtype",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("default_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "PAUSED", name="integrationstatus", native_enum=False, length=40),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("integrations")
