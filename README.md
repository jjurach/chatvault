# ChatVault CLI

A secure command-line interface for ChatVault, providing authenticated access to Large Language Models with comprehensive audit logging.

## Overview

ChatVault CLI is a command-line tool that serves as a "Smart Audit" layer for LLM requests. It provides secure, client-based authentication with bearer tokens and model access restrictions, ensuring all requests are properly logged with timestamps, client identification, and request/response details.

## Features

- **Secure Authentication**: Bearer token-based client authentication with model restrictions
- **Comprehensive Logging**: JSON-formatted logs with configurable verbosity
- **Model Access Control**: Per-client model restrictions for security
- **Multiple Output Formats**: Support for both regular and streaming responses
- **Flexible Configuration**: YAML-based configuration for models and clients
- **Cross-Platform**: Works on Linux, macOS, and Windows

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Access to LLM providers (OpenAI, Anthropic, etc.) or local Ollama instance

### Install from Source

1. Clone the repository:
```bash
git clone <repository-url>
cd chatvault
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e .
```

4. Verify installation:
```bash
chatvault --version
```

The `chatvault` command should now be available in your PATH.

## Quick Start

1. **Configure ChatVault**:
   Edit `config.yaml` to define your models and clients.

2. **Test the CLI**:
```bash
# Check available commands
chatvault --help

# List configured models
chatvault list-models

# List configured clients
chatvault list-clients
```

3. **Make a chat request**:
```bash
chatvault chat gpt-4 user "Hello, how are you?" --client mobile1 --bearer <your-token>
```

## Configuration

ChatVault CLI uses a YAML configuration file (default: `config.yaml`) to define models and client access controls.

### Configuration File Structure

```yaml
# Model definitions (existing ChatVault format)
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

  - model_name: local-llama
    litellm_params:
      model: llama3:8b
      api_base: ${OLLAMA_BASE_URL}
      max_tokens: 4096
      temperature: 0.7

# CLI Client definitions
clients:
  mobile1:
    bearer_token: "YOUR_LOCAL1_BEARER_TOKEN"
    allowed_models:
      - "local-llama"  # Restricted to local models only

  fullaccess:
    bearer_token: "YOUR_FULL1_BEARER_TOKEN"
    allowed_models:
      - "*"  # Allow all configured models

# General settings (existing ChatVault format)
general_settings:
  master_key: ${CHATVAULT_API_KEY}
  database_url: ${DATABASE_URL}
  log_level: INFO
```

### Environment Variables

Set these environment variables for API keys and configuration:

```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export DEEPSEEK_API_KEY="your-deepseek-key"
export OLLAMA_BASE_URL="http://localhost:11434"
export DATABASE_URL="sqlite:///chatvault.db"
export CHATVAULT_API_KEY="your-master-key"
```

## Usage

### Basic Chat Command

Send a chat completion request:

```bash
chatvault chat <model> <messages> --client <client-id> --bearer <token>
```

**Arguments:**
- `model`: Model name (must be configured and allowed for the client)
- `messages`: Message pairs in format `role "content"` (see examples below)

**Options:**
- `--client, -c`: Client identifier (required)
- `--bearer, -b`: Bearer token for authentication (required)
- `--config, -f`: Path to config file (default: config.yaml)
- `--verbose, -v`: Enable verbose logging (full content instead of truncated)
- `--logfile, -l`: Path to JSON log file (default: stdout)
- `--stream`: Enable streaming response mode
- `--temperature`: Temperature parameter (0.0-1.0)
- `--max-tokens`: Maximum tokens in response

### Message Format

Messages are specified as alternating role/content pairs:

```bash
# Single message
chatvault chat gpt-4 user "Hello, how are you?" --client mobile1 --bearer <token>

# Multiple messages (conversation)
chatvault chat gpt-4 \
  system "You are a helpful assistant." \
  user "What is Python?" \
  assistant "Python is a programming language." \
  user "Tell me more about it." \
  --client fullaccess --bearer <token>
```

**Supported roles:** `system`, `user`, `assistant`

### Examples

#### Basic Chat Request
```bash
chatvault chat gpt-4 user "Explain quantum computing in simple terms" \
  --client fullaccess \
  --bearer YOUR_FULL1_BEARER_TOKEN
```

#### Streaming Response
```bash
chatvault chat claude-3-sonnet user "Write a short story about AI" \
  --client fullaccess \
  --bearer YOUR_FULL1_BEARER_TOKEN \
  --stream
```

#### Local Model with Restricted Client
```bash
chatvault chat local-llama user "What is the capital of France?" \
  --client mobile1 \
  --bearer YOUR_LOCAL1_BEARER_TOKEN
```

#### With Custom Parameters
```bash
chatvault chat gpt-4 user "Write a creative poem" \
  --client fullaccess \
  --bearer YOUR_FULL1_BEARER_TOKEN \
  --temperature 0.9 \
  --max-tokens 200
```

