"""
Streaming response handler for ChatVault.

This module provides utilities for handling streaming LLM responses,
converting them to OpenAI-compatible Server-Sent Events (SSE) format,
and capturing final usage metadata.
"""

import json
import logging
from typing import Dict, Any, AsyncGenerator, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamingResponseHandler:
    """
    Handler for converting LiteLLM streaming responses to OpenAI-compatible SSE format.

    Manages the streaming lifecycle, captures usage metadata, and formats responses
    according to OpenAI's streaming API specification.
    """

    def __init__(self):
        self.usage_data = None
        self.response_started = False
        self.first_chunk_sent = False

    def reset(self):
        """Reset handler state for new request."""
        self.usage_data = None
        self.response_started = False
        self.first_chunk_sent = False

    async def process_stream(
        self,
        stream: AsyncGenerator[Dict[str, Any], None],
        request_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Process a streaming response and yield OpenAI-compatible SSE events.

        Args:
            stream: Async generator yielding LiteLLM response chunks
            request_id: Unique request identifier

        Yields:
            Server-Sent Events formatted strings
        """
        self.reset()

        try:
            async for chunk in stream:
                # Process each chunk and yield SSE events
                events = self._process_chunk(chunk, request_id)
                for event in events:
                    yield event

            # Send final usage chunk if available
            if self.usage_data:
                yield self._create_usage_chunk()

        except Exception as e:
            logger.error(f"Error processing stream: {e}")
            # Send error chunk
            yield self._create_error_chunk(str(e))
            raise

    def _process_chunk(self, chunk: Dict[str, Any], request_id: str) -> List[str]:
        """
        Process a single response chunk and return SSE events.

        Args:
            chunk: LiteLLM response chunk
            request_id: Request identifier

        Returns:
            List of SSE event strings
        """
        events = []

        try:
            # Convert LiteLLM chunk to OpenAI format
            openai_chunk = self._convert_to_openai_format(chunk, request_id)

            # Extract usage data if present (usually in final chunk)
            if hasattr(chunk, 'usage') and chunk.usage:
                self.usage_data = self._extract_usage_from_chunk(chunk)

            # Create SSE event
            event = self._create_sse_event(openai_chunk)
            events.append(event)

            self.response_started = True

        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            # Create error event
            error_chunk = {
                "id": f"chatcmpl-{request_id}",
                "object": "chat.completion.chunk",
                "created": int(datetime.utcnow().timestamp()),
                "model": "unknown",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "error"
                }],
                "usage": None
            }
            events.append(self._create_sse_event(error_chunk))

        return events

    def _convert_to_openai_format(self, chunk: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Convert LiteLLM chunk to OpenAI-compatible format.

        Args:
            chunk: LiteLLM response chunk
            request_id: Request identifier

        Returns:
            OpenAI-formatted chunk
        """
        # Extract basic information
        chunk_id = getattr(chunk, 'id', f"chatcmpl-{request_id}")
        model = getattr(chunk, 'model', 'unknown')
        created = getattr(chunk, 'created', int(datetime.utcnow().timestamp()))

        # Handle choices
        choices = []
        if hasattr(chunk, 'choices') and chunk.choices:
            for i, choice in enumerate(chunk.choices):
                openai_choice = {
                    "index": getattr(choice, 'index', i),
                    "delta": {},
                    "finish_reason": None
                }

                # Extract delta content
                if hasattr(choice, 'delta'):
                    delta = choice.delta
                    if hasattr(delta, 'content') and delta.content is not None:
                        openai_choice["delta"]["content"] = delta.content
                    if hasattr(delta, 'role') and delta.role:
                        openai_choice["delta"]["role"] = delta.role
                    # Add other delta fields as needed (tool_calls, etc.)

                # Extract finish reason
                if hasattr(choice, 'finish_reason') and choice.finish_reason:
                    openai_choice["finish_reason"] = choice.finish_reason

                choices.append(openai_choice)

        # Create OpenAI-formatted chunk
        openai_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": choices,
            "usage": None  # Usage comes in separate chunk
        }

        return openai_chunk

    def _extract_usage_from_chunk(self, chunk: Any) -> Optional[Dict[str, Any]]:
        """
        Extract usage information from a response chunk.

        Args:
            chunk: Response chunk containing usage data

        Returns:
            Usage data dictionary or None
        """
        try:
            if hasattr(chunk, 'usage') and chunk.usage:
                usage = chunk.usage
                return {
                    "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(usage, 'completion_tokens', 0),
                    "total_tokens": getattr(usage, 'total_tokens', 0)
                }
        except Exception as e:
            logger.warning(f"Could not extract usage from chunk: {e}")

        return None

    def _create_usage_chunk(self) -> str:
        """
        Create a usage data SSE event.

        Returns:
            SSE event string with usage data
        """
        if not self.usage_data:
            return ""

        usage_chunk = {
            "id": "usage",
            "object": "chat.completion.chunk",
            "created": int(datetime.utcnow().timestamp()),
            "model": "usage",
            "choices": [],
            "usage": self.usage_data
        }

        return self._create_sse_event(usage_chunk)

    def _create_error_chunk(self, error_message: str) -> str:
        """
        Create an error SSE event.

        Args:
            error_message: Error message

        Returns:
            SSE event string with error
        """
        error_chunk = {
            "id": "error",
            "object": "chat.completion.chunk",
            "created": int(datetime.utcnow().timestamp()),
            "model": "error",
            "choices": [{
                "index": 0,
                "delta": {"content": f"Error: {error_message}"},
                "finish_reason": "error"
            }],
            "usage": None
        }

        return self._create_sse_event(error_chunk)

    def _create_sse_event(self, data: Dict[str, Any]) -> str:
        """
        Create a Server-Sent Event string from data.

        Args:
            data: Data to serialize

        Returns:
            SSE formatted string
        """
        json_data = json.dumps(data, ensure_ascii=False)
        return f"data: {json_data}\n\n"


