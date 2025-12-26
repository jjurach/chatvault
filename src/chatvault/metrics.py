"""
Prometheus metrics collection for ChatVault.

This module provides comprehensive metrics collection using Prometheus client,
including request metrics, business metrics, and performance monitoring.
"""

import time
import logging
from typing import Optional, Dict, Any
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
)

from .config import settings

logger = logging.getLogger(__name__)

# Create custom registry for ChatVault metrics
registry = CollectorRegistry()

# Request Metrics
http_requests_total = Counter(
    'chatvault_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'chatvault_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=registry
)

# Active connections
active_connections = Gauge(
    'chatvault_active_connections',
    'Number of active connections',
    registry=registry
)

# Business Metrics
tokens_processed_total = Counter(
    'chatvault_tokens_processed_total',
    'Total number of tokens processed',
    ['model', 'user_type', 'provider'],
    registry=registry
)

requests_cost_total = Counter(
    'chatvault_requests_cost_total',
    'Total cost of requests in USD',
    ['model', 'user_type', 'provider'],
    registry=registry
)

# Model Usage Metrics
model_requests_total = Counter(
    'chatvault_model_requests_total',
    'Total number of requests per model',
    ['model', 'provider', 'status'],
    registry=registry
)

# Rate Limiting Metrics
rate_limit_exceeded_total = Counter(
    'chatvault_rate_limit_exceeded_total',
    'Total number of rate limit violations',
    ['user_id'],
    registry=registry
)

# Authentication Metrics
auth_attempts_total = Counter(
    'chatvault_auth_attempts_total',
    'Total authentication attempts',
    ['method', 'result'],
    registry=registry
)

# Database Metrics
db_connections_active = Gauge(
    'chatvault_db_connections_active',
    'Number of active database connections',
    registry=registry
)

db_query_duration_seconds = Histogram(
    'chatvault_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=registry
)

# Error Metrics
errors_total = Counter(
    'chatvault_errors_total',
    'Total number of errors',
    ['type', 'endpoint', 'status_code'],
    registry=registry
)

# Performance Metrics
response_time_percentiles = Summary(
    'chatvault_response_time_percentiles',
    'Response time percentiles',
    ['endpoint'],
    registry=registry
)

# System Metrics
memory_usage_bytes = Gauge(
    'chatvault_memory_usage_bytes',
    'Current memory usage in bytes',
    registry=registry
)

cpu_usage_percent = Gauge(
    'chatvault_cpu_usage_percent',
    'Current CPU usage percentage',
    registry=registry
)

# Custom Business Metrics
users_active = Gauge(
    'chatvault_users_active',
    'Number of active users in the last hour',
    registry=registry
)

models_available = Gauge(
    'chatvault_models_available',
    'Number of available models',
    registry=registry
)

providers_configured = Gauge(
    'chatvault_providers_configured',
    'Number of configured providers',
    registry=registry
)


