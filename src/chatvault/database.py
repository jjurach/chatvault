"""
Database setup and utilities for ChatVault.

This module provides database connection management, session handling,
and initialization utilities using SQLAlchemy with SQLite.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatvault.db")
ECHO_SQL = os.getenv("ECHO_SQL", "false").lower() == "true"

# Create engine with SQLite-specific optimizations
def create_db_engine() -> Engine:
    """
    Create and configure the SQLAlchemy database engine.

    Returns:
        Engine: Configured SQLAlchemy engine
    """
    if DATABASE_URL.startswith("sqlite"):
        # SQLite-specific configuration
        engine = create_engine(
            DATABASE_URL,
            connect_args={
                "check_same_thread": False,  # Allow multi-threaded access
            },
            poolclass=StaticPool,  # Better for SQLite
            echo=ECHO_SQL,
        )
    else:
        # For other databases (PostgreSQL, MySQL, etc.)
        engine = create_engine(
            DATABASE_URL,
            echo=ECHO_SQL,
            pool_pre_ping=True,  # Test connections before use
        )

    return engine

# Create engine instance
engine = create_db_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI that provides database sessions.

    Yields:
        Session: SQLAlchemy database session

    Automatically handles session cleanup and rollback on errors.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Provides a database session with automatic cleanup.
    Useful for background tasks and utilities.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.

    Creates all tables defined in the models if they don't exist.
    Should be called once during application startup.
    """
    try:
        logger.info("Initializing database...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")

        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Created tables: {tables}")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def reset_db() -> None:
    """
    Reset the database by dropping and recreating all tables.

    WARNING: This will delete all data! Use with caution.
    Useful for testing or development.
    """
    try:
        logger.warning("Resetting database - all data will be lost!")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Database reset successfully")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if the database connection is working.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_db_stats() -> dict:
    """
    Get database statistics and information.

    Returns:
        dict: Dictionary containing database statistics
    """
    stats = {
        "database_url": DATABASE_URL.replace("://", "://[REDACTED]@") if "://" in DATABASE_URL else DATABASE_URL,
        "connection_ok": check_db_connection(),
        "tables": [],
        "table_counts": {}
    }

    if not stats["connection_ok"]:
        return stats

    try:
        with engine.connect() as conn:
            # Get table list
            if DATABASE_URL.startswith("sqlite"):
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"))
                stats["tables"] = [row[0] for row in result.fetchall()]

                # Get row counts for each table
                for table in stats["tables"]:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.fetchone()[0]
                        stats["table_counts"][table] = count
                    except Exception as e:
                        logger.warning(f"Could not get count for table {table}: {e}")
                        stats["table_counts"][table] = "error"
            else:
                # For other databases, implement appropriate queries
                logger.warning("Database stats not fully implemented for non-SQLite databases")

    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        stats["error"] = str(e)

    return stats


# Migration utilities (basic implementation)
def create_migration_script(name: str) -> str:
    """
    Create a basic migration script template.

    Args:
        name: Name of the migration

    Returns:
        str: Migration script content
    """
    timestamp = os.popen("date +%Y%m%d_%H%M%S").read().strip()

    script = f'''"""
Migration: {name}
Date: {timestamp}
"""

from sqlalchemy import text
from database import engine

def upgrade():
    """Apply the migration."""
    with engine.connect() as conn:
        # Add your migration SQL here
        # Example: conn.execute(text("ALTER TABLE usage_logs ADD COLUMN new_field TEXT;"))
        pass

def downgrade():
    """Rollback the migration."""
    with engine.connect() as conn:
        # Add your rollback SQL here
        # Example: conn.execute(text("ALTER TABLE usage_logs DROP COLUMN new_field;"))
        pass

if __name__ == "__main__":
    print("Running migration: {name}")
    upgrade()
    print("Migration completed")
'''

    return script


# Initialize database on module import if running as main script
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()

    # Print database stats
    stats = get_db_stats()
    print("\nDatabase Status:")
    print(f"Connection: {'OK' if stats['connection_ok'] else 'FAILED'}")
    print(f"Tables: {stats['tables']}")
    print(f"Row counts: {stats['table_counts']}")