# Project Plan: ChatVault Initial Implementation

**Date:** 2025-12-24 19:19:12
**Estimated Duration:** 2-3 weeks
**Complexity:** High
**Status:** Approved

## Objective
Build ChatVault, a FastAPI-based "Smart Audit" layer that serves as a secure gateway for local and commercial Large Language Models (LLMs). The system will centralize API key management and usage tracking on local hardware while providing authenticated access to external devices through a single OpenAI-compatible endpoint.

## Requirements
- [ ] FastAPI web server with OpenAI-compatible `/v1/chat/completions` endpoint
- [ ] LiteLLM integration for routing requests between Ollama, Anthropic, and DeepSeek
- [ ] SQLite database for permanent token and cost logging (timestamp, user_id, model_name, input_tokens, output_tokens, calculated_cost)
- [ ] Bearer token authentication system
- [ ] Streaming response handling with usage metadata capture
- [ ] Demo script for testing functionality with local Ollama instance
- [ ] Comprehensive pytest test suite integrated throughout development
- [ ] Reverse SSH tunnel setup for EC2 access
- [ ] Configuration management (config.yaml for LiteLLM, .env for API keys)
- [ ] Comprehensive documentation suite

## Implementation Steps
1. **Step 1:** Project Structure Setup - Create Python project structure, requirements.txt, and basic configuration files
   - Files to modify: requirements.txt, config.yaml, .env.example, main.py
   - Files to create: requirements.txt, config.yaml, .env.example, tests/
   - Dependencies: fastapi, uvicorn, litellm, sqlalchemy, httpx, python-dotenv, pytest, pytest-asyncio
   - Estimated time: 2 hours
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

2. **Step 2:** Demo Script Creation - Create a simple demo script that connects to local Ollama instance to validate basic functionality
   - Files to create: demo.py, tests/test_demo.py
   - Dependencies: requests, ollama (if available locally)
   - Estimated time: 2 hours
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

3. **Step 3:** Database Schema and Models - Implement SQLite database with SQLAlchemy for usage tracking
   - Files to modify: models.py, database.py
   - Files to create: models.py, database.py, tests/test_database.py
   - Dependencies: SQLAlchemy, pytest
   - Estimated time: 3 hours
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

4. **Step 4:** Authentication System - Implement Bearer token validation
   - Files to modify: auth.py
   - Files to create: auth.py, tests/test_auth.py
   - Dependencies: fastapi, pytest
   - Estimated time: 2 hours
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

5. **Step 5:** LiteLLM Configuration and Routing - Set up model routing configuration
   - Files to modify: config.yaml
   - Files to create: tests/test_litellm_config.py
   - Dependencies: litellm, pytest
   - Estimated time: 2 hours
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

6. **Step 6:** Main FastAPI Application - Create core application with chat completions endpoint
   - Files to modify: main.py
   - Files to create: tests/test_main.py
   - Dependencies: fastapi, litellm, pytest
   - Estimated time: 4 hours
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

7. **Step 7:** Streaming Response Handler - Implement async streaming with usage capture
   - Files to modify: streaming_handler.py
   - Files to create: streaming_handler.py, tests/test_streaming.py
   - Dependencies: fastapi, litellm, pytest
   - Estimated time: 4 hours
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

8. **Step 8:** Usage Logging Integration - Connect database logging to request processing
   - Files to modify: main.py, database.py
   - Files to create: tests/test_usage_logging.py
   - Dependencies: sqlalchemy, pytest
   - Estimated time: 2 hours
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

9. **Step 9:** Configuration and Environment Setup - Complete configuration files
   - Files to modify: .env, config.yaml
   - Files to create: tests/test_config.py
   - Estimated time: 1 hour
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

10. **Step 10:** Integration Testing and Demo Validation - Run comprehensive tests and validate demo script with Ollama
    - Files to modify: demo.py, tests/
    - Dependencies: pytest, ollama
    - Estimated time: 3 hours
    - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

11. **Step 11:** SSH Tunnel Documentation - Document reverse tunnel setup
    - Files to modify: doc/DEPLOYMENT.md
    - Files to create: doc/DEPLOYMENT.md
    - Estimated time: 1 hour
    - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

