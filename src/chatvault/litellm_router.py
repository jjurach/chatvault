"""
LiteLLM integration for ChatVault.

This module provides a unified interface for routing requests to multiple LLM providers
using LiteLLM, with support for streaming responses and usage tracking.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, List
from contextlib import asynccontextmanager

import litellm
from litellm import completion, acompletion
from litellm.utils import get_model_info, token_counter

from .config import settings
from .database import get_db_session
from .models import UsageLog

logger = logging.getLogger(__name__)


class LiteLLMRouter:
    """
    Router for handling LLM requests through LiteLLM.

    Provides unified interface for multiple providers with usage tracking.
    """

    def __init__(self):
        self.config = settings.get_litellm_config()
        self.model_list = self.config.get('model_list', [])

        # Configure LiteLLM
        self._configure_litellm()

        logger.info(f"LiteLLM router initialized with {len(self.model_list)} models")

    def _configure_litellm(self):
        """
        Configure LiteLLM with model list and settings.
        """
        if self.model_list:
            litellm.model_list = self.model_list
            logger.info("LiteLLM model list configured")
        else:
            logger.warning("No models configured in LiteLLM")

        # Set up logging and callbacks if needed
        # LiteLLM callbacks can be added here for additional tracking

    def _get_model_params(self, model_name: str) -> Dict[str, Any]:
        """
        Get the LiteLLM parameters for a model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary of parameters for LiteLLM completion
        """
        for model_config in self.model_list:
            if model_config.get('model_name') == model_name:
                litellm_params = model_config.get('litellm_params', {})
                return litellm_params.copy()

        raise ValueError(f"Model '{model_name}' not found in configuration")

    def get_available_models(self) -> List[str]:
        """
        Get list of available model names.

        Returns:
            List of configured model names
        """
        return [model.get('model_name', '') for model in self.model_list if model.get('model_name')]

    def validate_model(self, model_name: str) -> bool:
        """
        Validate that a model is configured and available.

        Args:
            model_name: Name of the model to validate

        Returns:
            True if model is available
        """
        available_models = self.get_available_models()
        return model_name in available_models

    def get_model_provider(self, model_name: str) -> Optional[str]:
        """
        Get the provider for a given model.

        Args:
            model_name: Model name

        Returns:
            Provider name or None
        """
        for model_config in self.model_list:
            if model_config.get('model_name') == model_name:
                litellm_params = model_config.get('litellm_params', {})
                model = litellm_params.get('model', '')

                # Determine provider from model string
                if model.startswith('claude'):
                    return 'anthropic'
                elif model.startswith('deepseek'):
                    return 'deepseek'
                elif model.startswith('gpt') or model.startswith('text-'):
                    return 'openai'
                elif ':' in model:  # Ollama models
                    return 'ollama'

        return None

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        user_id: str,
        request_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform a chat completion request.

        Args:
            model: Model name to use
            messages: List of message dictionaries
            user_id: User identifier for tracking
            request_id: Optional request ID for tracking
            **kwargs: Additional parameters for the completion

        Returns:
            Completion response dictionary
        """
        if not self.validate_model(model):
            raise ValueError(f"Model '{model}' is not configured")

        if not request_id:
            request_id = str(uuid.uuid4())

        start_time = time.time()

        try:
            # Get the actual model parameters from config
            model_params = self._get_model_params(model)

            # Merge with additional kwargs
            completion_kwargs = {**model_params, **kwargs}
            completion_kwargs['messages'] = messages

            # Make the completion request
            response = await acompletion(**completion_kwargs)

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Extract usage information
            usage_info = self._extract_usage_info(response, model)

            # Log usage to database
            await self._log_usage(
                user_id=user_id,
                model_name=model,
                request_id=request_id,
                usage_info=usage_info,
                response_time_ms=response_time_ms,
                provider=self.get_model_provider(model)
            )

            # Record metrics
            from .metrics import record_chat_completion_metrics
            record_chat_completion_metrics(
                user_id=user_id,
                model=model,
                provider=provider or "unknown",
                tokens_used=usage_info.get("total_tokens", 0),
                cost=usage_info.get("cost", 0.0),
                response_time=response_time_ms / 1000.0,  # Convert to seconds
                success=True
            )

            logger.info(f"Chat completion successful: {model}, tokens={usage_info.get('total_tokens', 0)}, time={response_time_ms}ms")

            return response

        except Exception as e:
            # Log failed request
            response_time_ms = int((time.time() - start_time) * 1000)

            await self._log_usage(
                user_id=user_id,
                model_name=model,
                request_id=request_id,
                usage_info={"error": str(e)},
                response_time_ms=response_time_ms,
                provider=self.get_model_provider(model),
                status_code=500
            )

            logger.error(f"Chat completion failed: {model}, error={e}")
            raise

    async def chat_completion_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        user_id: str,
        request_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Perform a streaming chat completion request.

        Args:
            model: Model name to use
            messages: List of message dictionaries
            user_id: User identifier for tracking
            request_id: Optional request ID for tracking
            **kwargs: Additional parameters

        Yields:
            Response chunks as they arrive
        """
        if not self.validate_model(model):
            raise ValueError(f"Model '{model}' is not configured")

        if not request_id:
            request_id = str(uuid.uuid4())

        start_time = time.time()
        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        final_chunk = None

        try:
            # Get the actual model parameters from config
            model_params = self._get_model_params(model)

            # Merge with additional kwargs
            completion_kwargs = {**model_params, **kwargs}
            completion_kwargs['messages'] = messages
            completion_kwargs['stream'] = True

            # Make streaming completion request
            response_stream = await acompletion(**completion_kwargs)

            async for chunk in response_stream:
                # Track the final chunk for usage information
                if chunk.choices and chunk.choices[0].finish_reason:
                    final_chunk = chunk

                yield chunk

            # After streaming is complete, log usage
            if final_chunk and hasattr(final_chunk, 'usage'):
                usage_info = self._extract_usage_info_from_chunk(final_chunk)
                total_usage.update(usage_info)

            response_time_ms = int((time.time() - start_time) * 1000)

            await self._log_usage(
                user_id=user_id,
                model_name=model,
                request_id=request_id,
                usage_info=total_usage,
                response_time_ms=response_time_ms,
                provider=self.get_model_provider(model)
            )

            # Record metrics
            from .metrics import record_chat_completion_metrics
            provider = self.get_model_provider(model)
            record_chat_completion_metrics(
                user_id=user_id,
                model=model,
                provider=provider or "unknown",
                tokens_used=total_usage.get("total_tokens", 0),
                cost=self._calculate_cost(model, total_usage),
                response_time=response_time_ms / 1000.0,  # Convert to seconds
                success=True
            )

            logger.info(f"Streaming completion successful: {model}, tokens={total_usage.get('total_tokens', 0)}, time={response_time_ms}ms")

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)

            await self._log_usage(
                user_id=user_id,
                model_name=model,
                request_id=request_id,
                usage_info={"error": str(e)},
                response_time_ms=response_time_ms,
                provider=self.get_model_provider(model),
                status_code=500
            )

            logger.error(f"Streaming completion failed: {model}, error={e}")
            raise

    def _extract_usage_info(self, response: Any, model: str) -> Dict[str, Any]:
        """
        Extract usage information from completion response.

        Args:
            response: LiteLLM response object
            model: Model name used

        Returns:
            Dictionary with usage statistics
        """
        usage_info = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0
        }

        # Extract from response usage field
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            usage_info["input_tokens"] = getattr(usage, 'prompt_tokens', 0)
            usage_info["output_tokens"] = getattr(usage, 'completion_tokens', 0)
            usage_info["total_tokens"] = getattr(usage, 'total_tokens', 0)

            # Calculate cost if enabled
            if settings.enable_cost_calculation:
                usage_info["cost"] = self._calculate_cost(model, usage_info)

        return usage_info

    def _extract_usage_info_from_chunk(self, chunk: Any) -> Dict[str, Any]:
        """
        Extract usage information from streaming response chunk.

        Args:
            chunk: Final response chunk with usage info

        Returns:
            Dictionary with usage statistics
        """
        usage_info = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0
        }

        if hasattr(chunk, 'usage') and chunk.usage:
            usage = chunk.usage
            usage_info["input_tokens"] = getattr(usage, 'prompt_tokens', 0)
            usage_info["output_tokens"] = getattr(usage, 'completion_tokens', 0)
            usage_info["total_tokens"] = getattr(usage, 'total_tokens', 0)

        return usage_info

    def _calculate_cost(self, model: str, usage_info: Dict[str, Any]) -> float:
        """
        Calculate cost for a request based on token usage.

        Args:
            model: User-friendly model name
            usage_info: Usage statistics

        Returns:
            Calculated cost in USD
        """
        try:
            # Get the actual LiteLLM model name
            litellm_model = settings.get_litellm_model_name(model)

            # First check for custom costs
            custom_costs = settings.get_custom_costs()
            if litellm_model and litellm_model in custom_costs:
                cost_config = custom_costs[litellm_model]
                input_cost = cost_config.get('input_cost_per_token', 0.0)
                output_cost = cost_config.get('output_cost_per_token', 0.0)

                input_tokens = usage_info.get("input_tokens", 0)
                output_tokens = usage_info.get("output_tokens", 0)

                total_cost = (input_tokens * input_cost) + (output_tokens * output_cost)
                return total_cost

            # Fall back to LiteLLM's built-in cost calculation
            if litellm_model:
                cost_result = litellm.cost_per_token(
                    model=litellm_model,
                    prompt_tokens=usage_info.get("input_tokens", 0),
                    completion_tokens=usage_info.get("output_tokens", 0)
                )

                # Handle different return types from LiteLLM
                if isinstance(cost_result, tuple):
                    # Some models return (input_cost, output_cost) tuple
                    if len(cost_result) >= 2:
                        input_cost, output_cost = cost_result[0], cost_result[1]
                        input_tokens = usage_info.get("input_tokens", 0)
                        output_tokens = usage_info.get("output_tokens", 0)
                        return (input_tokens * input_cost) + (output_tokens * output_cost)
                    else:
                        return 0.0
                elif isinstance(cost_result, (int, float)):
                    # Some models return total cost as float
                    return float(cost_result)
                else:
                    # Unknown format, return 0
                    return 0.0
            else:
                logger.warning(f"No LiteLLM model mapping found for {model}")
                return 0.0

        except Exception as e:
            logger.warning(f"Could not calculate cost for {model}: {e}")
            return 0.0

    async def _log_usage(
        self,
        user_id: str,
        model_name: str,
        request_id: str,
        usage_info: Dict[str, Any],
        response_time_ms: int,
        provider: Optional[str] = None,
        status_code: int = 200
    ):
        """
        Log usage information to the database.

        Args:
            user_id: User identifier
            model_name: Model name used
            request_id: Unique request identifier
            usage_info: Token usage statistics
            response_time_ms: Response time in milliseconds
            provider: LLM provider name
            status_code: HTTP status code
        """
        if not settings.enable_usage_logging:
            return

        try:
            # Use synchronous database session from async context
            from .database import SessionLocal
            db = SessionLocal()
            try:
                usage_log = UsageLog(
                    user_id=user_id,
                    model_name=model_name,
                    request_id=request_id,
                    input_tokens=usage_info.get("input_tokens", 0),
                    output_tokens=usage_info.get("output_tokens", 0),
                    total_tokens=usage_info.get("total_tokens", 0),
                    cost=usage_info.get("cost", 0.0),
                    provider=provider,
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                    request_metadata=str(usage_info) if "error" in usage_info else None
                )

                db.add(usage_log)
                db.commit()

                logger.debug(f"Usage logged: {model_name}, user={user_id}, tokens={usage_info.get('total_tokens', 0)}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to log usage: {e}")

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a model.

        Args:
            model_name: Name of the model

        Returns:
            Model information dictionary or None
        """
        try:
            # Find the actual model identifier from config
            for model_config in self.model_list:
                if model_config.get('model_name') == model_name:
                    litellm_params = model_config.get('litellm_params', {})
                    actual_model = litellm_params.get('model', model_name)

                    # Get model info from LiteLLM
                    info = get_model_info(actual_model)
                    return info

        except Exception as e:
            logger.warning(f"Could not get model info for {model_name}: {e}")

        return None


# Global router instance
router = LiteLLMRouter()


# Convenience functions for easy access
async def chat_completion(model: str, messages: List[Dict[str, Any]], user_id: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for chat completion.

    Args:
        model: Model name
        messages: Message list
        user_id: User identifier
        **kwargs: Additional parameters

    Returns:
        Completion response
    """
    return await router.chat_completion(model, messages, user_id, **kwargs)


async def chat_completion_stream(model: str, messages: List[Dict[str, Any]], user_id: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function for streaming chat completion.

    Args:
        model: Model name
        messages: Message list
        user_id: User identifier
        **kwargs: Additional parameters

    Yields:
        Response chunks
    """
    async for chunk in router.chat_completion_stream(model, messages, user_id, **kwargs):
        yield chunk


def get_available_models() -> List[str]:
    """
    Get list of available models.

    Returns:
        List of model names
    """
    return router.get_available_models()


def validate_model(model_name: str) -> bool:
    """
    Validate a model name.

    Args:
        model_name: Model to validate

    Returns:
        True if valid
    """
    return router.validate_model(model_name)