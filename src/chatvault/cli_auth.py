"""
Client authentication and authorization for ChatVault CLI

Handles bearer token validation and model access control for CLI clients.
"""

from typing import Dict, Any, Optional
import hashlib


class CLIAuthError(Exception):
    """Exception raised for CLI authentication/authorization errors."""
    pass


def authenticate_client(client_name: str, bearer_token: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Authenticate a client using bearer token.

    Args:
        client_name: Name of the client attempting authentication
        bearer_token: Bearer token provided by the client
        config: Configuration dictionary containing client definitions

    Returns:
        Client configuration dictionary if authentication succeeds

    Raises:
        CLIAuthError: If authentication fails
    """
    # Import cli_config directly (no relative import to avoid issues with installed package)
    import sys
    import os
    current_dir = os.path.dirname(__file__)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from cli_config import get_client_config, validate_client_config

    # Get client configuration
    client_config = get_client_config(config, client_name)
    if client_config is None:
        raise CLIAuthError(f"Unknown client: {client_name}")

    # Validate client configuration structure
    try:
        validate_client_config(client_config)
    except Exception as e:
        raise CLIAuthError(f"Invalid client configuration for '{client_name}': {e}")

    # Check bearer token
    expected_token = client_config.get('bearer_token')
    if not expected_token:
        raise CLIAuthError(f"No bearer token configured for client '{client_name}'")

    # Use constant-time comparison to prevent timing attacks
    if not _constant_time_compare(bearer_token, expected_token):
        raise CLIAuthError(f"Invalid bearer token for client '{client_name}'")

    return client_config


def validate_model_access(client_config: Dict[str, Any], requested_model: str) -> None:
    """
    Validate that a client is authorized to access a specific model.

    Args:
        client_config: Client configuration dictionary
        requested_model: Name of the model being requested

    Raises:
        CLIAuthError: If the client is not authorized for the model
    """
    allowed_models = client_config.get('allowed_models', [])

    # Check if client has access to all models
    if '*' in allowed_models:
        return

    # Check if requested model is in allowed list
    if requested_model not in allowed_models:
        raise CLIAuthError(
            f"Client '{client_config.get('name', 'unknown')}' is not authorized "
            f"to access model '{requested_model}'. Allowed models: {allowed_models}"
        )


def _constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.

    Args:
        a: First string to compare
        b: Second string to compare

    Returns:
        True if strings are equal, False otherwise
    """
    if len(a) != len(b):
        return False

    # Use XOR to compare bytes
    result = 0
    for x, y in zip(a.encode('utf-8'), b.encode('utf-8')):
        result |= x ^ y

    return result == 0


def get_client_name_from_token(bearer_token: str, config: Dict[str, Any]) -> Optional[str]:
    """
    Get client name from bearer token (for logging purposes).

    Args:
        bearer_token: Bearer token to look up
        config: Configuration dictionary

    Returns:
        Client name if found, None otherwise
    """
    clients = config.get('clients', {})

    for client_name, client_config in clients.items():
        expected_token = client_config.get('bearer_token')
        if expected_token and _constant_time_compare(bearer_token, expected_token):
            return client_name

    return None


def hash_token_for_logging(bearer_token: str) -> str:
    """
    Create a hash of the bearer token for logging purposes.

    This allows logging client identity without exposing the actual token.

    Args:
        bearer_token: Bearer token to hash

    Returns:
        SHA-256 hash of the token (first 16 characters)
    """
    # Create SHA-256 hash and return first 16 characters
    token_hash = hashlib.sha256(bearer_token.encode('utf-8')).hexdigest()
    return token_hash[:16]


def check_client_exists(client_name: str, config: Dict[str, Any]) -> bool:
    """
    Check if a client exists in the configuration.

    Args:
        client_name: Name of the client to check
        config: Configuration dictionary

    Returns:
        True if client exists, False otherwise
    """
    clients = config.get('clients', {})
    return client_name in clients


def get_client_permissions(client_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of client permissions for display/logging.

    Args:
        client_config: Client configuration dictionary

    Returns:
        Dictionary with permission summary
    """
    allowed_models = client_config.get('allowed_models', [])

    return {
        'allows_all_models': '*' in allowed_models,
        'allowed_models': [model for model in allowed_models if model != '*'],
        'model_count': len(allowed_models) if '*' not in allowed_models else -1
    }


def validate_client_name(client_name: str) -> None:
    """
    Validate that a client name follows acceptable patterns.

    Args:
        client_name: Client name to validate

    Raises:
        CLIAuthError: If client name is invalid
    """
    if not client_name or not client_name.strip():
        raise CLIAuthError("Client name cannot be empty")

    if len(client_name) > 64:
        raise CLIAuthError("Client name too long (max 64 characters)")

    # Allow alphanumeric, underscores, and hyphens
    if not all(c.isalnum() or c in '-_' for c in client_name):
        raise CLIAuthError("Client name contains invalid characters (only alphanumeric, underscore, and hyphen allowed)")


def create_client_token() -> str:
    """
    Generate a random bearer token for a new client.

    Returns:
        Random 64-character hex string suitable for use as bearer token
    """
    import secrets
    return secrets.token_hex(32)  # 64 characters


def validate_token_format(bearer_token: str) -> None:
    """
    Validate that a bearer token follows expected format.

    Args:
        bearer_token: Token to validate

    Raises:
        CLIAuthError: If token format is invalid
    """
    if not bearer_token or not bearer_token.strip():
        raise CLIAuthError("Bearer token cannot be empty")

    # Should be reasonably long (at least 32 characters for security)
    if len(bearer_token) < 32:
        raise CLIAuthError("Bearer token too short (minimum 32 characters)")

    # Should not contain control characters
    if any(ord(c) < 32 for c in bearer_token):
        raise CLIAuthError("Bearer token contains invalid control characters")