class OpenAIStreamingResponse:
    """
    OpenAI-compatible streaming response formatter.

    Provides utilities for formatting streaming responses according to
    OpenAI's Chat Completions API specification.
    """

    @staticmethod
    def create_completion_chunk(
        content: str,
        model: str,
        request_id: str,
        finish_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an OpenAI-formatted completion chunk.

        Args:
            content: Content for this chunk
            model: Model name
            request_id: Request identifier
            finish_reason: Finish reason if this is the final chunk

        Returns:
            OpenAI-formatted chunk
        """
        chunk = {
            "id": f"chatcmpl-{request_id}",
            "object": "chat.completion.chunk",
            "created": int(datetime.utcnow().timestamp()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason
            }],
            "usage": None
        }

        return chunk

    @staticmethod
    def create_usage_chunk(usage_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Create an OpenAI-formatted usage chunk.

        Args:
            usage_data: Usage statistics
            request_id: Request identifier

        Returns:
            OpenAI-formatted usage chunk
        """
        chunk = {
            "id": f"chatcmpl-{request_id}",
            "object": "chat.completion.chunk",
            "created": int(datetime.utcnow().timestamp()),
            "model": "usage",
            "choices": [],
            "usage": usage_data
        }

        return chunk

    @staticmethod
    def format_as_sse(data: Dict[str, Any]) -> str:
        """
        Format data as Server-Sent Event.

        Args:
            data: Data to format

        Returns:
            SSE formatted string
        """
        json_data = json.dumps(data, ensure_ascii=False)
        return f"data: {json_data}\n\n"

    @staticmethod
    def create_done_event() -> str:
        """
        Create the final 'done' event for streaming.

        Returns:
            SSE done event
        """
        return "data: [DONE]\n\n"


# Global handler instance
streaming_handler = StreamingResponseHandler()


async def handle_streaming_response(
    stream: AsyncGenerator[Dict[str, Any], None],
    request_id: str
) -> AsyncGenerator[str, None]:
    """
    Convenience function for handling streaming responses.

    Args:
        stream: LiteLLM streaming response
        request_id: Request identifier

    Yields:
        SSE formatted events
    """
    async for event in streaming_handler.process_stream(stream, request_id):
        yield event


def create_error_response(error_message: str, status_code: int = 500) -> Dict[str, Any]:
    """
    Create an OpenAI-compatible error response.

    Args:
        error_message: Error message
        status_code: HTTP status code

    Returns:
        Error response dictionary
    """
    return {
        "error": {
            "message": error_message,
            "type": "invalid_request_error",
            "code": status_code
        }
    }


def validate_openai_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize an OpenAI-compatible request.

    Args:
        request_data: Raw request data

    Returns:
        Validated and normalized request data

    Raises:
        ValueError: If validation fails
    """
    # Required fields
    if "model" not in request_data:
        raise ValueError("model field is required")

    if "messages" not in request_data:
        raise ValueError("messages field is required")

    # Validate messages format
    messages = request_data["messages"]
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")

    for msg in messages:
        if not isinstance(msg, dict):
            raise ValueError("each message must be a dictionary")
        if "role" not in msg or "content" not in msg:
            raise ValueError("each message must have 'role' and 'content' fields")

    # Set defaults
    normalized = request_data.copy()

    # Default temperature
    if "temperature" not in normalized:
        normalized["temperature"] = 0.7

    # Default max_tokens
    if "max_tokens" not in normalized:
        normalized["max_tokens"] = 4096

    # Default stream
    if "stream" not in normalized:
        normalized["stream"] = False

    return normalized