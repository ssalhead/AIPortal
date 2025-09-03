"""Merge image_series and canvas migrations

Revision ID: d9528217a1b2
Revises: 004_add_canvas_share_system, create_image_series_tables
Create Date: 2025-09-02 19:00:45.780929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9528217a1b2'
down_revision: Union[str, None] = ('004_add_canvas_share_system', 'create_image_series_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass