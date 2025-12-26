"""
Database models for ChatVault usage tracking.

This module defines the SQLAlchemy models for storing chat completion usage data,
including token counts, costs, and request metadata.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UsageLog(Base):
    """
    Model for tracking chat completion usage statistics.

    Stores detailed information about each API request including token usage,
    cost calculations, and request metadata for auditing and analytics.
    """

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Timestamp when the request was processed
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # User identification (from authentication token or request metadata)
    user_id = Column(String(255), nullable=True, index=True)

    # Model name used for the request (e.g., 'vault-architect', 'vault-local')
    model_name = Column(String(255), nullable=False, index=True)

    # Token usage statistics
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    # Calculated cost for the request
    cost = Column(Float, nullable=False, default=0.0)

    # Unique request identifier for tracking
    request_id = Column(String(255), nullable=True, unique=True, index=True)

    # Additional metadata (stored as JSON string)
    request_metadata = Column(Text, nullable=True)

    # Provider information (e.g., 'anthropic', 'ollama', 'deepseek')
    provider = Column(String(100), nullable=True, index=True)

    # Response time in milliseconds
    response_time_ms = Column(Integer, nullable=True)

    # HTTP status code
    status_code = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<UsageLog(id={self.id}, model='{self.model_name}', tokens={self.total_tokens}, cost={self.cost})>"

    def to_dict(self):
        """Convert model instance to dictionary for API responses."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "request_id": self.request_id,
            "provider": self.provider,
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
        }


class ApiKey(Base):
    """
    Model for storing API key metadata.

    Tracks API keys used by the system for different providers.
    Note: Actual key values are stored in environment variables, not here.
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1, nullable=False)  # Boolean as integer for SQLite

    def __repr__(self):
        return f"<ApiKey(provider='{self.provider}', name='{self.name}', active={bool(self.is_active)})>"


# Index definitions for better query performance
from sqlalchemy import Index

# Composite index for common queries
Index('idx_usage_model_timestamp', UsageLog.model_name, UsageLog.timestamp)
Index('idx_usage_user_timestamp', UsageLog.user_id, UsageLog.timestamp)
Index('idx_usage_provider_timestamp', UsageLog.provider, UsageLog.timestamp)