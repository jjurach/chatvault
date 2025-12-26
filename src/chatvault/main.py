"""
ChatVault - FastAPI-based OpenAI-Compatible Chat Proxy

Main application file that sets up the FastAPI server, routes, middleware,
and integrates all components for the ChatVault system.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings
from .auth import get_current_user, require_auth
from .database import init_db, get_db_stats

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting ChatVault...")
    logger.info(f"Environment: {'development' if settings.debug else 'production'}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Log configuration status
    db_stats = get_db_stats()
    logger.info(f"Database connection: {'OK' if db_stats['connection_ok'] else 'FAILED'}")

    available_models = settings.get_available_models()
    logger.info(f"Available models: {available_models}")

    yield

    # Shutdown
    logger.info("Shutting down ChatVault...")


# Create FastAPI application
app = FastAPI(
    title="ChatVault",
    description="OpenAI-compatible chat proxy with usage tracking and secure key management",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
from .rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# Add metrics middleware
from .metrics import MetricsMiddleware
app.add_middleware(MetricsMiddleware)

# Add tracing middleware
from .tracing import TracingMiddleware, init_tracing
app.add_middleware(TracingMiddleware)

# Initialize tracing
init_tracing()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log HTTP requests and responses.

    Tracks request timing and logs important information.
    """
    start_time = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")

    try:
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        logger.info(".2f")

        return response

    except Exception as e:
        # Log error
        process_time = time.time() - start_time
        logger.error(".2f")
        raise


