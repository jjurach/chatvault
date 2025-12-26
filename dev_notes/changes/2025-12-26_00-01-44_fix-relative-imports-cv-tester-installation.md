# Change: Fix Relative Imports and CV-Tester Installation

**Date:** 2025-12-26 00:01:44
**Type:** Bug Fix
**Priority:** High
**Status:** Completed
**Related Project Plan:** `dev_notes/project_plans/2025-12-25_23-58-11_fix-relative-imports-cv-tester-installation.md`

## Overview
Fixed the "attempted relative import with no known parent package" error in the `chatvault serve` command and arranged for cv-tester to be installed as a command-line tool alongside chatvault.

## Files Modified
- `src/cli.py` - Updated imports to use relative imports
- `setup.py` - Modified entry points and package structure
- `src/chatvault/main.py` - Updated uvicorn.run to use app object directly
- Project structure reorganized to use proper Python package layout

## Code Changes

### Before: src/cli.py imports
```python
# Import CLI modules
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from cli_config import load_config, get_client_config, get_available_models, get_provider_for_model
from cli_auth import authenticate_client, validate_model_access
from cli_logging import setup_logging
from cli_server import make_chat_request, get_server_url, check_server_health
```

### After: src/cli.py imports
```python
# Import CLI modules
from .cli_config import load_config, get_client_config, get_available_models, get_provider_for_model
from .cli_auth import authenticate_client, validate_model_access
from .cli_logging import setup_logging
from .cli_server import make_chat_request, get_server_url, check_server_health
```

### Before: setup.py entry points
```python
entry_points={
    "console_scripts": [
        "chatvault=cli:main",
    ],
},
```

### After: setup.py entry points
```python
entry_points={
    "console_scripts": [
        "chatvault=chatvault.cli:main",
        "cv-tester=chatvault.cv_tester:main",
    ],
},
```

### Before: src/chatvault/main.py uvicorn.run
```python
uvicorn.run(
    "main:app",
    host=settings.host,
    port=settings.port,
    reload=settings.debug,
    log_level=settings.log_level.lower(),
    access_log=True
)
```

### After: src/chatvault/main.py uvicorn.run
```python
uvicorn.run(
    app,
    host=settings.host,
    port=settings.port,
    reload=settings.debug,
    log_level=settings.log_level.lower(),
    access_log=True
)
```

## Testing
- [x] `chatvault serve` starts without import errors
- [x] `cv-tester --help` command is available
- [x] Both commands are executable from venv/bin
- [x] No regression in existing CLI functionality

## Impact Assessment
- Breaking changes: None (commands work the same way)
- Dependencies affected: None
- Performance impact: None
- Package structure improved for better maintainability

## Notes
Reorganized the project structure to use a proper Python package layout with all modules under the `chatvault` package. This ensures correct relative imports when the package is installed. The cv-tester tool is now properly installed as a console script alongside chatvault.