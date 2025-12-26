# ChatVault Testing Guide

This document provides comprehensive testing instructions for ChatVault, covering authentication, authorization, model access, and API functionality using both cv-tester commands and direct curl requests.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Starting the Server](#starting-the-server)
- [Client Configuration](#client-configuration)
- [cv-tester Commands](#cv-tester-commands)
- [curl Commands](#curl-commands)
- [Testing Scenarios](#testing-scenarios)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- ChatVault installed and configured
- Ollama running locally (for qwen3-8k and mistral models)
- API keys configured in `.env` file (for commercial models)
- Python virtual environment activated

## Starting the Server

```bash
# Start ChatVault server
python -m chatvault.cli serve --log-level INFO

# Or with debug logging
python -m chatvault.cli serve --log-level DEBUG
```

The server will start on `http://localhost:4000` by default.

## Client Configuration

ChatVault supports multiple clients with different access levels:

### local1 (Restricted Access)
- **Bearer Token**: `YOUR_LOCAL1_BEARER_TOKEN`
- **Allowed Models**: `vault-qwen3-8k`, `vault-mistral-nemo-8k`
- **Use Case**: Local Ollama models only

### full1 (Full Access)
- **Bearer Token**: `YOUR_FULL1_BEARER_TOKEN`
- **Allowed Models**: All configured models (`*`)
- **Use Case**: Complete access to all providers

## cv-tester Commands

cv-tester provides automated testing of ChatVault functionality. All commands assume the server is running on `http://localhost:4000`.

### Basic Connectivity Testing

```bash
# Test basic server connectivity
cv-tester basic

# Test with specific client
cv-tester --client local1 basic
```

### Authentication Testing

```bash
# Test authentication with local1 client
cv-tester --client local1 models

# Test authentication with full1 client
cv-tester --client full1 models

# Test with custom bearer token
cv-tester --bearer YOUR_TOKEN models
```

### Model Access Testing

```bash
# List models available to local1 client
cv-tester --client local1 list-models

# List models available to full1 client
cv-tester --client full1 list-models

# Run comprehensive model access tests
cv-tester --client local1 models
cv-tester --client full1 models
```

### Comprehensive Testing

```bash
# Run all tests with local1 client
cv-tester --client local1 all

# Run all tests with full1 client
cv-tester --client full1 all

# Run streaming tests
cv-tester --client local1 streaming

# Run error handling tests
cv-tester errors
```

### Verbose Output

```bash
# Enable verbose output for debugging
cv-tester --client local1 --verbose models

# JSON output format
cv-tester --client local1 --json models
```

## curl Commands

Direct curl commands for testing ChatVault API endpoints. Replace `BEARER_TOKEN` with the appropriate client token.

### Health Check

```bash
# Health check with authentication (required)
curl -H "Authorization: Bearer YOUR_LOCAL1_BEARER_TOKEN" \
     http://localhost:4000/health

# Pretty-printed health check
curl -H "Authorization: Bearer YOUR_LOCAL1_BEARER_TOKEN" \
     http://localhost:4000/health | jq

# Health check without authentication (returns 401)
curl http://localhost:4000/health
# Expected: 401 Unauthorized
```

### List Available Models

```bash
# List models for local1 client (restricted access)
curl -H "Authorization: Bearer YOUR_LOCAL1_BEARER_TOKEN" \
     http://localhost:4000/v1/models

# List models for full1 client (full access)
curl -H "Authorization: Bearer YOUR_FULL1_BEARER_TOKEN" \
     http://localhost:4000/v1/models

# Pretty-printed model list
curl -H "Authorization: Bearer YOUR_LOCAL1_BEARER_TOKEN" \
     http://localhost:4000/v1/models | jq
```

### Chat Completions

#### Successful Requests

```bash
# Chat with qwen3-8k using local1 client (allowed)
curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_LOCAL1_BEARER_TOKEN" \
     -d '{
       "model": "vault-qwen3-8k",
       "messages": [
         {"role": "user", "content": "Hello, what is your name?"}
       ],
       "max_tokens": 100
     }'

# Chat with qwen3-8k using full1 client (allowed)
curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_FULL1_BEARER_TOKEN" \
     -d '{
       "model": "vault-qwen3-8k",
       "messages": [
         {"role": "user", "content": "Hello, what is your name?"}
       ],
       "max_tokens": 100
     }'
```

#### Access Denied Examples

```bash
# Try to access vault-architect with local1 client (should fail)
curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_LOCAL1_BEARER_TOKEN" \
     -d '{
       "model": "vault-architect",
       "messages": [
         {"role": "user", "content": "Hello"}
       ]
     }'

# Expected response: 403 Forbidden
# {"error":{"message":"Access denied to model 'vault-architect'","type":"invalid_request_error","code":403}}
```

#### Authentication Failures

```bash
# Missing authorization header
curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "vault-qwen3-8k",
       "messages": [{"role": "user", "content": "Hello"}]
     }'

# Expected response: 401 Unauthorized
# {"error":{"message":"Authentication required","type":"invalid_request_error","code":401}}

# Invalid bearer token
curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer invalid_token" \
     -d '{
       "model": "vault-qwen3-8k",
       "messages": [{"role": "user", "content": "Hello"}]
     }'

# Expected response: 401 Unauthorized
# {"error":{"message":"Invalid authentication token","type":"invalid_request_error","code":401}}
```

### Streaming Responses

```bash
# Streaming chat completion
curl -X POST http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_LOCAL1_BEARER_TOKEN" \
     -d '{
       "model": "vault-qwen3-8k",
       "messages": [{"role": "user", "content": "Tell me a short story"}],
       "stream": true,
       "max_tokens": 200
     }'
```

### Usage Statistics

```bash
# Get usage statistics (requires authentication)
curl -H "Authorization: Bearer YOUR_LOCAL1_BEARER_TOKEN" \
     http://localhost:4000/usage
```

## Testing Scenarios

### Scenario 1: Client Model Access Verification

**Objective**: Verify that clients can only access their allowed models

**Steps**:
1. List models for local1 client
2. List models for full1 client
3. Attempt to use restricted models with local1 client
4. Verify full1 client can access all models

**Expected Results**:
- local1: 2 models (vault-qwen3-8k, vault-mistral-nemo-8k)
- full1: 7 models (all configured models)
- local1 accessing vault-architect: 403 Forbidden

### Scenario 2: Authentication Testing

**Objective**: Verify proper authentication enforcement

**Steps**:
1. Make request without Authorization header
2. Make request with invalid bearer token
3. Make request with valid local1 token
4. Make request with valid full1 token

**Expected Results**:
- No auth header: 401 Unauthorized
- Invalid token: 401 Unauthorized
- Valid tokens: 200 OK with appropriate model access

### Scenario 3: Model Functionality Testing

**Objective**: Verify models work correctly for authorized clients

**Steps**:
1. Test qwen3-8k with local1 client
2. Test vault-local with full1 client (if Ollama available)
3. Test commercial models with full1 client (if API keys configured)
4. Test streaming responses

### Scenario 4: Error Handling

**Objective**: Verify proper error responses

**Steps**:
1. Request nonexistent model
2. Send malformed JSON
3. Test invalid message format

## CLI Direct Chat Commands

For testing without the server running, use the direct CLI chat commands:

```bash
# Direct chat with any configured model
python -m chatvault.cli chat qwen3-8k user "Hello, how are you?"

# With streaming
python -m chatvault.cli chat qwen3-8k user "Tell me a story" --stream

# With custom parameters
python -m chatvault.cli chat qwen3-8k user "Hello" --temperature 0.8 --max-tokens 100

# List all configured models
python -m chatvault.cli list-models
```

## Troubleshooting

### Common Issues

**1. "Model not configured" errors**
- Check that the model name matches exactly (e.g., `vault-qwen3-8k`, not `qwen3-8k`)
- Verify the model is configured in `config.yaml`

**2. Authentication failures**
- Ensure the bearer token is correct and properly formatted
- Check that the Authorization header is: `Bearer <token>`
- Verify the client has access to the requested model

**3. Connection refused errors**
- Ensure the ChatVault server is running on the correct port
- Check that no other service is using port 4000

**4. Model access denied**
- Verify you're using the correct client token for the model
- Check client permissions in `config.yaml`
- local1 can only access Ollama models

**5. Commercial model failures**
- Ensure API keys are configured in `.env` file
- Check API key validity and quota limits

### Debug Commands

```bash
# Check server health
curl http://localhost:4000/health

# Check server logs
tail -f server.log

# Test basic connectivity
cv-tester basic

# Verbose authentication testing
cv-tester --client local1 --verbose models
```

### Environment Variables

Ensure these are set in your `.env` file:

```bash
# Required
CHATVAULT_API_KEY=your_master_key_here

# For Ollama models
OLLAMA_BASE_URL=http://localhost:11434

# For commercial models (optional)
ANTHROPIC_API_KEY=sk-ant-api03-...
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
XAI_API_KEY=...
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `cv-tester --client local1 list-models` | Show models accessible to local1 |
| `cv-tester --client full1 models` | Test full1 authentication and model access |
| `cv-tester --client local1 --verbose models` | Verbose testing output |
| `python -m chatvault.cli chat qwen3-8k user "Hello"` | Direct CLI chat (no server needed) |

This testing guide covers all major ChatVault functionality, ensuring proper authentication, authorization, and model access controls.