## Success Criteria
- [ ] FastAPI application starts successfully on localhost:4000
- [ ] Bearer token authentication properly validates requests
- [ ] Requests are correctly routed to Ollama, Anthropic, and DeepSeek providers
- [ ] Usage data (tokens, costs) is accurately logged to SQLite database
- [ ] Streaming responses work with complete usage metadata capture
- [ ] Demo script successfully connects to local Ollama and demonstrates basic chat functionality
- [ ] Comprehensive pytest test suite covers all major components with >80% coverage
- [ ] SSH reverse tunnel successfully forwards traffic from EC2 to Local01
- [ ] All configuration files are properly set up and documented
- [ ] Basic OpenAI-compatible API testing passes

## Testing Strategy
- [ ] Unit tests for authentication, database operations, and routing logic (pytest)
- [ ] Integration tests with mock LLM providers to avoid API costs
- [ ] Demo script testing with local Ollama instance for real functionality validation
- [ ] Manual testing with real API calls (limited scope, monitor costs)
- [ ] Streaming response testing with various model providers
- [ ] Performance testing for concurrent requests and response times
- [ ] Security testing for authentication bypass attempts
- [ ] pytest fixtures for common test data and mock services

## Risk Assessment
- **High Risk:** API key security and exposure - **Mitigation:** Use .env files, never commit secrets, validate all configurations before deployment
- **High Risk:** Streaming response complexity and metadata capture - **Mitigation:** Thorough testing with all providers, implement fallback error handling
- **Medium Risk:** Database performance with high request volume - **Mitigation:** SQLite suitable for target use case, monitor and optimize queries if needed
- **Medium Risk:** Network connectivity issues between EC2 and Local01 - **Mitigation:** Document tunnel setup clearly, include monitoring and reconnection procedures
- **Medium Risk:** Demo script reliability with Ollama connectivity - **Mitigation:** Include fallback modes and clear error messages, document setup requirements
- **Low Risk:** Dependency conflicts between LiteLLM and other libraries - **Mitigation:** Pin specific versions in requirements.txt, test thoroughly

## Dependencies
- [ ] fastapi >= 0.104.0
- [ ] uvicorn[standard] >= 0.24.0
- [ ] litellm >= 1.35.0
- [ ] sqlalchemy >= 2.0.0
- [ ] httpx >= 0.25.0
- [ ] python-dotenv >= 1.0.0
- [ ] pydantic >= 2.5.0
- [ ] python-multipart >= 0.0.6
- [ ] pytest >= 7.4.0
- [ ] pytest-asyncio >= 0.21.0
- [ ] pytest-cov >= 4.1.0
- [ ] requests >= 2.31.0

## Database Changes (if applicable)
- [ ] New SQLite database file: chatvault.db
- [ ] New table: usage_logs
  - id: INTEGER PRIMARY KEY
  - timestamp: DATETIME
  - user_id: VARCHAR(255)
  - model_name: VARCHAR(255)
  - input_tokens: INTEGER
  - output_tokens: INTEGER
  - cost: DECIMAL(10,6)

## API Changes (if applicable)
- [ ] New endpoint: POST /v1/chat/completions
  - Request format: OpenAI-compatible chat completion request
  - Response format: OpenAI-compatible streaming/non-streaming response
  - Authentication: Bearer token required in Authorization header
  - Streaming support: Server-sent events for real-time responses

## Demo Script Requirements
- [ ] Connect to local Ollama instance (default localhost:11434)
- [ ] Send simple chat completion request to demonstrate routing
- [ ] Display response and usage metadata
- [ ] Include error handling for connection issues
- [ ] Support both streaming and non-streaming modes
- [ ] Validate authentication and logging functionality

## Notes
- Architecture documentation already exists in `doc/ARCHITECTURE.md` and covers hardware, network, and component details
- This implementation focuses on single-user design as specified
- SSH tunnel setup requires manual configuration on both Local01 and EC2 instances
- API keys for commercial providers must be obtained and configured securely
- Ollama should be pre-installed and running on Local01 for local LLM support
- Demo script will serve as early validation tool and integration test
- pytest will be integrated throughout development with test files created alongside implementation
- Project structure should follow Python best practices with clear separation of concerns