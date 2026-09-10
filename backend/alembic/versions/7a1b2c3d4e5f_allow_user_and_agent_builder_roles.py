"""allow_user_and_agent_builder_roles

Revision ID: 7a1b2c3d4e5f
Revises: 5372b78f87ee
Create Date: 2026-09-10 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '5372b78f87ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to allow both 'user' and 'agent_builder' roles."""
    op.drop_constraint('profiles_role_check', 'profiles', type_='check')
    op.create_check_constraint(
        'profiles_role_check',
        'profiles',
        "role IN ('admin', 'agent_builder', 'user')",
    )


def downgrade() -> None:
    """Downgrade schema to restrict to 'admin' and 'agent_builder'."""
    op.execute("UPDATE profiles SET role = 'agent_builder' WHERE role = 'user'")
    op.drop_constraint('profiles_role_check', 'profiles', type_='check')
    op.create_check_constraint(
        'profiles_role_check',
        'profiles',
        "role IN ('admin', 'agent_builder')",
    )
