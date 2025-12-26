"""
Migration: Add error_details field to usage_logs table
Date: 2025-12-26 02:35:07
Description: Add error_details column to store error information for failed requests
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from src.chatvault.database import engine


def upgrade():
    """Apply the migration."""
    # Add error_details column to usage_logs table
    with engine.connect() as conn:
        # SQLite syntax for adding column
        conn.execute(text("ALTER TABLE usage_logs ADD COLUMN error_details TEXT"))
        conn.commit()


def downgrade():
    """Rollback the migration."""
    # Note: SQLite doesn't support dropping columns directly
    # In production, you would need to recreate the table without the column
    # For now, we'll leave this as a no-op with a warning
    print("WARNING: SQLite does not support dropping columns.")
    print("To rollback this migration, you would need to:")
    print("1. Create a new table without error_details column")
    print("2. Copy data from old table to new table")
    print("3. Drop old table and rename new table")
    print("This is left as an exercise for production deployments.")


if __name__ == "__main__":
    print("Running migration: Add error_details field to usage_logs")
    upgrade()
    print("Migration completed successfully")