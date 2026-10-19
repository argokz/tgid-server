"""Add activity_log (журнал действий пользователей)

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-10-19 18:00:00

Входы и выходы, правки, расчёты, выгрузки всех пользователей (activity.py); общий для городов.
Без таблицы API работает — запись журнала пропускается с предупреждением в логе.
SQL для ручного применения (psql):

    CREATE TABLE IF NOT EXISTS activity_log (
        id serial PRIMARY KEY, at timestamp NOT NULL, username varchar(100), city varchar(20),
        action varchar(20) NOT NULL, method varchar(8), path varchar(300), status integer,
        duration_ms integer, ip varchar(64), user_agent varchar(300), details text);
    CREATE INDEX IF NOT EXISTS ix_activity_log_at ON activity_log (at);
    CREATE INDEX IF NOT EXISTS ix_activity_log_username ON activity_log (username);
    CREATE INDEX IF NOT EXISTS ix_activity_log_action ON activity_log (action);
    UPDATE alembic_version SET version_num = 'e2f3a4b5c6d7';
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'activity_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('at', sa.DateTime(), nullable=False),
        sa.Column('username', sa.String(100)),
        sa.Column('city', sa.String(20)),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('method', sa.String(8)),
        sa.Column('path', sa.String(300)),
        sa.Column('status', sa.Integer()),
        sa.Column('duration_ms', sa.Integer()),
        sa.Column('ip', sa.String(64)),
        sa.Column('user_agent', sa.String(300)),
        sa.Column('details', sa.Text()),
    )
    op.create_index('ix_activity_log_at', 'activity_log', ['at'])
    op.create_index('ix_activity_log_username', 'activity_log', ['username'])
    op.create_index('ix_activity_log_action', 'activity_log', ['action'])


def downgrade() -> None:
    op.drop_table('activity_log')
