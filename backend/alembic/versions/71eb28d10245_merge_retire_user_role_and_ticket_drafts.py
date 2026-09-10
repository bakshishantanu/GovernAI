"""merge retire_user_role and ticket_drafts

Revision ID: 71eb28d10245
Revises: 13bdf75f3ff2, 9c4e1f7a2b30
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71eb28d10245'
down_revision: Union[str, Sequence[str], None] = ('13bdf75f3ff2', '9c4e1f7a2b30')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
