"""Add cities to users (доступ пользователя к городам)

Revision ID: c4d5e6f7a8b9
Revises: b7c1e2d3f4a5
Create Date: 2026-10-15 10:00:00

Список кодов городов через запятую (cities.py, TGID_CITIES); NULL — все города.
Модель User читает users.cities: без колонки вход через UsersDB падает с 503.
SQL для ручного применения (psql):

    ALTER TABLE users ADD COLUMN IF NOT EXISTS cities text;
    UPDATE alembic_version SET version_num = 'c4d5e6f7a8b9';
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b7c1e2d3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('cities', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'cities')
