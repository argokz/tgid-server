"""Add role to users (RBAC: viewer | calculator | editor | admin)

Revision ID: b7c1e2d3f4a5
Revises: fd215dfad484
Create Date: 2026-09-27 12:00:00

Модель User и вход (/auth/login) уже читают users.role; без этой колонки
вход через UsersDB падает с 503. Существующие is_admin=true становятся admin,
остальные — viewer. SQL для ручного применения (psql):

    ALTER TABLE users ADD COLUMN IF NOT EXISTS role varchar(20) NOT NULL DEFAULT 'viewer';
    UPDATE users SET role = 'admin' WHERE is_admin IS TRUE;
    ALTER TABLE users ADD CONSTRAINT ck_users_role
        CHECK (role IN ('viewer', 'calculator', 'editor', 'admin'));
    UPDATE alembic_version SET version_num = 'b7c1e2d3f4a5';
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1e2d3f4a5'
down_revision: Union[str, None] = 'fd215dfad484'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('role', sa.String(length=20), nullable=False, server_default='viewer'),
    )
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin IS TRUE")
    op.create_check_constraint(
        'ck_users_role', 'users', "role IN ('viewer', 'calculator', 'editor', 'admin')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_users_role', 'users', type_='check')
    op.drop_column('users', 'role')
