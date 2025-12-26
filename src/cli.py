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
from cli_server import make_chat_request, get_server_url, check_server_health


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
@click.option('--server-url', default='http://localhost:4000',
              help='ChatVault server URL (default: http://localhost:4000)')
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
def chat(model: str, messages: List[str], client: str, bearer: str, server_url: str, config: str,
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

        # Check server connectivity first
        is_healthy, health_error = check_server_health(server_url)
        if not is_healthy:
            raise click.ClickException(f"ChatVault server not available: {health_error}")

        # Make the actual request to the ChatVault server
        click.echo(f"Sending request to {server_url}...", err=True)

        response_data, error = make_chat_request(server_url, request_data, bearer)

        if error:
            raise click.ClickException(f"Chat request failed: {error}")

        # Log the request if requested
        if logfile or verbose:
            logger = setup_logging(logfile=logfile, verbose=verbose)
            logger.log_request_response(client, model, request_data, response_data,
                                      verbose=verbose)
            logger.close()

        # Output response
        if stream:
            # For streaming, the response should already be handled by make_chat_request
            # For now, we'll output the response as-is
            click.echo(json.dumps(response_data, indent=2))
        else:
            # Regular response output
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
@click.option('--host', default='localhost',
              help='Server host (default: localhost)')
@click.option('--port', type=int, default=4000,
              help='Server port (default: 4000)')
@click.option('--config', '-f', default='config.yaml',
              help='Path to configuration file (default: config.yaml)')
@click.option('--reload', is_flag=True,
              help='Enable auto-reload for development')
@click.option('--log-level', default='INFO',
              help='Logging level (default: INFO)')
def serve(host: str, port: int, config: str, reload: bool, log_level: str):
    """
    Start the ChatVault server.

    Launches the FastAPI server with OpenAI-compatible endpoints for LLM processing.
    All requests are authenticated and logged according to the configuration.
    """
    try:
        import os
        import sys

        # Set environment variables for configuration
        os.environ['SERVER_HOST'] = host
        os.environ['SERVER_PORT'] = str(port)
        os.environ['LOG_LEVEL'] = log_level

        # Import and configure settings
        from .config import settings
        settings.host = host
        settings.port = port
        settings.debug = reload

        click.echo(f"Starting ChatVault server on {host}:{port}")
        if reload:
            click.echo("Development mode enabled (auto-reload)")
        click.echo("Press Ctrl+C to stop the server")
        click.echo()

        # Import and start the server
        from .main import main as server_main
        server_main()

    except KeyboardInterrupt:
        click.echo("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
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