"""
ChatVault CLI - Command-line interface for ChatVault LLM proxy

Provides a secure command-line gateway for LLM requests with client-based
authentication, model restrictions, and comprehensive logging.
"""

import json
import sys
from typing import Optional, Dict, Any, List
import click

# Import CLI modules
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from cli_config import load_config, get_client_config, get_available_models, get_provider_for_model
from cli_auth import authenticate_client, validate_model_access
from cli_logging import setup_logging


@click.group()
@click.version_option(version="1.0.0", prog_name="chatvault")
def cli():
    """
    ChatVault - Secure LLM proxy with usage tracking and client authentication

    ChatVault provides a command-line interface for routing LLM requests through
    authorized clients with bearer token authentication and model restrictions.
    All requests are logged with timestamps, client information, and request/response details.
    """
    pass


@cli.command()
@click.argument('model')
@click.argument('messages', nargs=-1, required=True)
@click.option('--client', '-c', required=True,
              help='Client identifier (must match configuration)')
@click.option('--bearer', '-b', required=True,
              help='Bearer token for client authentication')
@click.option('--config', '-f', default='config.yaml',
              help='Path to configuration file (default: config.yaml)')
@click.option('--verbose', '-v', is_flag=True,
              help='Log full request/response content instead of truncated portions')
@click.option('--logfile', '-l',
              help='Path to JSON log file (default: stdout)')
@click.option('--stream', is_flag=True,
              help='Enable streaming response mode')
@click.option('--temperature', type=float,
              help='Temperature parameter for LLM request')
@click.option('--max-tokens', type=int,
              help='Maximum tokens for response')
def chat(model: str, messages: List[str], client: str, bearer: str, config: str,
         verbose: bool, logfile: Optional[str], stream: bool, temperature: Optional[float],
         max_tokens: Optional[int]):
    """
    Send a chat completion request through ChatVault.

    MESSAGES should be provided as alternating role:content pairs, e.g.:
    user "Hello" assistant "Hi there" user "How are you?"

    Example:
    chatvault chat gpt-4 user "Hello, how are you?" --client mobile1 --bearer <token>
    """
    try:
        # Load configuration
        config_data = load_config(config)

        # Authenticate client
        client_config = authenticate_client(client, bearer, config_data)

        # Validate model access
        validate_model_access(client_config, model)

        # Parse messages from command line arguments
        parsed_messages = parse_messages(messages)

        # Prepare request data
        request_data = {
            "model": model,
            "messages": parsed_messages,
            "stream": stream
        }

        # Add optional parameters
        if temperature is not None:
            request_data["temperature"] = temperature
        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens

        # Here we would integrate with the existing ChatVault routing logic
        # For now, we'll create a placeholder response
        response_data = {
            "id": f"chatcmpl-{client}-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a placeholder response. CLI integration pending."
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(str(parsed_messages)),
                "completion_tokens": 10,
                "total_tokens": len(str(parsed_messages)) + 10
            }
        }

        # Output response
        if stream:
            # Streaming output (placeholder)
            click.echo("data: " + json.dumps(response_data))
            click.echo("data: [DONE]")
        else:
            # Regular output
            click.echo(json.dumps(response_data, indent=2))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-f', default='config.yaml',
              help='Path to configuration file (default: config.yaml)')
def list_models(config: str):
    """
    List available models from configuration.
    """
    try:
        config_data = load_config(config)
        model_names = get_available_models(config_data)

        if not model_names:
            click.echo("No models configured.")
            return

        click.echo("Available models:")
        for model_name in model_names:
            provider = get_provider_for_model(config_data, model_name)
            click.echo(f"  {model_name} (provider: {provider})")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-f', default='config.yaml',
              help='Path to configuration file (default: config.yaml)')
def list_clients(config: str):
    """
    List configured clients and their restrictions.
    """
    try:
        config_data = load_config(config)
        clients = config_data.get('clients', {})

        if not clients:
            click.echo("No clients configured.")
            return

        click.echo("Configured clients:")
        for client_name, client_config in clients.items():
            allowed_models = client_config.get('allowed_models', [])
            if allowed_models == ['*']:
                model_info = "all models"
            else:
                model_info = f"models: {', '.join(allowed_models)}"
            click.echo(f"  {client_name}: {model_info}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def parse_messages(messages: List[str]) -> List[Dict[str, str]]:
    """
    Parse command-line message arguments into OpenAI message format.

    Expects alternating role:content pairs.
    """
    if len(messages) % 2 != 0:
        raise click.BadParameter("Messages must be provided as role:content pairs")

    parsed_messages = []
    for i in range(0, len(messages), 2):
        role = messages[i]
        content = messages[i + 1]

        if role not in ['system', 'user', 'assistant']:
            raise click.BadParameter(f"Invalid role '{role}'. Must be system, user, or assistant")

        parsed_messages.append({
            "role": role,
            "content": content
        })

    return parsed_messages


def main():
    """
    Main entry point for the CLI application.
    """
    cli()


if __name__ == '__main__':
    main()