"""merge_user_role_into_agent_builder

Revision ID: 5372b78f87ee
Revises: acbf56ba6efa
Create Date: 2026-09-09 19:12:28.081976

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5372b78f87ee'
down_revision: Union[str, Sequence[str], None] = 'acbf56ba6efa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Data migration: convert all profiles with role = 'user' to 'agent_builder'
    op.execute("UPDATE profiles SET role = 'agent_builder' WHERE role = 'user'")

    # 2. Update CHECK constraint to only allow 'admin' and 'agent_builder'
    op.drop_constraint('profiles_role_check', 'profiles', type_='check')
    op.create_check_constraint(
        'profiles_role_check',
        'profiles',
        "role IN ('admin', 'agent_builder')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Restore check constraint allowing ('admin', 'agent_builder', 'user')
    # Note: We cannot deterministically know which profiles were originally 'user'
    # vs 'agent_builder', so profiles remain 'agent_builder'.
    op.drop_constraint('profiles_role_check', 'profiles', type_='check')
    op.create_check_constraint(
        'profiles_role_check',
        'profiles',
        "role IN ('admin', 'agent_builder', 'user')",
    )
