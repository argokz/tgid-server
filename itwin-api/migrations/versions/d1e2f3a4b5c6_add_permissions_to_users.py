"""Add permissions to users (отличия прав пользователя от шаблона роли)

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-10-19 15:00:00

JSON {"matrix": {вид: {действие: none|own|all}}, "general": {право: bool}} — только отличия
от шаблона роли (permissions.py); NULL — права роли как есть.
Модель User читает users.permissions: колонку добавить до перезапуска API.
SQL для ручного применения (psql):

    ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions text;
    UPDATE alembic_version SET version_num = 'd1e2f3a4b5c6';
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('permissions', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'permissions')
