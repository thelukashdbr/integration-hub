"""add slug to integrations

Revision ID: 642ac56c72fc
Revises: 7c2a370d7651
Create Date: 2026-09-12 14:46:10.961800

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "642ac56c72fc"
down_revision: str | None = "7c2a370d7651"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Added as nullable first so existing rows can be backfilled from `name`, the
    # same way the API derives a slug when one is not provided.
    op.add_column("integrations", sa.Column("slug", sa.String(length=100), nullable=True))
    op.execute(
        """
        UPDATE integrations
        SET slug = trim(both '-' from lower(regexp_replace(name, '[^A-Za-z0-9]+', '-', 'g')))
        """
    )
    # Two names can collapse into the same slug ("Foo!" and "Foo?"), or into nothing
    # at all; use part of the id for those so the unique constraint can be created.
    op.execute(
        """
        UPDATE integrations i
        SET slug = CASE
            WHEN i.slug = '' THEN left(i.id::text, 8)
            ELSE i.slug || '-' || left(i.id::text, 8)
        END
        WHERE i.slug = '' OR EXISTS (
            SELECT 1 FROM integrations o WHERE o.slug = i.slug AND o.id <> i.id
        )
        """
    )
    op.alter_column("integrations", "slug", nullable=False)
    op.create_unique_constraint("integrations_slug_key", "integrations", ["slug"])


def downgrade() -> None:
    op.drop_constraint("integrations_slug_key", "integrations", type_="unique")
    op.drop_column("integrations", "slug")
