# ChatVault Deployment Guide

This document provides comprehensive instructions for deploying ChatVault in production and development environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Production Deployment](#production-deployment)
- [SSH Reverse Tunnel Setup](#ssh-reverse-tunnel-setup)
- [Configuration](#configuration)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

**Local01 (Your local machine with GPU):**
- NVIDIA RTX 2080 or compatible GPU (4GB+ VRAM recommended)
- 16GB+ RAM
- 50GB+ free disk space
- Linux/Windows/macOS with Python 3.8+

**EC2 Instance (for remote access):**
- t3.micro or t3.small (free tier eligible)
- Ubuntu 22.04 LTS or Amazon Linux 2
- Security group allowing SSH (port 22) and HTTP (port 4000)

### Software Requirements

- **Python 3.8+** with pip
- **Ollama** installed and running locally
- **Git** for version control
- **SSH client** for tunnel setup
- **AWS CLI** (optional, for EC2 management)

### Network Requirements

- Stable internet connection
- Ability to SSH into EC2 instance
- Local firewall allowing outbound connections
- EC2 security group configured for ports 22 and 4000

## Local Development Setup

### 1. Clone and Setup Project

```bash
# Clone the repository
git clone <repository-url>
cd chatvault

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required .env settings for development:**
```bash
# Basic settings
CHATVAULT_API_KEY=dev-api-key-12345
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=sqlite:///./chatvault.db

# Ollama (if using local models)
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Setup Ollama (Optional)

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull a test model
ollama pull llama2:7b
```

### 4. Initialize Database

```bash
# Initialize database tables
python -c "from database import init_db; init_db()"
```

### 5. Run Development Server

```bash
# Start the server
python main.py

# Or with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 4000
```

### 6. Test Local Installation

```bash
# Run the demo script
python demo.py

# Or test manually with curl
curl http://localhost:4000/health
```

## Production Deployment

### 1. Prepare Production Environment

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install git
sudo apt install git -y
```

### 2. Deploy Application

```bash
# Clone repository
git clone <repository-url>
cd chatvault

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Production Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

**Required .env settings for production:**
```bash
# Security - Use strong, unique keys
CHATVAULT_API_KEY=your-production-api-key-here

# Server configuration
HOST=0.0.0.0
PORT=4000
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./chatvault.db

# API Keys for external providers
ANTHROPIC_API_KEY=your-anthropic-key
DEEPSEEK_API_KEY=your-deepseek-key
```

### 4. Setup Systemd Service

Create `/etc/systemd/system/chatvault.service`:

```ini
[Unit]
Description=ChatVault API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/chatvault
Environment=PATH=/home/ubuntu/chatvault/venv/bin
ExecStart=/home/ubuntu/chatvault/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable chatvault

# Start service
sudo systemctl start chatvault

# Check status
sudo systemctl status chatvault
```

### 5. Setup Log Rotation

Create `/etc/logrotate.d/chatvault`:

```
/home/ubuntu/chatvault/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 ubuntu ubuntu
}
```

## SSH Reverse Tunnel Setup

### EC2 Instance Preparation

1. **Launch EC2 instance:**
   - AMI: Ubuntu 22.04 LTS
   - Instance type: t3.micro (free tier)
   - Security group: Allow SSH (22) and Custom TCP (4000) from anywhere

2. **Connect to EC2:**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-public-ip
   ```

3. **Install basic tools:**
   ```bash
   sudo apt update
   sudo apt install -y openssh-server curl
   ```

### Local01 Setup (Your Machine)

1. **Generate SSH key pair (if not exists):**
   ```bash
   ssh-keygen -t rsa -b 4096 -C "chatvault-tunnel"
   ```

2. **Copy public key to EC2:**
   ```bash
   ssh-copy-id -i ~/.ssh/id_rsa.pub ubuntu@your-ec2-public-ip
   ```

3. **Test SSH connection:**
   ```bash
   ssh ubuntu@your-ec2-public-ip "echo 'SSH connection successful'"
   ```

### Establish Reverse Tunnel

**From Local01 to EC2:**

```bash
# Basic tunnel command
ssh -R 4000:localhost:4000 -N ubuntu@your-ec2-public-ip

# With connection persistence (recommended)
ssh -R 4000:localhost:4000 \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -N ubuntu@your-ec2-public-ip
```

### Automate Tunnel with Systemd

Create `/etc/systemd/system/chatvault-tunnel.service`:

```ini
[Unit]
Description=ChatVault SSH Reverse Tunnel
After=network.target chatvault.service
Wants=chatvault.service

[Service]
Type=simple
User=your-username
ExecStart=/usr/bin/ssh -R 4000:localhost:4000 \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -o StrictHostKeyChecking=no \
    -N ubuntu@your-ec2-public-ip
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable chatvault-tunnel
sudo systemctl start chatvault-tunnel
```

### Verify Tunnel

```bash
# On EC2 instance
curl http://localhost:4000/health

# From external client
curl http://your-ec2-public-ip:4000/health
```

## Configuration

### LiteLLM Model Configuration

Edit `config.yaml` to configure available models:

```yaml
model_list:
  - model_name: vault-architect
    litellm_params:
      model: claude-3-sonnet-20240229
      api_key: ${ANTHROPIC_API_KEY}

  - model_name: vault-local
    litellm_params:
      model: llama2:7b
      api_base: http://localhost:11434

  - model_name: vault-deepseek
    litellm_params:
      model: deepseek-chat
      api_key: ${DEEPSEEK_API_KEY}
```

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CHATVAULT_API_KEY` | API key for authentication | - | Yes |
| `HOST` | Server bind address | localhost | No |
| `PORT` | Server port | 4000 | No |
| `DEBUG` | Enable debug mode | false | No |
| `DATABASE_URL` | Database connection string | sqlite:///./chatvault.db | No |
| `ANTHROPIC_API_KEY` | Anthropic API key | - | No |
| `OLLAMA_BASE_URL` | Ollama server URL | http://localhost:11434 | No |

## Monitoring and Maintenance

### Health Checks

```bash
# Check service status
sudo systemctl status chatvault

# Check application health
curl http://localhost:4000/health

# View recent logs
sudo journalctl -u chatvault -n 50 -f
```

### Database Maintenance

```bash
# Backup database
cp chatvault.db chatvault.db.backup

# Check database integrity
sqlite3 chatvault.db "PRAGMA integrity_check;"

# View usage statistics
sqlite3 chatvault.db "SELECT model_name, COUNT(*) as requests, SUM(cost) as total_cost FROM usage_logs GROUP BY model_name;"
```

### Log Analysis

```bash
# View application logs
tail -f chatvault.log

# Search for errors
grep "ERROR" chatvault.log

# Monitor request patterns
grep "POST /v1/chat/completions" chatvault.log | wc -l
```

### Performance Monitoring

```bash
# Monitor system resources
htop
nvidia-smi  # For GPU monitoring

# Check network connections
netstat -tlnp | grep :4000

# Monitor disk usage
df -h
```

## Troubleshooting

### Common Issues

#### 1. Tunnel Connection Issues

**Problem:** SSH tunnel fails to establish
**Solutions:**
- Verify SSH key authentication
- Check EC2 security group settings
- Ensure Local01 firewall allows outbound connections
- Test basic SSH connection first

#### 2. Ollama Connection Failed

**Problem:** Local models not accessible
**Solutions:**
- Verify Ollama is running: `ollama list`
- Check OLLAMA_BASE_URL in .env
- Test Ollama directly: `curl http://localhost:11434/api/tags`

#### 3. Authentication Errors

**Problem:** API requests rejected
**Solutions:**
- Verify CHATVAULT_API_KEY in .env
- Check Authorization header format: `Bearer <key>`
- Ensure key matches between client and server

#### 4. Database Errors

**Problem:** SQLite connection issues
**Solutions:**
- Check file permissions on chatvault.db
- Verify DATABASE_URL in .env
- Test database connection manually

#### 5. High Memory Usage

**Problem:** Application consuming too much RAM
**Solutions:**
- Reduce max_concurrent_requests
- Implement request queuing
- Monitor and restart service periodically

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG
DEBUG=true

# Restart service
sudo systemctl restart chatvault

# View detailed logs
sudo journalctl -u chatvault -f
```

### Recovery Procedures

#### Service Restart
```bash
sudo systemctl restart chatvault
sudo systemctl restart chatvault-tunnel
```

#### Database Recovery
```bash
# Stop service
sudo systemctl stop chatvault

# Restore from backup
cp chatvault.db.backup chatvault.db

# Restart service
sudo systemctl start chatvault
```

#### Full System Reset
```bash
# Stop all services
sudo systemctl stop chatvault chatvault-tunnel

# Reset database
rm chatvault.db
python -c "from database import init_db; init_db()"

# Restart services
sudo systemctl start chatvault-tunnel
sudo systemctl start chatvault
```

## Security Considerations

- **API Keys:** Store securely, rotate regularly
- **SSH Keys:** Use strong keys, limit access
- **Firewall:** Restrict unnecessary ports
- **Updates:** Keep system and dependencies updated
- **Monitoring:** Log and monitor all access
- **Backups:** Regular database backups

## Support

For additional help:
1. Check application logs
2. Review this documentation
3. Test with the demo script
4. Check GitHub issues
5. Contact the development team

---

**Last updated:** December 2025
---
Last Updated: 2026-02-01