# Health check endpoint
@app.get("/health")
async def health_check(user_id: str = Depends(get_current_user)):
    """
    Health check endpoint for monitoring and load balancers.

    Returns comprehensive health status of all system components.
    """
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "components": {}
    }

    # Check database
    try:
        db_stats = get_db_stats()
        health["components"]["database"] = {
            "status": "healthy" if db_stats["connection_ok"] else "unhealthy",
            "tables": len(db_stats.get("tables", [])),
            "connection_ok": db_stats["connection_ok"]
        }
    except Exception as e:
        health["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "unhealthy"

    # Check configuration
    try:
        available_models = settings.get_available_models()
        api_key_status = settings.validate_api_keys()

        health["components"]["configuration"] = {
            "status": "healthy",
            "models_configured": len(available_models),
            "providers_available": sum(api_key_status.values())
        }
    except Exception as e:
        health["components"]["configuration"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "unhealthy"

    # Check authentication
    try:
        from .auth import check_auth_health
        auth_health = check_auth_health()

        health["components"]["authentication"] = {
            "status": "healthy",
            "auth_enabled": auth_health["auth_enabled"],
            "api_key_configured": auth_health["api_key_configured"],
            "jwt_enabled": auth_health.get("jwt_enabled", False)
        }
    except Exception as e:
        health["components"]["authentication"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "unhealthy"

    # Check metrics system
    try:
        from .metrics import check_metrics_health
        metrics_health = check_metrics_health()

        health["components"]["metrics"] = {
            "status": "healthy" if metrics_health.get("metrics_collection_working", False) else "degraded",
            "prometheus_available": metrics_health.get("prometheus_client_available", False),
            "system_metrics_available": metrics_health.get("system_metrics_available", False),
            "collection_working": metrics_health.get("metrics_collection_working", False)
        }
    except Exception as e:
        health["components"]["metrics"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check tracing system
    try:
        from .tracing import check_tracing_health
        tracing_health = check_tracing_health()

        health["components"]["tracing"] = {
            "status": "healthy" if tracing_health.get("span_processor_active", False) else "degraded",
            "opentelemetry_available": tracing_health.get("opentelemetry_available", False),
            "tracer_provider_configured": tracing_health.get("tracer_provider_configured", False),
            "span_processor_active": tracing_health.get("span_processor_active", False)
        }
    except Exception as e:
        health["components"]["tracing"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check external API connectivity
    try:
        # Test basic connectivity to configured providers
        api_keys = settings.validate_api_keys()
        external_checks = {}

        # Check Ollama connectivity (if configured)
        if settings.ollama_base_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{settings.ollama_base_url}/api/tags")
                    external_checks["ollama"] = {
                        "status": "healthy" if response.status_code == 200 else "degraded",
                        "response_code": response.status_code
                    }
            except Exception as e:
                external_checks["ollama"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

        # Note: Other providers (Anthropic, OpenAI, etc.) would require actual API calls
        # which might consume credits, so we just check if keys are configured

        health["components"]["external_apis"] = {
            "status": "healthy",
            "providers_configured": sum(api_keys.values()),
            "connectivity_checks": external_checks
        }

        # If any external API is unhealthy, mark overall health as degraded
        if any(check.get("status") == "unhealthy" for check in external_checks.values()):
            if health["status"] == "healthy":
                health["status"] = "degraded"

    except Exception as e:
        health["components"]["external_apis"] = {
            "status": "unknown",
            "error": str(e)
        }

    # Check model availability
    try:
        available_models = settings.get_available_models()
        total_models = len(available_models)

        # Basic validation - check if models are configured
        health["components"]["models"] = {
            "status": "healthy" if total_models > 0 else "unhealthy",
            "models_configured": total_models,
            "models_list": available_models[:5] if total_models > 0 else []  # Show first 5
        }

        if total_models == 0:
            health["status"] = "unhealthy"

    except Exception as e:
        health["components"]["models"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "unhealthy"

    # Performance metrics
    try:
        import psutil
        process = psutil.Process()

        health["performance"] = {
            "memory_usage_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
            "uptime_seconds": int(time.time() - health.get("timestamp", time.time()))
        }
    except ImportError:
        health["performance"] = {
            "note": "psutil not available for performance metrics"
        }
    except Exception as e:
        health["performance"] = {
            "error": str(e)
        }

    # Determine overall health status based on component statuses
    component_statuses = [comp.get("status", "unknown") for comp in health.get("components", {}).values()]

    if "unhealthy" in component_statuses:
        health["status"] = "unhealthy"
    elif "degraded" in component_statuses or "unknown" in component_statuses:
        if health["status"] == "healthy":
            health["status"] = "degraded"

    return health


# Models endpoint
@app.get("/v1/models")
async def list_models(user_id: str = Depends(get_current_user)):
    """
    OpenAI-compatible models endpoint.

    Returns list of available models configured in ChatVault that the user can access.
    """
    try:
        available_models = settings.get_available_models()

        # Filter models based on user permissions
        from .auth import authenticator
        accessible_models = []
        for model_name in available_models:
            if authenticator.validate_model_access(user_id, model_name):
                accessible_models.append(model_name)

        # Format as OpenAI-compatible response
        models = []
        for model_name in accessible_models:
            provider = settings.get_provider_for_model(model_name)

            models.append({
                "id": model_name,
                "object": "model",
                "created": int(time.time()),  # Placeholder
                "owned_by": provider or "chatvault",
                "permission": [],  # OpenAI compatibility
                "root": model_name,
                "parent": None
            })

        return {
            "object": "list",
            "data": models
        }

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve models"
        )


# Chat completions endpoint
@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    OpenAI-compatible chat completions endpoint.

    Routes requests to appropriate LLM providers via LiteLLM with usage tracking.
    Supports both streaming and non-streaming responses.
    """
    try:
        # Parse request data
        request_data = await request.json()

        # Validate and normalize request
        from .streaming_handler import validate_openai_request
        normalized_request = validate_openai_request(request_data)

        model = normalized_request["model"]
        messages = normalized_request["messages"]
        stream = normalized_request.get("stream", False)

        # Validate model access for authenticated user
        from .auth import authenticator
        if not authenticator.validate_model_access(user_id, model):
            logger.warning(f"Access denied for user {user_id} to model {model}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to model '{model}'"
            )

        # Remove OpenAI-specific fields that LiteLLM doesn't need
        litellm_params = {k: v for k, v in normalized_request.items()
                         if k not in ["model", "messages", "stream"]}

        # Generate unique request ID
        import uuid
        request_id = str(uuid.uuid4())

        logger.info(f"Chat completion request: model={model}, stream={stream}, user={user_id}, request_id={request_id}")

        # Import here to avoid circular imports
        from .litellm_router import chat_completion, chat_completion_stream
        from .streaming_handler import handle_streaming_response, create_error_response

        if stream:
            # Handle streaming response
            from fastapi.responses import StreamingResponse

            async def generate_stream():
                try:
                    stream_generator = await chat_completion_stream(
                        model=model,
                        messages=messages,
                        user_id=user_id,
                        request_id=request_id,
                        **litellm_params
                    )

                    async for event in handle_streaming_response(stream_generator, request_id):
                        yield event

                    # Send final done event
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    error_event = f"data: {create_error_response(str(e))}\n\n"
                    yield error_event
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Content-Type": "text/event-stream; charset=utf-8"}
            )

        else:
            # Handle regular (non-streaming) response
            response = await chat_completion(
                model=model,
                messages=messages,
                user_id=user_id,
                request_id=request_id,
                **litellm_params
            )

            # Convert LiteLLM response to OpenAI format
            openai_response = {
                "id": getattr(response, 'id', f"chatcmpl-{request_id}"),
                "object": "chat.completion",
                "created": getattr(response, 'created', int(time.time())),
                "model": model,
                "choices": [],
                "usage": {}
            }

            # Extract choices
            if hasattr(response, 'choices') and response.choices:
                for choice in response.choices:
                    openai_choice = {
                        "index": getattr(choice, 'index', 0),
                        "message": {
                            "role": "assistant",
                            "content": ""
                        },
                        "finish_reason": getattr(choice, 'finish_reason', None)
                    }

                    # Extract message content
                    if hasattr(choice, 'message'):
                        message = choice.message
                        openai_choice["message"]["role"] = getattr(message, 'role', 'assistant')
                        openai_choice["message"]["content"] = getattr(message, 'content', '')

                    openai_response["choices"].append(openai_choice)

            # Extract usage information
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                openai_response["usage"] = {
                    "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(usage, 'completion_tokens', 0),
                    "total_tokens": getattr(usage, 'total_tokens', 0)
                }

            return openai_response

    except ValueError as e:
        # Validation error
        logger.warning(f"Request validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        # General error
        logger.error(f"Chat completion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during chat completion"
        )


# Usage statistics endpoint (requires authentication)
@app.get("/usage")
async def get_usage_stats(
    user_id: str = Depends(require_auth),
    limit: int = 100,
    offset: int = 0,
    model: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json"
):
    """
    Get usage statistics for the authenticated user.

    Returns usage logs with filtering, pagination, and aggregation.

    Query Parameters:
    - limit: Maximum number of records to return (default: 100, max: 1000)
    - offset: Number of records to skip (default: 0)
    - model: Filter by specific model name
    - start_date: Filter records from this date (ISO format: YYYY-MM-DD)
    - end_date: Filter records until this date (ISO format: YYYY-MM-DD)
    - format: Response format - 'json' or 'csv' (default: json)
    """
    from sqlalchemy import and_, func, desc
    from datetime import datetime
    from fastapi.responses import StreamingResponse
    from .database import get_db_session
    from .models import UsageLog

    # Validate parameters
    if limit > 1000:
        limit = 1000
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0

    try:
        with get_db_session() as db:
            # Build query with filters
            query = db.query(UsageLog).filter(UsageLog.user_id == user_id)

            # Apply model filter
            if model:
                query = query.filter(UsageLog.model_name == model)

            # Apply date filters
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    query = query.filter(UsageLog.timestamp >= start_dt)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid start_date format. Use ISO format: YYYY-MM-DD"
                    )

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    query = query.filter(UsageLog.timestamp <= end_dt)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid end_date format. Use ISO format: YYYY-MM-DD"
                    )

            # Get total count for pagination
            total_count = query.count()

            # Apply ordering and pagination
            usage_logs = query.order_by(desc(UsageLog.timestamp)).offset(offset).limit(limit).all()

            # Calculate aggregations
            agg_query = db.query(
                func.count(UsageLog.id).label('total_requests'),
                func.sum(UsageLog.total_tokens).label('total_tokens'),
                func.sum(UsageLog.input_tokens).label('total_input_tokens'),
                func.sum(UsageLog.output_tokens).label('total_output_tokens'),
                func.sum(UsageLog.cost).label('total_cost'),
                func.avg(UsageLog.response_time_ms).label('avg_response_time')
            ).filter(UsageLog.user_id == user_id)

            # Apply same filters to aggregation query
            if model:
                agg_query = agg_query.filter(UsageLog.model_name == model)
            if start_date:
                agg_query = agg_query.filter(UsageLog.timestamp >= start_dt)
            if end_date:
                agg_query = agg_query.filter(UsageLog.timestamp <= end_dt)

            aggregations = agg_query.first()

            # Handle CSV export
            if format.lower() == "csv":
                import csv
                import io

                def generate_csv():
                    output = io.StringIO()
                    writer = csv.writer(output)

                    # Write header
                    writer.writerow([
                        'timestamp', 'model_name', 'input_tokens', 'output_tokens',
                        'total_tokens', 'cost', 'provider', 'response_time_ms',
                        'status_code', 'request_id'
                    ])

                    # Write data
                    for log in usage_logs:
                        writer.writerow([
                            log.timestamp.isoformat() if log.timestamp else '',
                            log.model_name,
                            log.input_tokens,
                            log.output_tokens,
                            log.total_tokens,
                            log.cost,
                            log.provider or '',
                            log.response_time_ms or '',
                            log.status_code or '',
                            log.request_id or ''
                        ])

                    yield output.getvalue()

                return StreamingResponse(
                    generate_csv(),
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=usage_stats.csv"}
                )

            # Prepare JSON response
            response_data = {
                "user_id": user_id,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total_count": total_count,
                    "has_more": offset + limit < total_count
                },
                "filters": {
                    "model": model,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "aggregations": {
                    "total_requests": aggregations.total_requests or 0,
                    "total_tokens": int(aggregations.total_tokens or 0),
                    "total_input_tokens": int(aggregations.total_input_tokens or 0),
                    "total_output_tokens": int(aggregations.total_output_tokens or 0),
                    "total_cost": round(float(aggregations.total_cost or 0), 6),
                    "avg_response_time_ms": round(float(aggregations.avg_response_time or 0), 2)
                },
                "usage_logs": [log.to_dict() for log in usage_logs]
            }

            return response_data

    except Exception as e:
        logger.error(f"Error retrieving usage stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )


# Cost prediction and estimation endpoint
@app.get("/costs/predict")
async def predict_costs(
    user_id: str = Depends(require_auth),
    days_ahead: int = 30,
    model: Optional[str] = None
):
    """
    Predict future costs based on historical usage patterns.

    Query Parameters:
    - days_ahead: Number of days to predict ahead (default: 30, max: 365)
    - model: Specific model to predict costs for (optional)
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, desc
    from .database import get_db_session
    from .models import UsageLog

    # Validate parameters
    if days_ahead > 365:
        days_ahead = 365
    if days_ahead < 1:
        days_ahead = 1

    try:
        with get_db_session() as db:
            # Get historical data for prediction
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=settings.get_litellm_config().get('cost_calculation', {}).get('cost_prediction', {}).get('prediction_window_days', 30))

            query = db.query(
                func.date(UsageLog.timestamp).label('date'),
                func.sum(UsageLog.cost).label('daily_cost'),
                func.sum(UsageLog.total_tokens).label('daily_tokens'),
                func.count(UsageLog.id).label('daily_requests')
            ).filter(
                UsageLog.user_id == user_id,
                UsageLog.timestamp >= start_date,
                UsageLog.timestamp <= end_date
            )

            if model:
                query = query.filter(UsageLog.model_name == model)

            query = query.group_by(func.date(UsageLog.timestamp)).order_by(desc('date'))

            historical_data = query.all()

            if not historical_data:
                return {
                    "prediction": {
                        "total_predicted_cost": 0.0,
                        "daily_average_cost": 0.0,
                        "confidence_interval": {
                            "low": 0.0,
                            "high": 0.0
                        }
                    },
                    "historical_data_points": 0,
                    "message": "No historical data available for prediction"
                }

            # Simple linear regression for prediction
            import numpy as np

            # Prepare data for regression
            dates = [(end_date - datetime.combine(row.date, datetime.min.time())).days for row in historical_data]
            costs = [float(row.daily_cost) for row in historical_data]

            if len(dates) < 2:
                # Not enough data for prediction
                avg_cost = np.mean(costs)
                predicted_total = avg_cost * days_ahead

                return {
                    "prediction": {
                        "total_predicted_cost": round(predicted_total, 2),
                        "daily_average_cost": round(avg_cost, 2),
                        "confidence_interval": {
                            "low": round(predicted_total * 0.8, 2),
                            "high": round(predicted_total * 1.2, 2)
                        }
                    },
                    "historical_data_points": len(historical_data),
                    "method": "simple_average"
                }

            # Linear regression
            X = np.array(dates).reshape(-1, 1)
            y = np.array(costs)

            # Add intercept
            X = np.column_stack([np.ones(len(X)), X])

            # Calculate coefficients
            try:
                beta = np.linalg.inv(X.T @ X) @ X.T @ y
                intercept, slope = beta[0], beta[1]

                # Predict future costs
                future_days = np.array(range(1, days_ahead + 1))
                predicted_costs = intercept + slope * future_days
                total_predicted = max(0, np.sum(predicted_costs))  # Ensure non-negative

                # Calculate confidence interval (simplified)
                residuals = y - (intercept + slope * np.array(dates))
                std_error = np.std(residuals, ddof=2)
                confidence_multiplier = 1.96  # 95% confidence
                margin_error = confidence_multiplier * std_error * np.sqrt(days_ahead)

                return {
                    "prediction": {
                        "total_predicted_cost": round(float(total_predicted), 2),
                        "daily_average_cost": round(float(total_predicted / days_ahead), 2),
                        "confidence_interval": {
                            "low": round(max(0, float(total_predicted - margin_error)), 2),
                            "high": round(float(total_predicted + margin_error), 2)
                        }
                    },
                    "historical_data_points": len(historical_data),
                    "method": "linear_regression",
                    "trend": "increasing" if slope > 0 else "decreasing"
                }

            except np.linalg.LinAlgError:
                # Fallback to average
                avg_cost = np.mean(costs)
                predicted_total = avg_cost * days_ahead

                return {
                    "prediction": {
                        "total_predicted_cost": round(predicted_total, 2),
                        "daily_average_cost": round(avg_cost, 2),
                        "confidence_interval": {
                            "low": round(predicted_total * 0.8, 2),
                            "high": round(predicted_total * 1.2, 2)
                        }
                    },
                    "historical_data_points": len(historical_data),
                    "method": "simple_average_fallback"
                }

    except Exception as e:
        logger.error(f"Error predicting costs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to predict costs"
        )


# Budget tracking endpoint
@app.get("/costs/budget")
async def get_budget_status(
    user_id: str = Depends(require_auth),
    period: str = "monthly"
):
    """
    Get budget status and alerts for the authenticated user.

    Query Parameters:
    - period: Budget period - 'daily' or 'monthly' (default: monthly)
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_, extract
    from .database import get_db_session
    from .models import UsageLog

    if period not in ["daily", "monthly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Period must be 'daily' or 'monthly'"
        )

    try:
        with get_db_session() as db:
            # Calculate date range for current period
            now = datetime.utcnow()

            if period == "daily":
                period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                budget_limit = settings.get_litellm_config().get('cost_calculation', {}).get('budget_alerts', {}).get('user_limits', {}).get('default_daily_limit', 10.0)
            else:  # monthly
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                budget_limit = settings.get_litellm_config().get('cost_calculation', {}).get('budget_alerts', {}).get('user_limits', {}).get('default_monthly_limit', 300.0)

            # Get current spending for the period
            current_spending = db.query(func.sum(UsageLog.cost)).filter(
                UsageLog.user_id == user_id,
                UsageLog.timestamp >= period_start,
                UsageLog.timestamp <= now
            ).scalar() or 0.0

            current_spending = float(current_spending)

            # Calculate budget status
            budget_used_percentage = (current_spending / budget_limit) * 100 if budget_limit > 0 else 0
            remaining_budget = max(0, budget_limit - current_spending)

            # Determine alert level
            alert_thresholds = settings.get_litellm_config().get('cost_calculation', {}).get('budget_alerts', {}).get('alert_thresholds', [50, 80, 90, 95, 100])
            current_alert_level = None

            for threshold in sorted(alert_thresholds, reverse=True):
                if budget_used_percentage >= threshold:
                    current_alert_level = threshold
                    break

            # Get spending breakdown by model
            model_breakdown = db.query(
                UsageLog.model_name,
                func.sum(UsageLog.cost).label('total_cost'),
                func.sum(UsageLog.total_tokens).label('total_tokens'),
                func.count(UsageLog.id).label('request_count')
            ).filter(
                UsageLog.user_id == user_id,
                UsageLog.timestamp >= period_start,
                UsageLog.timestamp <= now
            ).group_by(UsageLog.model_name).all()

            breakdown = []
            for row in model_breakdown:
                breakdown.append({
                    "model_name": row.model_name,
                    "total_cost": round(float(row.total_cost), 2),
                    "total_tokens": int(row.total_tokens),
                    "request_count": row.request_count,
                    "percentage": round((float(row.total_cost) / current_spending) * 100, 1) if current_spending > 0 else 0
                })

            return {
                "budget_status": {
                    "period": period,
                    "period_start": period_start.isoformat(),
                    "budget_limit": round(budget_limit, 2),
                    "current_spending": round(current_spending, 2),
                    "remaining_budget": round(remaining_budget, 2),
                    "budget_used_percentage": round(budget_used_percentage, 1),
                    "alert_level": current_alert_level,
                    "alert_triggered": current_alert_level is not None
                },
                "model_breakdown": breakdown,
                "currency": settings.get_litellm_config().get('cost_calculation', {}).get('currency', 'USD')
            }

    except Exception as e:
        logger.error(f"Error retrieving budget status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve budget status"
        )


# Cost reporting dashboard endpoint
@app.get("/costs/dashboard")
async def get_cost_dashboard(
    user_id: str = Depends(require_auth),
    period: str = "monthly",
    limit: int = 30
):
    """
    Get comprehensive cost dashboard data for analytics and reporting.

    Query Parameters:
    - period: Reporting period grouping - 'daily', 'weekly', 'monthly' (default: monthly)
    - limit: Number of data points to return (default: 30, max: 365)
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_, extract, case
    from .database import get_db_session
    from .models import UsageLog

    if period not in ["daily", "weekly", "monthly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Period must be 'daily', 'weekly', or 'monthly'"
        )

    if limit > 365:
        limit = 365
    if limit < 1:
        limit = 1

    try:
        with get_db_session() as db:
            # Calculate date range
            end_date = datetime.utcnow()
            if period == "daily":
                start_date = end_date - timedelta(days=limit)
                date_trunc = func.date(UsageLog.timestamp)
                period_label = "day"
            elif period == "weekly":
                start_date = end_date - timedelta(weeks=limit)
                # SQLite week calculation (starts on Monday)
                date_trunc = func.strftime('%Y-%W', UsageLog.timestamp)
                period_label = "week"
            else:  # monthly
                start_date = end_date - timedelta(days=limit*30)  # Approximate
                date_trunc = func.strftime('%Y-%m', UsageLog.timestamp)
                period_label = "month"

            # Get time series data
            time_series_query = db.query(
                date_trunc.label('period'),
                func.sum(UsageLog.cost).label('total_cost'),
                func.sum(UsageLog.total_tokens).label('total_tokens'),
                func.count(UsageLog.id).label('total_requests'),
                func.avg(UsageLog.response_time_ms).label('avg_response_time'),
                func.count(case((UsageLog.status_code >= 400, 1))).label('error_count')
            ).filter(
                UsageLog.user_id == user_id,
                UsageLog.timestamp >= start_date,
                UsageLog.timestamp <= end_date
            ).group_by(date_trunc).order_by(date_trunc)

            time_series_data = time_series_query.all()

            # Get model distribution
            model_distribution = db.query(
                UsageLog.model_name,
                func.sum(UsageLog.cost).label('total_cost'),
                func.sum(UsageLog.total_tokens).label('total_tokens'),
                func.count(UsageLog.id).label('request_count'),
                func.avg(UsageLog.cost).label('avg_cost_per_request')
            ).filter(
                UsageLog.user_id == user_id,
                UsageLog.timestamp >= start_date,
                UsageLog.timestamp <= end_date
            ).group_by(UsageLog.model_name).order_by(func.sum(UsageLog.cost).desc()).all()

            # Get provider distribution
            provider_distribution = db.query(
                UsageLog.provider,
                func.sum(UsageLog.cost).label('total_cost'),
                func.count(UsageLog.id).label('request_count')
            ).filter(
                UsageLog.user_id == user_id,
                UsageLog.timestamp >= start_date,
                UsageLog.timestamp <= end_date,
                UsageLog.provider.isnot(None)
            ).group_by(UsageLog.provider).order_by(func.sum(UsageLog.cost).desc()).all()

            # Calculate summary statistics
            total_cost = sum(float(row.total_cost) for row in time_series_data)
            total_tokens = sum(int(row.total_tokens) for row in time_series_data)
            total_requests = sum(int(row.total_requests) for row in time_series_data)
            total_errors = sum(int(row.error_count) for row in time_series_data)

            # Format time series data
            time_series = []
            for row in time_series_data:
                time_series.append({
                    "period": row.period,
                    "total_cost": round(float(row.total_cost), 2),
                    "total_tokens": int(row.total_tokens),
                    "total_requests": int(row.total_requests),
                    "avg_response_time_ms": round(float(row.avg_response_time or 0), 1),
                    "error_count": int(row.error_count),
                    "error_rate": round((int(row.error_count) / int(row.total_requests)) * 100, 2) if int(row.total_requests) > 0 else 0
                })

            # Format model distribution
            models = []
            for row in model_distribution:
                models.append({
                    "model_name": row.model_name,
                    "total_cost": round(float(row.total_cost), 2),
                    "total_tokens": int(row.total_tokens),
                    "request_count": int(row.request_count),
                    "avg_cost_per_request": round(float(row.avg_cost_per_request or 0), 4),
                    "cost_percentage": round((float(row.total_cost) / total_cost) * 100, 1) if total_cost > 0 else 0
                })

            # Format provider distribution
            providers = []
            for row in provider_distribution:
                providers.append({
                    "provider": row.provider,
                    "total_cost": round(float(row.total_cost), 2),
                    "request_count": int(row.request_count),
                    "cost_percentage": round((float(row.total_cost) / total_cost) * 100, 1) if total_cost > 0 else 0
                })

            return {
                "summary": {
                    "total_cost": round(total_cost, 2),
                    "total_tokens": total_tokens,
                    "total_requests": total_requests,
                    "total_errors": total_errors,
                    "error_rate": round((total_errors / total_requests) * 100, 2) if total_requests > 0 else 0,
                    "avg_cost_per_request": round(total_cost / total_requests, 4) if total_requests > 0 else 0,
                    "currency": settings.get_litellm_config().get('cost_calculation', {}).get('currency', 'USD')
                },
                "time_series": {
                    "period_type": period_label,
                    "data": time_series
                },
                "model_distribution": models,
                "provider_distribution": providers,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

    except Exception as e:
        logger.error(f"Error retrieving cost dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost dashboard"
        )


# JWT Authentication endpoints
@app.post("/auth/login")
async def jwt_login(request: Request):
    """
    JWT login endpoint.

    Accepts username/password and returns JWT access and refresh tokens.
    Note: This is a demo implementation - in production, validate against user database.
    """
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password required"
            )

        # Authenticate user (demo implementation)
        from .auth import authenticator
        tokens = authenticator.authenticate_jwt_user(username, password)

        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@app.post("/auth/refresh")
async def jwt_refresh(request: Request):
    """
    JWT token refresh endpoint.

    Accepts a valid refresh token and returns new access and refresh tokens.
    """
    try:
        data = await request.json()
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )

        # Validate and refresh tokens
        from .auth import authenticator
        new_tokens = authenticator.refresh_access_token(refresh_token)

        if not new_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        return new_tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@app.post("/auth/logout")
async def jwt_logout(request: Request):
    """
    JWT logout endpoint.

    Revokes the refresh token to prevent further token refresh.
    """
    try:
        data = await request.json()
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )

        # Revoke refresh token
        from .auth import authenticator
        revoked = authenticator.revoke_refresh_token(refresh_token)

        if not revoked:
            # Token might already be invalid/expired, but we still return success
            logger.info("Attempted to revoke already invalid refresh token")

        return {"message": "Successfully logged out"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# Rate limiting monitoring endpoints
@app.get("/admin/rate-limits")
async def get_rate_limits(user_id: str = Depends(require_auth)):
    """
    Get rate limiting statistics for all users (admin endpoint).

    Requires authentication. Returns current rate limiting status for monitoring.
    """
    try:
        from .rate_limiter import get_all_rate_limit_stats

        # Only allow admin users to access this endpoint
        if not (user_id == "api_user" or user_id.startswith("admin")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        stats = get_all_rate_limit_stats()
        return {
            "rate_limits": stats,
            "total_users": len(stats),
            "timestamp": int(time.time())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving rate limits: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit statistics"
        )


@app.get("/rate-limits/my-limits")
async def get_my_rate_limits(user_id: str = Depends(require_auth)):
    """
    Get rate limiting statistics for the current user.

    Returns current rate limit status and usage for the authenticated user.
    """
    try:
        from .rate_limiter import get_rate_limit_stats

        stats = get_rate_limit_stats(user_id)
        config = settings.get_litellm_config()
        router_settings = config.get('router_settings', {})
        rate_limit_settings = router_settings.get('rate_limit_per_user', {})

        return {
            "user_id": user_id,
            "current_usage": stats,
            "config": {
                "requests_per_minute": rate_limit_settings.get('requests_per_minute', settings.rate_limit_requests),
                "window_seconds": 60
            },
            "timestamp": int(time.time())
        }

    except Exception as e:
        logger.error(f"Error retrieving user rate limits: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit information"
        )


@app.post("/admin/rate-limits/reset/{user_id}")
async def reset_user_rate_limit(
    user_id: str,
    requesting_user: str = Depends(require_auth)
):
    """
    Reset rate limiting for a specific user (admin endpoint).

    Path Parameters:
    - user_id: User ID to reset rate limits for

    Requires admin authentication.
    """
    try:
        # Only allow admin users to reset rate limits
        if not (requesting_user == "api_user" or requesting_user.startswith("admin")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        from .rate_limiter import reset_user_rate_limit as reset_limit

        reset_limit(user_id)
        logger.info(f"Rate limits reset for user: {user_id} by admin: {requesting_user}")

        return {"message": f"Rate limits reset for user {user_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting rate limits: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset rate limits"
        )


# Prometheus metrics endpoint
@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus format for monitoring and alerting.
    No authentication required for monitoring systems.
    """
    try:
        from .metrics import metrics_collector

        # Update business metrics before returning
        metrics_collector.update_business_metrics()

        metrics_data = metrics_collector.get_metrics()
        return Response(
            content=metrics_data,
            media_type=metrics_collector.get_metrics_content_type()
        )

    except Exception as e:
        logger.error(f"Error serving metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "name": "ChatVault",
        "version": "1.0.0",
        "description": "OpenAI-compatible chat proxy with usage tracking",
        "docs": "/docs" if settings.debug else None,
        "health": "/health"
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Global HTTP exception handler.

    Provides consistent error responses.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "invalid_request_error",
                "code": exc.status_code
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.

    Logs errors and returns generic error response.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "type": "internal_server_error",
                "code": 500
            }
        }
    )


def main():
    """
    Main entry point for running the ChatVault server.
    """
    logger.info(f"Starting ChatVault server on {settings.host}:{settings.port}")

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()