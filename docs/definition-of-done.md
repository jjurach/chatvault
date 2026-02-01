# Definition of Done - ChatVault

**Referenced from:** [AGENTS.md](../AGENTS.md)

This document defines the "Done" criteria for ChatVault. It extends the universal Agent Kernel Definition of Done with project-specific requirements.

## Agent Kernel Definition of Done

This project follows the Agent Kernel Definition of Done. **You MUST review these documents first:**

### Universal Requirements

See **[Universal Definition of Done](system-prompts/principles/definition-of-done.md)** for:
- Plan vs. Reality Protocol
- Verification as Data
- Codebase State Integrity
- Agent Handoff

### Python Requirements

See **[Python Definition of Done](system-prompts/languages/python/definition-of-done.md)** for:
- Python environment & dependencies
- Testing requirements (pytest)
- Code quality standards (PEP 8, type hints)

## Project-Specific Extensions

The following requirements are specific to ChatVault and extend the Agent Kernel DoD:

### 1. CLI Integrity

**Mandatory Checks:**
- [ ] New CLI commands are registered in `src/chatvault/cli.py`.
- [ ] Commands support `--config`, `--verbose`, and `--logfile` where appropriate.
- [ ] Command help text is clear and accurate.

### 2. Audit Logging

**Mandatory Checks:**
- [ ] All significant actions are logged via `cli_logging.py` or FastAPI logger.
- [ ] Logs are in JSON format for the CLI.
- [ ] No sensitive information (tokens, keys) is logged.

### 3. API Compatibility

**Mandatory Checks:**
- [ ] Server endpoints remain compatible with OpenAI API specs where intended.
- [ ] `cv-tester.py` passes all relevant tests for any changes to the server or model routing.

### 4. Configuration

**Mandatory Checks:**
- [ ] New configuration keys are added to `config.yaml` and documented in `README.md`.
- [ ] Pydantic models in `config.py` are updated if needed.

## Pre-Commit Checklist

Before committing, verify:

- [ ] `pytest tests/` passes.
- [ ] `python cv_tester.py all` passes (if server modified).
- [ ] Code is formatted and linted.
- [ ] Change log created in `dev_notes/changes/` with verification proof.

## See Also

- [AGENTS.md](../AGENTS.md) - Core workflow
- [Architecture](architecture.md) - System design
- [Implementation Reference](implementation-reference.md) - Code patterns
- [Workflows](workflows.md) - Development workflows

---
Last Updated: 2026-02-01