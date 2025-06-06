"""add tweet posted_at

Revision ID: 8dff340c1513
Revises: c1e693828e54
Create Date: 2025-04-10 21:14:10.411775

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8dff340c1513"
down_revision: Union[str, None] = "c1e693828e54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "tweet", sa.Column("posted_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )

    op.execute(
        """
        UPDATE
            tweet
        SET
            posted_at = updated_at
        WHERE
            status = 'success' 
        """
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("tweet", "posted_at")
    # ### end Alembic commands ###
