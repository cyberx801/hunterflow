"""report format pdf

Revision ID: c7f1a2b3d4e5
Revises: ed2dade4d608
Create Date: 2026-10-29 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c7f1a2b3d4e5'
down_revision: Union[str, None] = 'ed2dade4d608'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE reports ALTER COLUMN format TYPE varchar(16) USING format::text")
        op.execute("DROP TYPE IF EXISTS report_format")
    # SQLite stores enums as VARCHAR; no change needed.


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE reports ALTER COLUMN format TYPE varchar(16)")