### Logging Examples

#### Log to File with Verbose Output
```bash
chatvault chat gpt-4 user "Hello" \
  --client fullaccess \
  --bearer <token> \
  --verbose \
  --logfile chat.log
```

#### Default Logging (to stdout)
```bash
chatvault chat gpt-4 user "Hello" \
  --client fullaccess \
  --bearer <token>
```

### Configuration Management

#### List Available Models
```bash
chatvault list-models
```

Output:
```
Available models:
  gpt-4 (provider: openai)
  claude-3-sonnet (provider: anthropic)
  local-llama (provider: ollama)
```

#### List Configured Clients
```bash
chatvault list-clients
```

Output:
```
Configured clients:
  mobile1: models: local-llama
  fullaccess: all models
```

## Logging

ChatVault CLI provides comprehensive JSON-formatted logging with the following features:

### Log Format

All logs are output in JSON format with these common fields:
- `timestamp`: ISO 8601 timestamp (UTC)
- `event_type`: Type of log event (`request`, `response`, `error`, `info`)
- `client`: Client identifier
- `model`: Model name (when applicable)
- `version`: Log format version

### Verbose vs Truncated Logging

- **Default (truncated)**: Messages longer than limits are truncated with "..."
- **Verbose (`--verbose`)**: Full message content is logged

### Log Destinations

- **Default**: Logs to stdout (console)
- **File logging**: Use `--logfile path/to/log.jsonl` for file output

### Example Log Entries

#### Request Log (truncated)
```json
{
  "timestamp": "2025-12-25T22:15:43.123456Z",
  "event_type": "request_response",
  "client": "mobile1",
  "model": "gpt-4",
  "request": {
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Hello, how are you?..."}
    ],
    "stream": false
  },
  "response": {
    "id": "chatcmpl-abc123",
    "choices": [
      {
        "message": {
          "content": "I'm doing well, thank you for asking..."
        }
      }
    ]
  },
  "truncated": true,
  "success": true
}
```

#### Error Log
```json
{
  "timestamp": "2025-12-25T22:15:44.123456Z",
  "event_type": "error",
  "client": "mobile1",
  "error": "Client 'mobile1' is not authorized to access model 'gpt-4'",
  "success": false
}
```

## Security

### Authentication
- Bearer token authentication with constant-time comparison
- No token values are logged (only client identifiers)
- Tokens should be at least 32 characters long

### Access Control
- Per-client model restrictions
- Support for wildcard (`*`) access to all models
- Granular permission system

### Best Practices
- Use strong, random bearer tokens
- Rotate tokens regularly
- Store tokens securely (environment variables, not in files)
- Use HTTPS for token transmission when possible
- Regularly audit access logs

## Troubleshooting

### Common Issues

#### "Unknown client" Error
- Verify client name matches configuration
- Check config file path with `--config`

#### "Invalid bearer token" Error
- Verify token matches exactly (case-sensitive)
- Check for extra whitespace or special characters

#### "Not authorized to access model" Error
- Check client's `allowed_models` in configuration
- Verify model name is spelled correctly

#### "Configuration file not found" Error
- Ensure config.yaml exists in current directory
- Use `--config` to specify correct path

#### "No models configured" Error
- Check model_list section in config.yaml
- Verify environment variables for API keys are set

### Debug Mode

Enable verbose logging to see full request/response content:

```bash
chatvault chat gpt-4 user "Test" --client mobile1 --bearer <token> --verbose
```

### Log Analysis

Search logs for specific events:

```bash
# Find all errors
grep '"event_type": "error"' chat.log

# Find requests from specific client
grep '"client": "mobile1"' chat.log

# Count requests per client
grep '"event_type": "request_response"' chat.log | grep -o '"client": "[^"]*"' | sort | uniq -c
```

## Development

### Project Structure

```
chatvault/
├── src/
│   ├── cli.py              # Main CLI entry point
│   ├── cli_config.py       # Configuration file parsing
│   ├── cli_auth.py         # Client authentication
│   ├── cli_logging.py      # JSON logging system
│   ├── main.py            # FastAPI web application
│   └── ...                # Other ChatVault modules
├── config.yaml            # Configuration file
├── setup.py              # Packaging configuration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

### Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation for API changes
4. Use type hints and comprehensive error handling

### Testing

Run the test suite:

```bash
pip install -e .[test]
pytest tests/
```

## License

[Specify your license here]

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the configuration examples
- Examine log files for detailed error information
- Create an issue in the project repository

## Changelog

### Version 1.0.0
- Initial release of ChatVault CLI
- Bearer token authentication
- Model access restrictions
- JSON logging with configurable verbosity
- Support for streaming and regular responses
- Cross-platform command-line interface