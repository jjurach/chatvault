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
from .cli_config import load_config, get_client_config, get_available_models, get_provider_for_model
from .cli_auth import authenticate_client, validate_model_access
from .cli_logging import setup_logging
from .cli_server import make_chat_request, get_server_url, check_server_health


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
def chat(model: str, messages: List[str], config: str,
         verbose: bool, logfile: Optional[str], stream: bool, temperature: Optional[float],
         max_tokens: Optional[int]):
    """
    Send a chat completion request directly to configured LLM backends.

    This command communicates directly with LLM providers (Ollama, OpenAI, Anthropic, etc.)
    without requiring a ChatVault server to be running. It bypasses client restrictions
    and provides administrative access to all configured models.

    MESSAGES should be provided as alternating role:content pairs, e.g.:
    user "Hello" assistant "Hi there" user "How are you?"

    Examples:
    chatvault chat qwen3-8k user "Hello, how are you?"
    chatvault chat gpt-4 user "Hello, how are you?"
    """
    try:
        import asyncio
        import time

        # Load configuration and initialize settings
        config_data = load_config(config)
        from .config import settings

        if verbose:
            click.echo(f"Communicating directly with LLM backends...", err=True)
        else:
            # Suppress LiteLLM warnings in non-verbose mode
            import logging
            logging.getLogger('litellm').setLevel(logging.ERROR)

        # Parse messages from command line arguments
        parsed_messages = parse_messages(messages)

        # Prepare request parameters
        request_params = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        # Remove None values
        request_params = {k: v for k, v in request_params.items() if v is not None}

        # Initialize LiteLLM router for direct backend communication
        # Force re-initialization with current config
        from . import litellm_router
        litellm_router.router = litellm_router.LiteLLMRouter()
        from .litellm_router import chat_completion, chat_completion_stream

        start_time = time.time()
        client = "cli_direct"

        if stream:
            # Handle streaming response
            click.echo("Streaming response:", err=True)

            async def stream_and_print():
                try:
                    async for chunk in chat_completion_stream(
                        model=model,
                        messages=parsed_messages,
                        user_id=client,
                        **request_params
                    ):
                        # Print streaming chunks
                        if hasattr(chunk, 'choices') and chunk.choices:
                            choice = chunk.choices[0]
                            if hasattr(choice, 'delta') and choice.delta:
                                content = getattr(choice.delta, 'content', '')
                                if content:
                                    click.echo(content, nl=False)
                            elif hasattr(choice, 'text') and choice.text:
                                click.echo(choice.text, nl=False)
                except Exception as e:
                    click.echo(f"\nError during streaming: {e}", err=True)
                    raise

            # Run async streaming
            asyncio.run(stream_and_print())
            click.echo()  # New line after streaming

        else:
            # Handle regular response
            async def get_response():
                try:
                    # Suppress warnings during LLM call
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        response = await chat_completion(
                            model=model,
                            messages=parsed_messages,
                            user_id=client,
                            **request_params
                        )
                    return response
                except Exception as e:
                    raise click.ClickException(f"Chat request failed: {e}")

            # Get the response
            response_data = asyncio.run(get_response())

            # Convert LiteLLM response to dict for JSON serialization
            response_dict = {
                "id": getattr(response_data, 'id', None),
                "object": getattr(response_data, 'object', 'chat.completion'),
                "created": getattr(response_data, 'created', int(time.time())),
                "model": getattr(response_data, 'model', model),
                "choices": [],
                "usage": {}
            }

            # Extract choices
            if hasattr(response_data, 'choices') and response_data.choices:
                for choice in response_data.choices:
                    choice_dict = {
                        "index": getattr(choice, 'index', 0),
                        "message": {
                            "role": "assistant",
                            "content": ""
                        },
                        "finish_reason": getattr(choice, 'finish_reason', None)
                    }

                    # Extract message content
                    if hasattr(choice, 'message') and choice.message:
                        message = choice.message
                        choice_dict["message"]["role"] = getattr(message, 'role', 'assistant')
                        choice_dict["message"]["content"] = getattr(message, 'content', '')

                    response_dict["choices"].append(choice_dict)

            # Extract usage information
            if hasattr(response_data, 'usage') and response_data.usage:
                usage = response_data.usage
                response_dict["usage"] = {
                    "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(usage, 'completion_tokens', 0),
                    "total_tokens": getattr(usage, 'total_tokens', 0)
                }

            # Log the request if requested
            if logfile or verbose:
                request_data = {
                    "model": model,
                    "messages": parsed_messages,
                    "stream": stream,
                    **request_params
                }
                logger = setup_logging(logfile=logfile, verbose=verbose)
                logger.log_request_response(client, model, request_data, response_dict,
                                          verbose=verbose)
                logger.close()

            # Output response in OpenAI format
            click.echo(json.dumps(response_dict, indent=2))

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