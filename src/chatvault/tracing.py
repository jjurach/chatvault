"""
OpenTelemetry distributed tracing for ChatVault.

This module provides distributed tracing capabilities using OpenTelemetry,
enabling request tracing across services and detailed performance monitoring.
"""

import logging
from typing import Optional, Dict, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace import set_tracer_provider

from .config import settings

logger = logging.getLogger(__name__)

# Global tracer instance
_tracer = None


def init_tracing(service_name: str = "chatvault", service_version: str = "1.0.0"):
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service
        service_version: Version of the service
    """
    global _tracer

    try:
        # Set up tracer provider
        trace.set_tracer_provider(TracerProvider(
            resource=trace.Resource.create({
                "service.name": service_name,
                "service.version": service_version,
            })
        ))

        # Configure OTLP exporter (can be configured for Jaeger, Zipkin, etc.)
        otlp_exporter = OTLPSpanExporter(
            endpoint="http://localhost:4317",  # Default OTLP gRPC endpoint
            insecure=True,
        )

        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)

        # Get tracer instance
        _tracer = trace.get_tracer(__name__)

        # Instrument FastAPI (this will be called from main.py)
        # FastAPIInstrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())

        logger.info("OpenTelemetry tracing initialized successfully")

    except Exception as e:
        logger.warning(f"Failed to initialize tracing: {e}")
        # Create a no-op tracer if initialization fails
        _tracer = trace.get_tracer(__name__, tracer_provider=trace.NoOpTracerProvider())


def get_tracer():
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        # Initialize with defaults if not already done
        init_tracing()
    return _tracer


def create_request_span(
    operation_name: str,
    user_id: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    **attributes
) -> trace.Span:
    """
    Create a new span for a request operation.

    Args:
        operation_name: Name of the operation
        user_id: User identifier
        model: Model name (optional)
        provider: Provider name (optional)
        **attributes: Additional span attributes

    Returns:
        OpenTelemetry span
    """
    tracer = get_tracer()

    # Start span with operation name
    with tracer.start_as_span(operation_name) as span:
        # Set span attributes
        span.set_attribute("user.id", user_id)
        span.set_attribute("service.name", "chatvault")

        if model:
            span.set_attribute("llm.model", model)
        if provider:
            span.set_attribute("llm.provider", provider)

        # Add custom attributes
        for key, value in attributes.items():
            if isinstance(value, (str, int, float, bool)):
                span.set_attribute(f"custom.{key}", value)

        return span


def instrument_chat_completion(
    user_id: str,
    model: str,
    provider: str,
    tokens_used: int,
    cost: float,
    response_time_ms: int,
    success: bool = True,
    error_message: Optional[str] = None
):
    """
    Instrument a chat completion operation with tracing.

    Args:
        user_id: User identifier
        model: Model name
        provider: Provider name
        tokens_used: Number of tokens used
        cost: Cost of the operation
        response_time_ms: Response time in milliseconds
        success: Whether the operation was successful
        error_message: Error message if operation failed
    """
    tracer = get_tracer()

    operation_name = f"chat_completion.{model}"
    with tracer.start_as_span(operation_name) as span:
        # Set span attributes
        span.set_attribute("user.id", user_id)
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.provider", provider)
        span.set_attribute("llm.tokens_used", tokens_used)
        span.set_attribute("llm.cost", cost)
        span.set_attribute("performance.response_time_ms", response_time_ms)
        span.set_attribute("operation.success", success)

        # Set span status
        if success:
            span.set_status(Status(StatusCode.OK))
        else:
            span.set_status(Status(StatusCode.ERROR, error_message or "Chat completion failed"))

        # Add event for completion
        span.add_event(
            "chat_completion_complete",
            {
                "tokens_used": tokens_used,
                "cost": cost,
                "response_time_ms": response_time_ms
            }
        )


def instrument_authentication(
    method: str,
    success: bool,
    user_id: Optional[str] = None,
    error_message: Optional[str] = None
):
    """
    Instrument authentication operations.

    Args:
        method: Authentication method (e.g., "bearer_token", "jwt")
        success: Whether authentication was successful
        user_id: User identifier if successful
        error_message: Error message if authentication failed
    """
    tracer = get_tracer()

    with tracer.start_as_span(f"auth.{method}") as span:
        span.set_attribute("auth.method", method)
        span.set_attribute("auth.success", success)

        if user_id:
            span.set_attribute("user.id", user_id)

        if success:
            span.set_status(Status(StatusCode.OK))
        else:
            span.set_status(Status(StatusCode.ERROR, error_message or "Authentication failed"))


def instrument_rate_limiting(
    user_id: str,
    allowed: bool,
    current_requests: int,
    limit: int
):
    """
    Instrument rate limiting operations.

    Args:
        user_id: User identifier
        allowed: Whether the request was allowed
        current_requests: Current number of requests in window
        limit: Rate limit
    """
    tracer = get_tracer()

    with tracer.start_as_span("rate_limit_check") as span:
        span.set_attribute("user.id", user_id)
        span.set_attribute("rate_limit.allowed", allowed)
        span.set_attribute("rate_limit.current_requests", current_requests)
        span.set_attribute("rate_limit.limit", limit)
        span.set_attribute("rate_limit.utilization_percent", (current_requests / limit) * 100)

        if allowed:
            span.set_status(Status(StatusCode.OK))
        else:
            span.set_status(Status(StatusCode.ERROR, "Rate limit exceeded"))


def instrument_database_operation(
    operation: str,
    table: str,
    duration_ms: float,
    success: bool = True,
    error_message: Optional[str] = None,
    **attributes
):
    """
    Instrument database operations.

    Args:
        operation: Database operation (SELECT, INSERT, UPDATE, etc.)
        table: Table name
        duration_ms: Operation duration in milliseconds
        success: Whether the operation was successful
        error_message: Error message if operation failed
        **attributes: Additional attributes
    """
    tracer = get_tracer()

    with tracer.start_as_span(f"db.{operation}") as span:
        span.set_attribute("db.operation", operation)
        span.set_attribute("db.table", table)
        span.set_attribute("performance.duration_ms", duration_ms)

        # Add custom attributes
        for key, value in attributes.items():
            if isinstance(value, (str, int, float, bool)):
                span.set_attribute(f"db.{key}", value)

        if success:
            span.set_status(Status(StatusCode.OK))
        else:
            span.set_status(Status(StatusCode.ERROR, error_message or "Database operation failed"))


def instrument_external_api_call(
    provider: str,
    endpoint: str,
    method: str,
    duration_ms: float,
    status_code: int,
    success: bool = True,
    error_message: Optional[str] = None
):
    """
    Instrument external API calls.

    Args:
        provider: External service provider
        endpoint: API endpoint
        method: HTTP method
        duration_ms: Call duration in milliseconds
        status_code: HTTP status code
        success: Whether the call was successful
        error_message: Error message if call failed
    """
    tracer = get_tracer()

    with tracer.start_as_span(f"external_api.{provider}") as span:
        span.set_attribute("external.provider", provider)
        span.set_attribute("external.endpoint", endpoint)
        span.set_attribute("external.method", method)
        span.set_attribute("external.status_code", status_code)
        span.set_attribute("performance.duration_ms", duration_ms)

        if success:
            span.set_status(Status(StatusCode.OK))
        else:
            span.set_status(Status(StatusCode.ERROR, error_message or "External API call failed"))


# Middleware for automatic request tracing
class TracingMiddleware:
    """
    Middleware for automatic request tracing.

    Adds tracing to all incoming requests.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tracer = get_tracer()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/unknown")

        # Extract user ID from headers if available
        headers = dict((k.decode(), v.decode()) for k, v in scope.get("headers", []))
        user_id = headers.get("x-user-id", "anonymous")

        # Start request span
        with tracer.start_as_span(f"request.{method}") as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.url", path)
            span.set_attribute("user.id", user_id)

            # Track response
            response_status = [200]

            async def traced_send(message):
                if message["type"] == "http.response.start":
                    response_status[0] = message.get("status", 200)
                    span.set_attribute("http.status_code", response_status[0])

                    if response_status[0] >= 400:
                        span.set_status(Status(StatusCode.ERROR, f"HTTP {response_status[0]}"))
                    else:
                        span.set_status(Status(StatusCode.OK))

                await send(message)

            try:
                await self.app(scope, receive, traced_send)
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.add_event("request_error", {"error": str(e)})
                raise


