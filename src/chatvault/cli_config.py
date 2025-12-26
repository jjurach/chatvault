"""
Configuration management for ChatVault CLI

Handles loading and parsing of configuration files, including model definitions
and client authentication settings for CLI usage.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class CLIConfigError(Exception):
    """Exception raised for CLI configuration errors."""
    pass


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load and parse the ChatVault configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Parsed configuration dictionary

    Raises:
        CLIConfigError: If configuration file cannot be loaded or parsed
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise CLIConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if config is None:
            raise CLIConfigError(f"Configuration file is empty: {config_path}")

        # Validate required sections
        _validate_config_structure(config)

        # Expand environment variables
        config = _expand_env_vars(config)

        return config

    except yaml.YAMLError as e:
        raise CLIConfigError(f"Invalid YAML in configuration file: {e}")
    except Exception as e:
        raise CLIConfigError(f"Error loading configuration: {e}")


def _validate_config_structure(config: Dict[str, Any]) -> None:
    """
    Validate that the configuration has the required structure.

    Args:
        config: Configuration dictionary to validate

    Raises:
        CLIConfigError: If required sections are missing
    """
    # Check for models section (required)
    if 'model_list' not in config and 'models' not in config:
        raise CLIConfigError("Configuration must contain 'model_list' or 'models' section")

    # For CLI, we need clients section
    if 'clients' not in config:
        raise CLIConfigError("Configuration must contain 'clients' section for CLI usage")


def _expand_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively expand environment variables in configuration values.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with expanded environment variables
    """
    if isinstance(config, dict):
        return {key: _expand_env_vars(value) for key, value in config.items()}
    elif isinstance(config, list):
        return [_expand_env_vars(item) for item in config]
    elif isinstance(config, str):
        return os.path.expandvars(config)
    else:
        return config


def get_available_models(config: Dict[str, Any]) -> List[str]:
    """
    Get list of available model names from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of model names
    """
    models = []

    # Check both possible model section names for backward compatibility
    if 'model_list' in config:
        for model_config in config['model_list']:
            if 'model_name' in model_config:
                models.append(model_config['model_name'])
    elif 'models' in config:
        models = list(config['models'].keys())

    return models


def get_model_config(config: Dict[str, Any], model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific model.

    Args:
        config: Configuration dictionary
        model_name: Name of the model

    Returns:
        Model configuration dictionary or None if not found
    """
    # Check model_list format
    if 'model_list' in config:
        for model_config in config['model_list']:
            if model_config.get('model_name') == model_name:
                return model_config

    # Check models format
    elif 'models' in config:
        return config['models'].get(model_name)

    return None


def get_provider_for_model(config: Dict[str, Any], model_name: str) -> Optional[str]:
    """
    Get the provider for a specific model.

    Args:
        config: Configuration dictionary
        model_name: Name of the model

    Returns:
        Provider name or None if not found
    """
    model_config = get_model_config(config, model_name)
    if model_config:
        # Try different possible locations for provider info
        if 'litellm_params' in model_config and 'model' in model_config['litellm_params']:
            litellm_model = model_config['litellm_params']['model']
            # Extract provider from litellm model name (e.g., "claude-3-sonnet-20240229" -> "anthropic")
            if '/' in litellm_model:
                return litellm_model.split('/')[0]
            elif litellm_model.startswith(('claude', 'anthropic')):
                return 'anthropic'
            elif litellm_model.startswith(('gpt', 'chatgpt')):
                return 'openai'
            elif litellm_model.startswith(('llama', 'mistral')):
                return 'ollama'
            elif 'deepseek' in litellm_model:
                return 'deepseek'

        if 'provider' in model_config:
            return model_config['provider']

    return None


def get_client_config(config: Dict[str, Any], client_name: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific client.

    Args:
        config: Configuration dictionary
        client_name: Name of the client

    Returns:
        Client configuration dictionary or None if not found
    """
    clients = config.get('clients', {})
    return clients.get(client_name)


def get_all_clients(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get all client configurations.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary of client configurations
    """
    return config.get('clients', {})


def validate_client_config(client_config: Dict[str, Any]) -> None:
    """
    Validate that a client configuration is properly structured.

    Args:
        client_config: Client configuration dictionary

    Raises:
        CLIConfigError: If client configuration is invalid
    """
    if 'bearer_token' not in client_config:
        raise CLIConfigError("Client configuration must include 'bearer_token'")

    if 'allowed_models' not in client_config:
        raise CLIConfigError("Client configuration must include 'allowed_models'")

    allowed_models = client_config['allowed_models']
    if not isinstance(allowed_models, list):
        raise CLIConfigError("Client 'allowed_models' must be a list")

    # Check that allowed_models contains valid values
    for model in allowed_models:
        if not isinstance(model, str):
            raise CLIConfigError("All items in 'allowed_models' must be strings")
        if model != '*' and not model.strip():
            raise CLIConfigError("Model names in 'allowed_models' cannot be empty")


def create_example_config() -> str:
    """
    Create an example configuration string with CLI-specific settings.

    Returns:
        Example configuration as YAML string
    """
    example_config = """
# ChatVault Configuration Example with CLI Support

# Model definitions (existing format)
model_list:
  - model_name: gpt-4
    litellm_params:
      model: gpt-4
      api_key: ${OPENAI_API_KEY}
      max_tokens: 4096
      temperature: 0.7

  - model_name: claude-3-sonnet
    litellm_params:
      model: claude-3-sonnet-20240229
      api_key: ${ANTHROPIC_API_KEY}
      max_tokens: 4096
      temperature: 0.7

  - model_name: llama3-local
    litellm_params:
      model: llama3:8b
      api_base: ${OLLAMA_BASE_URL}
      max_tokens: 4096
      temperature: 0.7

# CLI Client definitions (NEW for CLI usage)
clients:
  mobile1:
    bearer_token: "YOUR_LOCAL1_BEARER_TOKEN"
    allowed_models:
      - "llama3-local"

  full3:
    bearer_token: "YOUR_FULL1_BEARER_TOKEN"
    allowed_models:
      - "*"  # Allow all models

# General settings (existing)
general_settings:
  master_key: ${CHATVAULT_API_KEY}
  database_url: ${DATABASE_URL}
  log_level: INFO
  telemetry: false

# Router settings (existing)
router_settings:
  routing_strategy: "simple"
  fallbacks:
    - gpt-4: ["claude-3-sonnet"]
  rate_limit_per_user:
    requests_per_minute: 60
"""
    return example_config.strip()