"""merge two-role model with enum normalisation

Revision ID: e52e63e33395
Revises: f3625681d4d6, f4dda260077e
Create Date: 2026-09-11 13:49:50.540527

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'e52e63e33395'
down_revision: str | Sequence[str] | None = ('f3625681d4d6', 'f4dda260077e')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
