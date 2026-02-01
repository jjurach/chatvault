# Implementation Reference

This document describes the key patterns and conventions used in the ChatVault project.

## 1. FastAPI Route Pattern

New endpoints should follow this pattern:

```python
@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user: User = Depends(get_current_user)
):
    try:
        # Implementation...
        return response
    except Exception as e:
        logger.error(f"Error in chat_completions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 2. CLI Command Pattern

We use `click` for the CLI:

```python
@cli.command()
@click.argument('model')
@click.option('--verbose', '-v', is_flag=True)
def my_command(model, verbose):
    """Command description."""
    # Setup logging
    logger = setup_logging(verbose=verbose)
    
    # Implementation...
```

## 3. Database Access Pattern

Use SQLAlchemy sessions and the established models:

```python
from .database import SessionLocal
from .models import UsageLog

def log_usage(data):
    with SessionLocal() as session:
        log = UsageLog(**data)
        session.add(log)
        session.commit()
```

## 4. Configuration Management

-   `src/chatvault/config.py`: Application-wide settings using `Pydantic`.
-   `src/chatvault/cli_config.py`: CLI-specific YAML configuration parsing.
-   Environment variables should have defaults in `config.py`.

## 5. Error Handling & Logging

-   Use `logging.getLogger(__name__)`.
-   For CLI, use the `setup_logging` from `cli_logging.py` which produces JSON logs for auditability.
-   Always include context in log messages (e.g., client ID, model name).

## 6. Testing Patterns

We use `pytest`. Tests should be located in `tests/`.
-   Unit tests: `tests/test_*.py`
-   Integration tests: `tests/test_cv_tester.py`

## 7. Database Changes

### Schema Changes
- **ALWAYS** create a migration script.
- Document the migration in the project plan.
- Include rollback procedures.

### Migration Script Format
```sql
-- Migration: [Description]
-- Date: YYYY-MM-DD
-- Related Project Plan: [plan-id]

-- Forward migration
BEGIN;
-- Your migration SQL here
COMMIT;

-- Rollback (if needed)
-- BEGIN;
-- Rollback SQL here
-- COMMIT;
```

## 8. API Documentation Template

Use this template for documenting new or modified endpoints:

```markdown
## [Endpoint Name]

**Method:** [GET/POST/PUT/DELETE]  
**Path:** `/api/v1/[path]`  
**Authentication:** [Required/Optional]

### Request
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

### Response (Success)
```json
{
  "status": "success",
  "data": {}
}
```

### Response (Error)
```json
{
  "status": "error",
  "message": "Error description",
  "code": "ERROR_CODE"
}
```
```

---
Last Updated: 2026-02-01
