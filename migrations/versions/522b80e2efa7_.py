"""empty message

Revision ID: 522b80e2efa7
Revises: None
Create Date: 2016-03-17 21:26:23.944508

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '522b80e2efa7'
down_revision = None


def upgrade():
    # pylint: disable=E1101
    # commands auto generated by Alembic - please adjust!
    op.add_column('city', sa.Column('population', sa.Integer(), nullable=True))
    # end Alembic commands


def downgrade():
    # pylint: disable=E1101
    # commands auto generated by Alembic - please adjust!
    op.drop_column('city', 'population')
    # end Alembic commands
