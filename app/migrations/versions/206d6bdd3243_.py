"""empty message

Revision ID: 206d6bdd3243
Revises: a31119b31b3b
Create Date: 2024-07-02 01:20:17.599211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '206d6bdd3243'
down_revision: Union[str, None] = 'a31119b31b3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('lud_session_log',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('lud_session_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.Enum('RE_BUY', 'CASH_OUT', name='ludactiononsession'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['lud_session_id'], ['lud_sessions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('payments',
    sa.Column('debtor_id', sa.Integer(), nullable=True),
    sa.Column('collector_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cash_received', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['collector_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['debtor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('user_lud_session')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_lud_session',
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('lud_session_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('cash_deposit', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('cash_out', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('cash_received', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['lud_session_id'], ['lud_sessions.id'], name='user_lud_session_lud_session_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='user_lud_session_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='user_lud_session_pkey')
    )
    op.drop_table('payments')
    op.drop_table('lud_session_log')
    # ### end Alembic commands ###
