"""Add agent config and knowledge base

Revision ID: 07dc3c2e6fa3
Revises: 852a7eec665a
Create Date: 2025-02-13 11:52:45.761167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07dc3c2e6fa3'
down_revision: Union[str, None] = '852a7eec665a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('agents', sa.Column('config', sa.JSON(), server_default='{}', nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('agents', 'config')
    # ### end Alembic commands ###
