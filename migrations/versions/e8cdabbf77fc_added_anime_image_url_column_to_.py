"""Added anime_image_url column to ClickedAnime model

Revision ID: e8cdabbf77fc
Revises: 
Create Date: 2024-11-23 21:35:59.828414

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8cdabbf77fc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('clicked_anime', schema=None) as batch_op:
        batch_op.add_column(sa.Column('anime_image_url', sa.String(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('clicked_anime', schema=None) as batch_op:
        batch_op.drop_column('anime_image_url')

    # ### end Alembic commands ###
