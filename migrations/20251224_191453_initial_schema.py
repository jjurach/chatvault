"""
Migration: Initial database schema setup
Date: 20251224_191453

Creates the initial database schema for ChatVault including:
- usage_logs table for tracking chat completion usage
- api_keys table for storing API key metadata
- Indexes for optimal query performance
"""

import logging
from sqlalchemy import text, Index
from database import engine
from models import Base

logger = logging.getLogger(__name__)


def upgrade():
    """
    Apply the initial database schema migration.

    Creates all tables defined in models.py and adds necessary indexes.
    """
    logger.info("Applying initial schema migration...")

    try:
        # Create all tables defined in models.py
        Base.metadata.create_all(bind=engine)
        logger.info("Created base tables")

        # Additional indexes for performance (beyond what's in models.py)
        with engine.connect() as conn:
            # Index for cost analysis queries
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_usage_cost_timestamp
                    ON usage_logs(cost, timestamp)
                """))
                logger.info("Created cost/timestamp index")
            except Exception as e:
                logger.warning(f"Could not create cost index: {e}")

            # Index for request tracking
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_usage_request_provider
                    ON usage_logs(request_id, provider)
                """))
                logger.info("Created request/provider index")
            except Exception as e:
                logger.warning(f"Could not create request index: {e}")

            # Index for response time analysis
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_usage_response_time
                    ON usage_logs(response_time_ms, model_name)
                """))
                logger.info("Created response time index")
            except Exception as e:
                logger.warning(f"Could not create response time index: {e}")

            conn.commit()

        logger.info("Initial schema migration completed successfully")

    except Exception as e:
        logger.error(f"Failed to apply initial schema migration: {e}")
        raise


def downgrade():
    """
    Rollback the initial database schema migration.

    Drops all tables created in the upgrade function.
    WARNING: This will delete all data!
    """
    logger.warning("Rolling back initial schema migration - all data will be lost!")

    try:
        # Drop all tables in reverse order to handle foreign keys
        with engine.connect() as conn:
            # Get all table names (excluding SQLite internal tables)
            result = conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """))

            tables = [row[0] for row in result.fetchall()]

            # Drop tables (reverse order to handle dependencies)
            for table in reversed(tables):
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                    logger.info(f"Dropped table: {table}")
                except Exception as e:
                    logger.warning(f"Could not drop table {table}: {e}")

            conn.commit()

        logger.info("Initial schema migration rolled back successfully")

    except Exception as e:
        logger.error(f"Failed to rollback initial schema migration: {e}")
        raise


def verify_migration():
    """
    Verify that the migration was applied correctly.

    Returns:
        dict: Verification results
    """
    verification = {
        "tables_exist": [],
        "tables_missing": [],
        "indexes_exist": [],
        "indexes_missing": [],
        "errors": []
    }

    try:
        with engine.connect() as conn:
            # Check for required tables
            required_tables = ["usage_logs", "api_keys"]

            result = conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """))

            existing_tables = [row[0] for row in result.fetchall()]

            for table in required_tables:
                if table in existing_tables:
                    verification["tables_exist"].append(table)
                else:
                    verification["tables_missing"].append(table)

            # Check for key indexes
            result = conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """))

            existing_indexes = [row[0] for row in result.fetchall()]
            required_indexes = [
                "idx_usage_model_timestamp",
                "idx_usage_user_timestamp",
                "idx_usage_provider_timestamp",
                "idx_usage_cost_timestamp",
                "idx_usage_request_provider",
                "idx_usage_response_time"
            ]

            for index in required_indexes:
                if index in existing_indexes:
                    verification["indexes_exist"].append(index)
                else:
                    verification["indexes_missing"].append(index)

    except Exception as e:
        verification["errors"].append(str(e))

    return verification


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "upgrade":
            upgrade()
        elif command == "downgrade":
            downgrade()
        elif command == "verify":
            result = verify_migration()
            print("\nMigration Verification:")
            print(f"Tables exist: {result['tables_exist']}")
            print(f"Tables missing: {result['tables_missing']}")
            print(f"Indexes exist: {result['indexes_exist']}")
            print(f"Indexes missing: {result['indexes_missing']}")
            if result['errors']:
                print(f"Errors: {result['errors']}")
        else:
            print("Usage: python migration.py [upgrade|downgrade|verify]")
    else:
        print("Running upgrade by default...")
        upgrade()