# Health check for tracing system
def check_tracing_health() -> Dict[str, Any]:
    """
    Check the health of the tracing system.

    Returns:
        Dict with tracing health check results
    """
    health = {
        "tracing_enabled": True,
        "opentelemetry_available": True,
        "tracer_provider_configured": False,
        "span_processor_active": False
    }

    try:
        provider = trace.get_tracer_provider()
        if not isinstance(provider, trace.NoOpTracerProvider):
            health["tracer_provider_configured"] = True

            # Check if span processors are configured
            if hasattr(provider, '_span_processors') and provider._span_processors:
                health["span_processor_active"] = True

    except Exception as e:
        health["error"] = str(e)

    return health


# Utility functions
def get_current_span() -> Optional[trace.Span]:
    """Get the current active span."""
    return trace.get_current_span()


def add_span_attributes(**attributes):
    """Add attributes to the current span."""
    span = get_current_span()
    if span:
        for key, value in attributes.items():
            if isinstance(value, (str, int, float, bool)):
                span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Add an event to the current span."""
    span = get_current_span()
    if span:
        span.add_event(name, attributes or {})


if __name__ == "__main__":
    # Test tracing functionality
    logging.basicConfig(level=logging.INFO)

    print("Testing ChatVault Tracing...")

    # Initialize tracing
    init_tracing()

    # Test basic span creation
    tracer = get_tracer()
    with tracer.start_as_span("test_operation") as span:
        span.set_attribute("test.attribute", "test_value")
        span.add_event("test_event", {"event_data": "test"})
        print("Created test span with attributes and events")

    print("Tracing test completed!")