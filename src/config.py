"""
Configuration management for ChatVault.

This module handles loading and validation of configuration from environment variables
and configuration files (YAML, .env).
"""

import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic import field_validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings using Pydantic for validation and type conversion.

    Loads configuration from environment variables with optional .env file support.
    """

    # Server Configuration
    host: str = Field(default="localhost", env="HOST")
    port: int = Field(default=4000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Database Configuration
    database_url: str = Field(default="sqlite:///./chatvault.db", env="DATABASE_URL")
    echo_sql: bool = Field(default=False, env="ECHO_SQL")

    # Authentication Configuration
    chatvault_api_key: str = Field(..., env="CHATVAULT_API_KEY")
    auth_required: bool = Field(default=True, env="AUTH_REQUIRED")

    # LLM Provider API Keys
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_timeout: int = Field(default=120, env="OLLAMA_TIMEOUT")

    # LiteLLM Configuration
    litellm_config_path: str = Field(default="config.yaml", env="LITELLM_CONFIG_PATH")
    litellm_model_list: List[Dict[str, Any]] = Field(default_factory=list)

    # Usage Tracking Configuration
    enable_usage_logging: bool = Field(default=True, env="ENABLE_USAGE_LOGGING")
    enable_cost_calculation: bool = Field(default=True, env="ENABLE_COST_CALCULATION")

    # Security Configuration
    cors_origins_str: str = Field(default="*", env="CORS_ORIGINS")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")

    # Performance Configuration
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=300, env="REQUEST_TIMEOUT")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is a valid logging level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()

    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        """Validate port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535')
        return v

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from string to list."""
        return [origin.strip() for origin in self.cors_origins_str.split(',') if origin.strip()]

    def get_litellm_config(self) -> Dict[str, Any]:
        """
        Load LiteLLM configuration from YAML file.

        Returns:
            Dict containing LiteLLM configuration
        """
        config_path = Path(self.litellm_config_path)

        if not config_path.exists():
            logger.warning(f"LiteLLM config file not found: {config_path}")
            return {"model_list": []}

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}

            # Substitute environment variables in config
            config = self._substitute_env_vars(config)

            logger.info(f"Loaded LiteLLM config with {len(config.get('model_list', []))} models")
            return config

        except Exception as e:
            logger.error(f"Failed to load LiteLLM config: {e}")
            return {"model_list": []}

    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively substitute environment variables in configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with environment variables substituted
        """
        if isinstance(config, dict):
            result = {}
            for key, value in config.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract environment variable name
                    env_var = value[2:-1]
                    result[key] = os.getenv(env_var, value)
                else:
                    result[key] = self._substitute_env_vars(value)
            return result
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        else:
            return config

    def get_available_models(self) -> List[str]:
        """
        Get list of available model names from LiteLLM configuration.

        Returns:
            List of model names
        """
        config = self.get_litellm_config()
        model_list = config.get('model_list', [])

        return [model.get('model_name', '') for model in model_list if model.get('model_name')]

    def validate_api_keys(self) -> Dict[str, bool]:
        """
        Validate that required API keys are present.

        Returns:
            Dict mapping provider names to availability status
        """
        key_status = {
            'anthropic': bool(self.anthropic_api_key),
            'deepseek': bool(self.deepseek_api_key),
            'openai': bool(self.openai_api_key),
            'ollama': True,  # Ollama doesn't require API key
        }

        missing_keys = [provider for provider, available in key_status.items() if not available]
        if missing_keys:
            logger.warning(f"Missing API keys for providers: {missing_keys}")

        return key_status

    def get_provider_for_model(self, model_name: str) -> Optional[str]:
        """
        Get the provider name for a given model.

        Args:
            model_name: Name of the model

        Returns:
            Provider name or None if not found
        """
        config = self.get_litellm_config()

        for model_config in config.get('model_list', []):
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
                elif ':' in model:  # Ollama models have format "name:tag"
                    return 'ollama'

        return None


# Global settings instance
settings = Settings()

# Validate configuration on import
def validate_configuration():
    """Validate configuration and log warnings for missing components."""
    logger.info("Validating ChatVault configuration...")

    # Check API keys
    key_status = settings.validate_api_keys()
    available_providers = [p for p, available in key_status.items() if available]

    if not available_providers:
        logger.warning("No LLM providers configured - ChatVault will not function!")
    else:
        logger.info(f"Available providers: {available_providers}")

    # Check LiteLLM config
    models = settings.get_available_models()
    if not models:
        logger.warning("No models configured in LiteLLM config")
    else:
        logger.info(f"Configured models: {models}")

    # Check database
    from .database import check_db_connection
    if not check_db_connection():
        logger.error("Database connection failed!")
    else:
        logger.info("Database connection successful")

    logger.info("Configuration validation complete")


# Initialize validation on import
if __name__ != "__main__":
    validate_configuration()