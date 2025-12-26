# Project Plan: ChatVault CLI Implementation

**Date:** 2025-12-25 22:15:43
**Estimated Duration:** 4-6 hours
**Complexity:** Medium
**Status:** Approved

## Objective
Transform ChatVault from a FastAPI web application into a command-line tool that can be installed via `pip install -e .` and provides a secure gateway for LLM requests. The CLI tool will support client-based authentication with bearer tokens, model restrictions, and comprehensive logging capabilities.

## Requirements
- [ ] Create command-line script "chatvault" that appears in venv/bin after pip install -e .
- [ ] Implement --help flag that outputs usage information
- [ ] Add README.md with comprehensive documentation on how to run the tool
- [ ] Create configuration file support for defining models and authorized clients
- [ ] Implement bearer token authentication with model restrictions per client
- [ ] Add --verbose flag for full string logging instead of truncated portions
- [ ] Add --logfile flag for JSON format logging to specified file
- [ ] Implement timestamped logging with client, model, and request/response details
- [ ] Ensure logging defaults to stdout when --logfile is not specified

## Implementation Steps
1. **Create packaging configuration (setup.py/pyproject.toml)**
   - Files to create: setup.py or pyproject.toml
   - Files to modify: None
   - Dependencies: setuptools, wheel
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [ ] In Progress / [x] Completed

2. **Create CLI entry point module**
   - Files to create: src/cli.py
   - Files to modify: None
   - Dependencies: click or argparse for CLI parsing
   - Estimated time: 1 hour
   - Status: [ ] Not Started / [ ] In Progress / [x] Completed

3. **Implement configuration file parsing**
   - Files to create: src/cli_config.py
   - Files to modify: config.yaml (extend existing)
   - Dependencies: PyYAML, pydantic for validation
   - Estimated time: 45 minutes
   - Status: [ ] Not Started / [ ] In Progress / [x] Completed

4. **Implement client authentication system**
   - Files to create: src/cli_auth.py
   - Files to modify: None
   - Dependencies: Existing auth.py as reference
   - Estimated time: 45 minutes
   - Status: [ ] Not Started / [ ] In Progress / [x] Completed

5. **Implement logging system**
   - Files to create: src/cli_logging.py
   - Files to modify: None
   - Dependencies: json, logging modules
   - Estimated time: 45 minutes
   - Status: [ ] Not Started / [ ] In Progress / [x] Completed

6. **Create main CLI application logic**
   - Files to modify: src/cli.py
   - Files to create: None
   - Dependencies: All previous CLI modules
   - Estimated time: 1 hour
   - Status: [ ] Not Started / [ ] In Progress / [x] Completed

7. **Create README.md documentation**
   - Files to create: README.md
   - Files to modify: None
   - Dependencies: None
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [ ] In Progress / [x] Completed

8. **Update requirements and test installation**
   - Files to modify: requirements.txt, setup.py/pyproject.toml
   - Files to create: None
   - Dependencies: pip install -e .
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [x] In Progress / [ ] Completed

## Success Criteria
- [ ] `pip install -e .` creates chatvault executable in venv/bin
- [ ] `chatvault --help` displays comprehensive usage information
- [ ] README.md provides clear installation and usage instructions
- [ ] Configuration file properly defines models and client restrictions
- [ ] Bearer token authentication works with model restrictions
- [ ] --verbose flag enables full message logging
- [ ] --logfile flag outputs JSON-formatted logs to specified file
- [ ] Default logging to stdout works correctly
- [ ] Logs include timestamps, client info, model details, and request/response portions

## Testing Strategy
- [ ] Unit tests for CLI argument parsing
- [ ] Unit tests for configuration file parsing
- [ ] Unit tests for client authentication logic
- [ ] Unit tests for logging functionality
- [ ] Integration tests for full CLI workflow
- [ ] Manual testing of pip install -e . and executable creation
- [ ] Manual testing of --help output
- [ ] Manual testing of configuration file loading
- [ ] Manual testing of authentication and model restrictions
- [ ] Manual testing of --verbose and --logfile flags

## Risk Assessment
- **Medium Risk:** Packaging configuration complexity
  - **Mitigation:** Use well-documented setuptools patterns, test installation thoroughly
- **Medium Risk:** CLI argument parsing edge cases
  - **Mitigation:** Comprehensive unit testing of argument combinations
- **Low Risk:** Configuration file format changes
  - **Mitigation:** Extend existing config.yaml format, maintain backward compatibility
- **Low Risk:** Logging format inconsistencies
  - **Mitigation:** Define clear JSON schema for log entries, validate output

## Dependencies
- [ ] click >= 8.0.0 (for CLI framework)
- [ ] PyYAML >= 6.0 (for configuration file parsing)
- [ ] Existing ChatVault dependencies (FastAPI, LiteLLM, etc.)
- [ ] setuptools >= 65.0 (for packaging)
- [ ] wheel >= 0.37.0 (for packaging)

## Database Changes (if applicable)
- [ ] No database schema changes required
- [ ] CLI will reuse existing database functionality for usage logging

## API Changes (if applicable)
- [ ] No API endpoint changes
- [ ] CLI provides command-line interface to existing FastAPI functionality

## Configuration File Requirements
The CLI configuration must support:
- Model definitions with provider mappings
- Client definitions with bearer tokens and allowed model lists
- Example mobile1 client: bearer "YOUR_LOCAL1_BEARER_TOKEN" restricted to "ollama/nemo-8k:latest"
- Example full3 client: bearer "YOUR_FULL1_BEARER_TOKEN" with access to all models

## Logging Requirements
- JSON format with timestamps
- Client identification (bearer token mapping)
- Model and backend details
- Request and response portions (configurable verbosity)
- Clear indication of truncated vs full content

## Notes
This implementation extends the existing FastAPI ChatVault application with a command-line interface. The CLI will provide a secure way to route LLM requests from authorized clients while maintaining comprehensive audit logging. The existing web API functionality will remain unchanged, allowing both CLI and API usage patterns.

Key design decisions:
1. Use setuptools for packaging to ensure cross-platform compatibility
2. Extend existing configuration format rather than creating new files
3. Reuse existing authentication and routing logic where possible
4. Implement logging as a separate concern from the web API logging
5. Maintain separation between CLI and web application code for clean architecture

The CLI will serve as a "Smart Audit" layer that can be deployed on local hardware to provide secure, logged access to multiple LLM providers through a simple command-line interface.