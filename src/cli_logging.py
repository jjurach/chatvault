"""
Logging system for ChatVault CLI

Provides JSON-formatted logging with timestamps, client identification,
model details, and configurable verbosity for request/response content.
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Optional, TextIO, List
from pathlib import Path


class CLILogger:
    """
    CLI-specific logger that outputs JSON-formatted logs.

    Supports both file and stdout output with configurable verbosity.
    """

    def __init__(self, logfile: Optional[str] = None, verbose: bool = False):
        """
        Initialize the CLI logger.

        Args:
            logfile: Path to log file (None for stdout)
            verbose: Whether to log full content or truncated portions
        """
        self.logfile = logfile
        self.verbose = verbose
        self.output_stream: TextIO = self._setup_output_stream()

    def _setup_output_stream(self) -> TextIO:
        """
        Set up the output stream for logging.

        Returns:
            File stream for logging output
        """
        if self.logfile:
            log_path = Path(self.logfile)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            return open(log_path, 'a', encoding='utf-8')
        else:
            return sys.stdout

    def log_request(self, client: str, model: str, request_data: Dict[str, Any],
                   request_id: Optional[str] = None) -> None:
        """
        Log an incoming request.

        Args:
            client: Client identifier
            model: Model being requested
            request_data: Request payload
            request_id: Optional request identifier
        """
        log_entry = self._create_base_log_entry("request", client, model, request_id)
        log_entry.update({
            "request": self._truncate_content(request_data, "request") if not self.verbose else request_data,
            "truncated": not self.verbose
        })

        self._write_log_entry(log_entry)

    def log_response(self, client: str, model: str, response_data: Dict[str, Any],
                    request_id: Optional[str] = None, error: Optional[str] = None) -> None:
        """
        Log an outgoing response.

        Args:
            client: Client identifier
            model: Model that was used
            response_data: Response payload
            request_id: Optional request identifier
            error: Optional error message
        """
        log_entry = self._create_base_log_entry("response", client, model, request_id)

        if error:
            log_entry.update({
                "error": error,
                "success": False
            })
        else:
            log_entry.update({
                "response": self._truncate_content(response_data, "response") if not self.verbose else response_data,
                "truncated": not self.verbose,
                "success": True
            })

        self._write_log_entry(log_entry)

    def log_request_response(self, client: str, model: str, request_data: Dict[str, Any],
                           response_data: Dict[str, Any], request_id: Optional[str] = None,
                           verbose: bool = False) -> None:
        """
        Log a complete request-response pair.

        Args:
            client: Client identifier
            model: Model that was used
            request_data: Request payload
            response_data: Response payload
            request_id: Optional request identifier
            verbose: Override verbosity for this log entry
        """
        log_entry = self._create_base_log_entry("request_response", client, model, request_id)
        use_verbose = verbose or self.verbose

        log_entry.update({
            "request": self._truncate_content(request_data, "request") if not use_verbose else request_data,
            "response": self._truncate_content(response_data, "response") if not use_verbose else response_data,
            "truncated": not use_verbose,
            "success": True
        })

        self._write_log_entry(log_entry)

    def log_error(self, client: Optional[str], error_message: str,
                 request_id: Optional[str] = None, model: Optional[str] = None) -> None:
        """
        Log an error.

        Args:
            client: Optional client identifier
            error_message: Error message
            request_id: Optional request identifier
            model: Optional model name
        """
        log_entry = self._create_base_log_entry("error", client or "unknown", model, request_id)
        log_entry.update({
            "error": error_message,
            "success": False
        })

        self._write_log_entry(log_entry)

    def log_info(self, message: str, client: Optional[str] = None,
                model: Optional[str] = None, request_id: Optional[str] = None) -> None:
        """
        Log an informational message.

        Args:
            message: Info message
            client: Optional client identifier
            model: Optional model name
            request_id: Optional request identifier
        """
        log_entry = self._create_base_log_entry("info", client, model, request_id)
        log_entry.update({
            "message": message,
            "success": True
        })

        self._write_log_entry(log_entry)

    def _create_base_log_entry(self, event_type: str, client: Optional[str] = None,
                             model: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a base log entry with common fields.

        Args:
            event_type: Type of log event
            client: Optional client identifier
            model: Optional model name
            request_id: Optional request identifier

        Returns:
            Base log entry dictionary
        """
        # Get current timestamp in ISO format
        timestamp = datetime.utcnow().isoformat() + 'Z'

        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "version": "1.0"
        }

        if client:
            log_entry["client"] = client

        if model:
            log_entry["model"] = model

        if request_id:
            log_entry["request_id"] = request_id

        return log_entry

    def _truncate_content(self, content: Any, content_type: str) -> Any:
        """
        Truncate content based on type and verbosity settings.

        Args:
            content: Content to potentially truncate
            content_type: Type of content ("request" or "response")

        Returns:
            Truncated or full content
        """
        if isinstance(content, dict):
            return self._truncate_dict_content(content, content_type)
        elif isinstance(content, list):
            return self._truncate_list_content(content, content_type)
        elif isinstance(content, str):
            return self._truncate_string_content(content, content_type)
        else:
            return content

    def _truncate_dict_content(self, content: Dict[str, Any], content_type: str) -> Dict[str, Any]:
        """
        Truncate dictionary content intelligently.

        Args:
            content: Dictionary to truncate
            content_type: Type of content

        Returns:
            Truncated dictionary
        """
        truncated = {}

        for key, value in content.items():
            if key == "messages" and isinstance(value, list):
                # Truncate message content
                truncated[key] = self._truncate_messages(value)
            elif key == "choices" and isinstance(value, list):
                # Truncate response choices
                truncated[key] = self._truncate_choices(value)
            elif isinstance(value, (dict, list)):
                truncated[key] = self._truncate_content(value, content_type)
            elif isinstance(value, str) and len(value) > 100:
                truncated[key] = value[:100] + "..."
            else:
                truncated[key] = value

        return truncated

    def _truncate_list_content(self, content: List[Any], content_type: str) -> List[Any]:
        """
        Truncate list content.

        Args:
            content: List to truncate
            content_type: Type of content

        Returns:
            Truncated list
        """
        # For now, keep lists as-is but truncate their elements
        return [self._truncate_content(item, content_type) for item in content]

    def _truncate_string_content(self, content: str, content_type: str) -> str:
        """
        Truncate string content.

        Args:
            content: String to truncate
            content_type: Type of content

        Returns:
            Truncated string
        """
        max_length = 200 if content_type == "request" else 500
        if len(content) > max_length:
            return content[:max_length] + "..."
        return content

    def _truncate_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Truncate chat messages for logging.

        Args:
            messages: List of message dictionaries

        Returns:
            Truncated messages
        """
        truncated_messages = []

        for msg in messages:
            truncated_msg = dict(msg)
            if "content" in truncated_msg and isinstance(truncated_msg["content"], str):
                if len(truncated_msg["content"]) > 100:
                    truncated_msg["content"] = truncated_msg["content"][:100] + "..."
            truncated_messages.append(truncated_msg)

        return truncated_messages

    def _truncate_choices(self, choices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Truncate response choices for logging.

        Args:
            choices: List of choice dictionaries

        Returns:
            Truncated choices
        """
        truncated_choices = []

        for choice in choices:
            truncated_choice = dict(choice)
            if "message" in truncated_choice and isinstance(truncated_choice["message"], dict):
                if "content" in truncated_choice["message"] and isinstance(truncated_choice["message"]["content"], str):
                    content = truncated_choice["message"]["content"]
                    if len(content) > 200:
                        truncated_choice["message"]["content"] = content[:200] + "..."
            truncated_choices.append(truncated_choice)

        return truncated_choices

    def _write_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """
        Write a log entry to the output stream.

        Args:
            log_entry: Log entry dictionary to write
        """
        try:
            json_line = json.dumps(log_entry, ensure_ascii=False)
            print(json_line, file=self.output_stream, flush=True)
        except Exception as e:
            # Fallback error logging
            error_entry = {
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "event_type": "logging_error",
                "error": f"Failed to write log entry: {e}",
                "original_entry": str(log_entry)[:500]
            }
            try:
                json_line = json.dumps(error_entry, ensure_ascii=False)
                print(json_line, file=self.output_stream, flush=True)
            except:
                # Last resort - write to stderr
                print(f"CRITICAL: Logging failed: {e}", file=sys.stderr)

    def close(self) -> None:
        """
        Close the logger and clean up resources.
        """
        if self.logfile and self.output_stream != sys.stdout:
            self.output_stream.close()


def setup_logging(logfile: Optional[str] = None, verbose: bool = False) -> CLILogger:
    """
    Create and return a configured CLI logger.

    Args:
        logfile: Optional path to log file
        verbose: Whether to enable verbose logging

    Returns:
        Configured CLILogger instance
    """
    return CLILogger(logfile=logfile, verbose=verbose)


# Global logger instance for convenience
_default_logger: Optional[CLILogger] = None


def get_default_logger() -> CLILogger:
    """
    Get the default logger instance.

    Returns:
        Default CLILogger instance

    Raises:
        RuntimeError: If no default logger has been set
    """
    if _default_logger is None:
        raise RuntimeError("No default logger configured. Call setup_logging() first.")
    return _default_logger


def set_default_logger(logger: CLILogger) -> None:
    """
    Set the default logger instance.

    Args:
        logger: CLILogger instance to set as default
    """
    global _default_logger
    _default_logger = logger