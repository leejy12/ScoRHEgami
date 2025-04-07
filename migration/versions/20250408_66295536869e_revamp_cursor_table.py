"""revamp cursor table

Revision ID: 66295536869e
Revises: f62f6c41650b
Create Date: 2025-04-08 00:05:50.788660

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "66295536869e"
down_revision: Union[str, None] = "f62f6c41650b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, drop primary key constraint on the cursor table
    op.execute("ALTER TABLE cursor DROP CONSTRAINT cursor_pkey;")

    # Create the sequence if it doesn't exist
    op.execute(
        """
        DO $$
        BEGIN
            CREATE SEQUENCE IF NOT EXISTS cursor_id_seq;
        END
        $$;
        """
    )

    # Add new columns
    op.add_column(
        "cursor", sa.Column("id", sa.Integer(), autoincrement=True, nullable=True)
    )
    op.add_column("cursor", sa.Column("task_name", sa.String(), nullable=True))

    # Update task_name for existing records
    op.execute(
        """
        UPDATE
            cursor
        SET
            task_name = 'game_fetcher',
            id = nextval('cursor_id_seq');
        """
    )

    # Set NOT NULL constraints after populating data
    op.alter_column("cursor", "id", nullable=False)
    op.alter_column("cursor", "task_name", nullable=False)

    # Add new primary key
    op.execute("ALTER TABLE cursor ADD PRIMARY KEY (id);")

    # Add last_completed column
    op.add_column(
        "cursor",
        sa.Column(
            "last_completed",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )

    # Copy data from date to last_completed if needed
    op.execute(
        """
        UPDATE
            cursor
        SET
            last_completed = date;
        """
    )

    # Finally drop the old column
    op.drop_column("cursor", "date")


def downgrade() -> None:
    # Add back the date column
    op.add_column(
        "cursor",
        sa.Column(
            "date",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
    )

    # Copy data back
    op.execute(
        """
        UPDATE
            cursor
        SET
            date = last_completed;
        """
    )

    # Set NOT NULL constraint
    op.alter_column("cursor", "date", nullable=False)

    # Drop the new columns and constraints
    op.drop_column("cursor", "last_completed")
    op.drop_column("cursor", "task_name")

    # Drop the new primary key
    op.execute("ALTER TABLE cursor DROP CONSTRAINT cursor_pkey;")

    # Set primary key back to what it was (assuming it was "date")
    op.execute("ALTER TABLE cursor ADD PRIMARY KEY (date);")

    # Drop the id column
    op.drop_column("cursor", "id")
