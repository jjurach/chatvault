# Project Plan: CV-Tester Testing Tool

**Date:** 2025-12-25 22:56:32
**Estimated Duration:** 2-3 hours
**Complexity:** Low
**Status:** Draft

## Objective
Create a testing tool called "cv-tester" that connects to a running ChatVault instance, authenticates with OpenAI-compatible authorization tokens, and executes predefined LLM chat requests to validate ChatVault functionality. This tool will serve as a reliable way to test ChatVault features during development and deployment.

## Requirements
- [ ] Create cv-tester Python script that connects to running ChatVault port
- [ ] Implement OpenAI-compatible authentication using bearer tokens
- [ ] Include hard-coded test requests with short expected responses
- [ ] Support multiple test scenarios (basic chat, model restrictions, error handling)
- [ ] Provide clear pass/fail output for each test
- [ ] Include configuration for target ChatVault instance
- [ ] Add command-line options for test selection and verbosity
- [ ] Generate summary report of test results

## Current State Analysis
ChatVault CLI has been implemented with authentication and basic functionality. A dedicated testing tool is needed to validate the CLI works correctly with real requests and responses.

## Implementation Steps
1. **Create basic cv-tester script structure**
   - Files to create: `cv_tester.py`
   - Files to modify: None
   - Dependencies: requests, argparse
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

2. **Implement ChatVault connection and authentication**
   - Files to modify: `cv_tester.py`
   - Files to create: None
   - Dependencies: httpx or requests for HTTP client
   - Estimated time: 45 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

3. **Add hard-coded test requests and expected responses**
   - Files to modify: `cv_tester.py`
   - Files to create: None
   - Dependencies: JSON test data structures
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

4. **Implement test execution and validation logic**
   - Files to modify: `cv_tester.py`
   - Files to create: None
   - Dependencies: Response parsing and comparison logic
   - Estimated time: 45 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

5. **Add command-line interface and configuration**
   - Files to modify: `cv_tester.py`
   - Files to create: None
   - Dependencies: argparse for CLI parsing
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

6. **Create test scenarios and update documentation**
   - Files to modify: `README.md` (add testing section)
   - Files to create: `tests/test_cv_tester.py`
   - Dependencies: pytest for unit tests
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

## Test Scenarios Design

### Basic Connectivity Test
- **Purpose**: Verify ChatVault is running and accepting connections
- **Request**: Simple ping/health check
- **Expected**: HTTP 200 response with ChatVault identification

### Authentication Test
- **Purpose**: Test bearer token authentication
- **Request**: Valid chat request with correct token
- **Expected**: Successful response with chat completion

### Model Access Test
- **Purpose**: Test model-specific access restrictions
- **Request**: Request to restricted model with appropriate token
- **Expected**: Successful response for authorized access

### Error Handling Test
- **Purpose**: Test error responses for invalid requests
- **Request**: Invalid model, wrong token, malformed request
- **Expected**: Appropriate HTTP error codes and error messages

### Streaming Response Test
- **Purpose**: Test streaming functionality
- **Request**: Chat request with stream=true
- **Expected**: Server-sent events format response

## Configuration Structure

```python
# cv_tester.py configuration
DEFAULT_CONFIG = {
    'chatvault_url': 'http://localhost:4000',
    'timeout': 30,
    'test_clients': {
        'mobile1': {
            'token': 'YOUR_LOCAL1_BEARER_TOKEN',
            'allowed_models': ['vault-local']
        },
        'full3': {
            'token': 'YOUR_FULL1_BEARER_TOKEN',
            'allowed_models': ['*']  # All models
        }
    },
    'test_requests': [
        {
            'name': 'basic_chat',
            'model': 'vault-local',
            'client': 'mobile1',
            'messages': [{'role': 'user', 'content': 'Hello, what is 2+2?'}],
            'expected_contains': '4'
        },
        {
            'name': 'model_restriction_test',
            'model': 'vault-architect',
            'client': 'mobile1',
            'messages': [{'role': 'user', 'content': 'Test message'}],
            'expected_error': 'not authorized'
        }
    ]
}
```

## Command-Line Interface

```bash
cv-tester [OPTIONS] [TESTS]...

Options:
  --url TEXT           ChatVault URL (default: http://localhost:4000)
  --client TEXT        Test client to use (default: mobile1)
  --verbose, -v        Enable verbose output
  --json               Output results in JSON format
  --help               Show this message and exit

Tests:
  basic                Run basic connectivity and authentication tests
  models               Test model-specific functionality
  errors               Test error handling scenarios
  streaming            Test streaming responses
  all                  Run all tests (default)
```

## Success Criteria
- [ ] cv-tester connects successfully to running ChatVault instance
- [ ] Authentication works with valid bearer tokens
- [ ] Hard-coded test requests execute and validate responses
- [ ] Multiple test scenarios cover different ChatVault features
- [ ] Clear pass/fail output for each test case
- [ ] Command-line options work for test selection and configuration
- [ ] Tool integrates with existing ChatVault testing workflow

## Testing Strategy
- [ ] Unit tests for individual test functions
- [ ] Integration tests with mock ChatVault server
- [ ] Manual testing with actual ChatVault instance
- [ ] Error condition testing with invalid configurations
- [ ] Performance testing for multiple concurrent requests

## Risk Assessment
- **Low Risk:** HTTP client implementation
  - **Mitigation:** Use well-tested requests library with timeout handling
- **Medium Risk:** Test data becomes outdated as ChatVault evolves
  - **Mitigation:** Design tests to be easily configurable and updatable
- **Low Risk:** False positives from response validation
  - **Mitigation:** Use flexible matching criteria and clear error reporting

## Dependencies
- [ ] requests >= 2.25.0 (for HTTP client)
- [ ] argparse (built-in, for CLI parsing)
- [ ] json (built-in, for response handling)
- [ ] pytest >= 6.0.0 (for testing the tester)

## Notes
This testing tool will be essential for validating ChatVault functionality during development and deployment. The tool should be designed to be:

1. **Easy to run**: Simple command-line interface with sensible defaults
2. **Comprehensive**: Cover all major ChatVault features and edge cases
3. **Maintainable**: Easy to add new test cases as ChatVault evolves
4. **Reliable**: Robust error handling and clear success/failure reporting
5. **Fast**: Quick execution for integration into CI/CD pipelines

The tool will serve as both a development aid and a deployment validation mechanism, ensuring ChatVault works correctly in different environments and configurations.