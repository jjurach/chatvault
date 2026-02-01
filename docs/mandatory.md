# MANDATORY - READ BEFORE STARTING WORK

This document defines the specific rules and structure for the ChatVault project.

## Project Overview

ChatVault is a FastAPI-based "Smart Audit" layer for LLMs. It provides:
- Secure gateway for local (Ollama) and commercial (OpenAI, Anthropic, etc.) models.
- Centralized API key management.
- Detailed usage tracking and audit logging.
- Client-based authentication with model-level access control.
- CLI tool for easy interaction and testing.

## Core Principles

1.  **Security First:** Never expose commercial API keys. All keys must be managed through `.env` and `config.yaml`.
2.  **Audit Integrity:** Every request and response must be logged. No bypasses for tracking.
3.  **Client isolation:** Clients only see the models they are authorized to access.
4.  **Local Preference:** Prefer local models (Ollama) when possible for privacy and cost.

## Project Structure

```
chatvault/
├── AGENTS.md               # Mandatory AI Agent instructions
├── src/
│   └── chatvault/          # Main package
│       ├── main.py         # FastAPI entry point
│       ├── cli.py          # CLI entry point
│       ├── auth.py         # Web authentication
│       ├── cli_auth.py     # CLI authentication
│       ├── config.py       # Application config
│       ├── cli_config.py   # CLI config
│       ├── database.py     # Database operations
│       ├── models.py       # SQL Alchemy models
│       ├── litellm_router.py # Model routing via LiteLLM
│       └── ...
├── tests/                  # Test suite
├── docs/                   # Documentation
│   ├── architecture.md
│   ├── definition-of-done.md
│   ├── deployment.md
│   └── implementation-reference.md
└── dev_notes/              # Planning and change logs
```

## Prohibited Actions

1.  **NO** hardcoding of API keys or bearer tokens.
2.  **NO** modifications to `docs/system-prompts/` (the Agent Kernel).
3.  **NO** creation of new directories without project plan approval.
4.  **NO** direct SQL queries without using the SQLAlchemy models.
5.  **NO** commits without verification proof in change logs.

## When to Stop and Ask

- If you encounter a conflict between `AGENTS.md` and project code.
- If you find a security vulnerability.
- If the required LLM provider is not supported by LiteLLM.
- If the database schema needs a non-trivial migration.

---
Last Updated: 2026-02-01
