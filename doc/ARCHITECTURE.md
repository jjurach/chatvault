# ChatVault Architecture

## Overview
ChatVault is a FastAPI-based "Smart Audit" layer that serves as a secure gateway for local and commercial Large Language Models (LLMs). The system centralizes API key management and usage tracking on local hardware while providing authenticated access to external devices through a single endpoint.

## Hardware Architecture

### Local01 (Primary Processing Node)
- **GPU:** NVIDIA RTX 2080 (8GB VRAM)
- **CPU:** Intel/AMD processor supporting CUDA
- **Purpose:** Local LLM processing via Ollama, API key storage, database operations
- **OS:** Linux-based system
- **Network:** Local network access

### EC2 Instance (Public Gateway)
- **Purpose:** Public-facing endpoint for external device access
- **Network:** AWS EC2 instance with public IP
- **Function:** SSH tunnel endpoint, traffic routing

## Network Architecture

```
External Devices → EC2 Public IP:4000 → SSH Reverse Tunnel → Local01:4000 → FastAPI App
```

### Data Flow
1. **Request Ingress:** External requests hit EC2 instance on port 4000
2. **SSH Tunnel:** Reverse SSH tunnel forwards traffic to Local01:4000
3. **FastAPI Processing:** Requests processed by ChatVault application
4. **LLM Routing:** Requests routed to appropriate LLM provider:
   - Local Ollama (via HTTPX)
   - Anthropic Claude (via LiteLLM)
   - DeepSeek (via LiteLLM)
5. **Response Processing:** Streaming responses captured with usage metadata
6. **Database Logging:** Token counts and costs logged to SQLite
7. **Response Egress:** Formatted response returned to client

## Component Architecture

### Core Components

#### FastAPI Application (`main.py`)
- Web server and API endpoints
- Authentication middleware
- Route handlers for `/v1/chat/completions`

#### LiteLLM Router (`litellm_router.py`)
- Provider abstraction layer
- Model mapping and routing
- Unified API interface

#### Database Layer (`models.py`, `database.py`)
- SQLite database for usage tracking
- SQLAlchemy ORM for data operations
- Schema: timestamp, user_id, model_name, input_tokens, output_tokens, cost

#### Authentication System (`auth.py`)
- Bearer token validation
- API key management
- Request authorization

#### Streaming Handler (`streaming_handler.py`)
- Async response processing
- Usage metadata capture
- Connection management

#### Configuration (`config.yaml`, `.env`)
- Model provider mappings
- API keys (securely stored)
- Application settings

### Data Flow Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  External       │    │  EC2 Gateway    │    │  Local01        │
│  Device         │───▶│  (Public IP)    │───▶│  FastAPI App    │
│                 │    │                 │    │                 │
│ • Mobile App    │    │ • SSH Tunnel     │    │ • Auth Check    │
│ • Web Client    │    │ • Port 4000      │    │ • Request Val.  │
│ • Desktop App   │    │                 │    │ • Route to LLM  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  LLM Providers  │    │  Usage Logger   │    │  SQLite DB      │
│                 │    │                 │    │                 │
│ • Ollama Local  │◀───│ • Token Counts   │───▶│ • Usage Stats   │
│ • Anthropic     │    │ • Cost Calc.     │    │ • Cost Tracking │
│ • DeepSeek      │    │ • Metadata       │    │ • Audit Trail   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Security Considerations

### API Key Management
- All commercial API keys stored locally on Local01
- Never exposed to external networks
- Environment variable configuration via `.env`

### Authentication
- Bearer token authentication required
- Token validation against local dictionary
- No external authentication services

### Network Security
- SSH reverse tunnel encryption
- Localhost-only API access on Local01
- No direct internet exposure of LLM providers

## Performance Characteristics

### Hardware Utilization
- RTX 2080: Local LLM inference
- CPU: FastAPI request processing, database operations
- Memory: Model loading, request queuing

### Latency Considerations
- Local Ollama: ~100-500ms response time
- Commercial APIs: Network-dependent (100ms-2s)
- Streaming: Real-time response processing

### Scalability
- Single-user focused design
- SQLite suitable for moderate usage logging
- FastAPI async support for concurrent requests

## Deployment Configuration

### SSH Tunnel Setup
```bash
# On Local01
ssh -R 4000:localhost:4000 ec2-user@ec2-public-ip
```

### Service Startup
```bash
# Local01
cd /path/to/chatvault
python main.py
```

### Configuration Files
- `config.yaml`: LiteLLM model mappings
- `.env`: API keys and secrets
- `requirements.txt`: Python dependencies

## Monitoring and Logging

### Application Logs
- FastAPI request/response logging
- Authentication attempts
- LLM provider errors

### Usage Analytics
- Token consumption tracking
- Cost calculation per request
- Model usage statistics

### System Monitoring
- GPU utilization (Ollama)
- Memory usage
- Network throughput

## Future Extensions

### Potential Enhancements
- Multiple user support
- Advanced cost analytics dashboard
- Model performance benchmarking
- Request rate limiting
- Backup and recovery procedures