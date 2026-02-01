# Project Workflows - ChatVault

This document describes development workflows specific to ChatVault.

## Core Agent Workflow

All AI agents working on this project must follow the **A-E workflow** defined in [AGENTS.md](../AGENTS.md).

## Project-Specific Workflows

### 1. Feature Development

**When to use:** Adding new CLI commands or server features.

**Steps:**
1.  **Analyze:** Identify if it's a CLI change, Server change, or both.
2.  **Spec:** Document the new command/endpoint in `dev_notes/specs/`.
3.  **Plan:** Create a plan in `dev_notes/project_plans/`.
4.  **Implement:**
    -   Update `src/chatvault/`.
    -   Add unit tests in `tests/`.
    -   If it's an API change, update `cv_tester.py`.
5.  **Verify:** Run `pytest` and `cv-tester`.

### 2. Testing with CV-Tester

**When to use:** After any change to the FastAPI server or `litellm_router`.

**Steps:**
1.  Start the ChatVault server (if testing locally):
    ```bash
    python src/chatvault/main.py
    ```
2.  Run the tester in another terminal:
    ```bash
    python cv_tester.py all
    ```
3.  Verify all tests pass (✅).
4.  If tests fail, check JSON logs for error details.

### 3. Database Migrations

**When to use:** When `models.py` schema is changed.

**Steps:**
1.  Use Alembic (if configured) or create a manual migration script.
2.  Test the migration on a copy of `chatvault.db`.
3.  Update `database.py` if initialization logic changes.

## See Also

- [AGENTS.md](../AGENTS.md) - Core workflow
- [Definition of Done](definition-of-done.md) - Quality standards
- [Architecture](architecture.md) - System design
- [Implementation Reference](implementation-reference.md) - Code patterns

---
Last Updated: 2026-02-01