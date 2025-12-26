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
async def health_check():
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
            "api_key_configured": auth_health["api_key_configured"]
        }
    except Exception as e:
        health["components"]["authentication"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "unhealthy"

    return health


# Models endpoint
@app.get("/v1/models")
async def list_models(user_id: str = Depends(get_current_user)):
    """
    OpenAI-compatible models endpoint.

    Returns list of available models configured in ChatVault.
    """
    try:
        available_models = settings.get_available_models()

        # Format as OpenAI-compatible response
        models = []
        for model_name in available_models:
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
    offset: int = 0
):
    """
    Get usage statistics for the authenticated user.

    Returns recent usage logs with pagination.
    """
    # Placeholder - will be implemented when usage logging is complete
    return {
        "message": "Usage statistics endpoint - to be implemented",
        "user_id": user_id,
        "pagination": {
            "limit": limit,
            "offset": offset
        }
    }


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