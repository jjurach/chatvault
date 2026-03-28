# Project Plan: CLI Server Integration and End-to-End Demo

**Date:** 2025-12-25 23:18:00
**Estimated Duration:** 2-3 hours
**Complexity:** Medium
**Status:** Approved

## Objective
Integrate the ChatVault CLI with the FastAPI server to enable end-to-end LLM processing, and demonstrate cv-tester validating authenticated requests through ChatVault to the user's Qwen3-8k Ollama model. By completion, users should be able to start ChatVault server via CLI and process authenticated LLM requests through it.

## Current State Analysis
- **FastAPI Server**: Complete with OpenAI-compatible endpoints and LiteLLM integration
- **CLI**: Has authentication and validation but returns placeholder responses
- **Configuration**: Has Ollama models but needs Qwen3-8k specifically
- **cv-tester**: Ready to validate the integration

## Requirements
- [ ] Add `serve` command to CLI for starting ChatVault server
- [ ] Update CLI `chat` command to make HTTP requests to running server
- [ ] Add Qwen3-8k model configuration to config.yaml
- [ ] Ensure proper error handling for server connectivity
- [ ] Demonstrate end-to-end functionality with cv-tester
- [ ] Update CLI to support server URL configuration

## Implementation Steps

1. **Add Qwen3-8k model configuration**
   - Files to modify: `config.yaml`
   - Add model entry for `qwen3-8k` with Ollama integration
   - Update client configurations to include the new model
   - Estimated time: 15 minutes
   - Status: ✅ Completed

2. **Add serve command to CLI**
   - Files to modify: `src/cli.py`
   - Add new `serve` subcommand that starts the FastAPI server
   - Include options for host, port, and configuration
   - Handle graceful shutdown and error conditions
   - Estimated time: 45 minutes
   - Status: ✅ Completed

3. **Update CLI chat command for server integration**
   - Files to modify: `src/cli.py`
   - Replace placeholder response with actual HTTP request to server
   - Add server URL configuration option
   - Implement proper error handling for connection failures
   - Maintain existing authentication and validation logic
   - Estimated time: 45 minutes
   - Status: ✅ Completed
   - Status: ✅ Completed

4. **Add server connectivity utilities**
   - Files to create: `src/cli_server.py`
   - Add functions to check server health and availability
   - Implement server startup detection and wait logic
   - Add timeout handling for server operations
   - Estimated time: 30 minutes

5. **Update CLI configuration handling**
   - Files to modify: `src/cli_config.py`
   - Add server URL and port configuration options
   - Support for overriding server connection details
   - Backward compatibility with existing configurations
   - Estimated time: 20 minutes

6. **Integration testing and demonstration**
   - Start ChatVault server via CLI
   - Test CLI chat command with real server requests
   - Run cv-tester against running server to validate functionality
   - Verify Qwen3-8k model integration
   - Estimated time: 30 minutes

## Configuration Updates Required

### New Model Configuration (config.yaml)
```yaml
- model_name: qwen3-8k
  litellm_params:
    model: qwen3:8k  # User's specific Ollama model
    api_base: ${OLLAMA_BASE_URL}
    api_key: null
    max_tokens: 8192
    temperature: 0.7
```

### CLI Configuration Extensions
```yaml
# Add to general_settings
server:
  host: ${SERVER_HOST:-localhost}
  port: ${SERVER_PORT:-4000}
  auto_start: false  # Whether CLI should start server automatically
```

## Command-Line Interface Updates

### New serve Command
```bash
chatvault serve [OPTIONS]

Options:
  --host TEXT         Server host (default: localhost)
  --port INTEGER      Server port (default: 4000)
  --config FILE       Configuration file
  --reload            Enable auto-reload for development
  --log-level TEXT    Logging level
```

### Updated chat Command
```bash
chatvault chat <model> <messages> [OPTIONS]

New Options:
  --server-url URL    ChatVault server URL (default: http://localhost:4000)
  --auto-start        Automatically start server if not running
```

## Testing Strategy
- [ ] Unit tests for new CLI server utilities
- [ ] Integration tests for CLI-to-server communication
- [ ] End-to-end tests with cv-tester validation
- [ ] Error condition testing (server not running, invalid URLs, etc.)

## Risk Assessment
- **Medium Risk:** Server startup integration
  - **Mitigation:** Comprehensive error handling and health checks
- **Low Risk:** Model configuration changes
  - **Mitigation:** Validate configuration before applying
- **Low Risk:** Backward compatibility
  - **Mitigation:** Maintain existing CLI behavior by default

## Dependencies
- [ ] requests >= 2.31.0 (for CLI-to-server HTTP communication)
- [ ] httpx (already in requirements for FastAPI)
- [ ] Existing FastAPI and uvicorn dependencies

## Success Criteria
- [ ] `chatvault serve` starts ChatVault server successfully
- [ ] `chatvault chat` makes real HTTP requests to server instead of placeholders
- [ ] Qwen3-8k model is properly configured and accessible
- [ ] cv-tester can successfully run authenticated requests through ChatVault
- [ ] CLI provides clear error messages for connection failures
- [ ] All existing CLI functionality remains intact

## Demonstration Flow
1. Start Ollama with Qwen3-8k model
2. Run `chatvault serve` to start ChatVault server
3. Use `chatvault chat qwen3-8k user "Hello" --client full3 --bearer <token>` for real LLM response
4. Run `cv-tester all` to validate full integration
5. Verify authenticated requests work end-to-end

## Notes
This integration bridges the gap between the existing FastAPI server implementation and the CLI interface. The goal is to provide a seamless experience where users can start the server and immediately begin processing LLM requests through authenticated channels, with full validation via cv-tester.

The implementation should maintain backward compatibility while adding the new server integration capabilities. All changes should follow existing code patterns and include comprehensive error handling.