class MetricsCollector:
    """
    Metrics collection and management for ChatVault.

    Provides methods to record various metrics throughout the application.
    """

    def __init__(self):
        self.start_time = time.time()
        self._update_system_metrics()

    def _update_system_metrics(self):
        """Update system-level metrics."""
        try:
            import psutil

            # Memory usage
            process = psutil.Process()
            memory_usage_bytes.set(process.memory_info().rss)

            # CPU usage (over 1 second interval)
            cpu_usage_percent.set(process.cpu_percent(interval=1.0))

        except ImportError:
            # psutil not available, skip system metrics
            logger.debug("psutil not available, skipping system metrics")
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        # Record errors
        if status_code >= 400:
            errors_total.labels(
                type='http',
                endpoint=endpoint,
                status_code=status_code
            ).inc()

    def record_token_usage(self, model: str, user_type: str, provider: str, tokens: int):
        """Record token usage metrics."""
        tokens_processed_total.labels(
            model=model,
            user_type=user_type,
            provider=provider
        ).inc(tokens)

    def record_request_cost(self, model: str, user_type: str, provider: str, cost: float):
        """Record request cost metrics."""
        requests_cost_total.labels(
            model=model,
            user_type=user_type,
            provider=provider
        ).inc(cost)

    def record_model_request(self, model: str, provider: str, status: str = 'success'):
        """Record model-specific request metrics."""
        model_requests_total.labels(
            model=model,
            provider=provider,
            status=status
        ).inc()

    def record_rate_limit_violation(self, user_id: str):
        """Record rate limiting violations."""
        rate_limit_exceeded_total.labels(user_id=user_id).inc()

    def record_auth_attempt(self, method: str, success: bool):
        """Record authentication attempts."""
        result = 'success' if success else 'failure'
        auth_attempts_total.labels(method=method, result=result).inc()

    def record_db_query(self, operation: str, table: str, duration: float):
        """Record database query metrics."""
        db_query_duration_seconds.labels(
            operation=operation,
            table=table
        ).observe(duration)

    def update_business_metrics(self):
        """Update business-level metrics."""
        try:
            # Update available models count
            available_models = settings.get_available_models()
            models_available.set(len(available_models))

            # Update configured providers count
            api_keys = settings.validate_api_keys()
            providers_configured.set(sum(api_keys.values()))

            # Update active users (simplified - users active in last hour)
            # This would need actual session tracking in production
            users_active.set(0)  # Placeholder

        except Exception as e:
            logger.warning(f"Failed to update business metrics: {e}")

    def record_response_time(self, endpoint: str, duration: float):
        """Record response time percentiles."""
        response_time_percentiles.labels(endpoint=endpoint).observe(duration)

    def get_metrics(self) -> bytes:
        """Get all metrics in Prometheus format."""
        return generate_latest(registry)

    def get_metrics_content_type(self) -> str:
        """Get the content type for metrics endpoint."""
        return CONTENT_TYPE_LATEST


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Middleware for automatic metrics collection
class MetricsMiddleware:
    """
    FastAPI middleware for automatic metrics collection.

    Records HTTP request metrics for all endpoints.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        # Extract request info
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/unknown")

        # Create response wrapper to capture status code
        response_status = [200]  # Default

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                response_status[0] = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)

            # Record metrics
            duration = time.time() - start_time
            metrics_collector.record_http_request(method, path, response_status[0], duration)
            metrics_collector.record_response_time(path, duration)

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            metrics_collector.record_http_request(method, path, 500, duration)
            raise


# Utility functions for business metrics
def record_chat_completion_metrics(
    user_id: str,
    model: str,
    provider: str,
    tokens_used: int,
    cost: float,
    response_time: float,
    success: bool = True
):
    """Record metrics for chat completion requests."""
    user_type = "authenticated" if user_id else "anonymous"

    metrics_collector.record_token_usage(model, user_type, provider, tokens_used)
    metrics_collector.record_request_cost(model, user_type, provider, cost)
    metrics_collector.record_model_request(
        model, provider, "success" if success else "error"
    )

    if not success:
        errors_total.labels(
            type='chat_completion',
            endpoint='/v1/chat/completions',
            status_code='error'
        ).inc()


def record_auth_metrics(method: str, success: bool):
    """Record authentication metrics."""
    metrics_collector.record_auth_attempt(method, success)


def record_rate_limit_metrics(user_id: str):
    """Record rate limiting metrics."""
    metrics_collector.record_rate_limit_violation(user_id)


# Health check for metrics system
def check_metrics_health() -> Dict[str, Any]:
    """
    Check the health of the metrics system.

    Returns:
        Dict with metrics health check results
    """
    health = {
        "metrics_enabled": True,
        "prometheus_client_available": True,
        "registry_active": True,
        "system_metrics_available": False
    }

    try:
        import psutil
        health["system_metrics_available"] = True
    except ImportError:
        pass

    # Test metrics collection
    try:
        metrics_data = metrics_collector.get_metrics()
        health["metrics_collection_working"] = len(metrics_data) > 0
    except Exception as e:
        health["metrics_collection_working"] = False
        health["error"] = str(e)

    return health


if __name__ == "__main__":
    # Test metrics functionality
    logging.basicConfig(level=logging.INFO)

    print("Testing ChatVault Metrics...")

    # Record some test metrics
    metrics_collector.record_http_request("GET", "/health", 200, 0.1)
    metrics_collector.record_token_usage("gpt-4", "authenticated", "openai", 100)
    metrics_collector.record_request_cost("gpt-4", "authenticated", "openai", 0.002)

    # Get metrics output
    metrics_output = metrics_collector.get_metrics()
    print("Sample metrics output:")
    print(metrics_output.decode()[:500] + "...")

    print("Metrics test completed!")