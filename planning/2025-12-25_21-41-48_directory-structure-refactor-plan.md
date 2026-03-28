# Project Plan: Directory Structure Refactor

**Date:** 2025-12-25 21:41:48
**Estimated Duration:** 2 hours
**Complexity:** Medium
**Status:** Completed

## Objective
Restructure the Chat Vault Python project to follow best practices by moving all Python source files into a dedicated `src/` directory. This will improve code organization, maintainability, and follow standard Python project structure conventions.

## Requirements
- [ ] Create a `src/` directory in the project root
- [ ] Move all Python source files from root to `src/` directory
- [ ] Update all import statements to reflect new file locations
- [ ] Ensure all relative imports work correctly
- [ ] Verify that tests and demo scripts still function properly
- [ ] Update any configuration files that reference moved files

## Implementation Steps

1. **Create src/ directory structure**
   - Files to create: `src/`
   - Files to modify: None
   - Dependencies: None
   - Estimated time: 5 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

2. **Move Python source files to src/ directory**
   - Files to move:
     - `auth.py` → `src/auth.py`
     - `config.py` → `src/config.py`
     - `database.py` → `src/database.py`
     - `demo.py` → `src/demo.py`
     - `litellm_router.py` → `src/litellm_router.py`
     - `main.py` → `src/main.py`
     - `models.py` → `src/models.py`
     - `streaming_handler.py` → `src/streaming_handler.py`
   - Dependencies: Step 1 completion
   - Estimated time: 15 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

3. **Update import statements**
   - Files to modify: All moved Python files
   - Dependencies: Step 2 completion
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

4. **Update configuration and entry points**
   - Files to modify:
     - Check `config.yaml` for any file path references
     - Update `requirements-dev.txt` if needed
     - Update `requirements.txt` if needed
   - Dependencies: Step 2 completion
   - Estimated time: 15 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

5. **Test the refactored structure**
   - Run all tests in `tests/` directory
   - Execute demo scripts to ensure functionality
   - Check for any import errors or runtime issues
   - Dependencies: Steps 2-4 completion
   - Estimated time: 30 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

6. **Final verification and cleanup**
   - Verify no Python files remain in root directory (except special files like setup.py)
   - Run final test suite
   - Check that main application still starts correctly
   - Dependencies: Step 5 completion
   - Estimated time: 15 minutes
   - Status: [ ] Not Started / [ ] In Progress / [ ] Completed

## Success Criteria
- [ ] All Python source files are located in `src/` directory
- [ ] No Python source files remain in project root
- [ ] All imports work correctly from new locations
- [ ] All tests pass
- [ ] Demo scripts run without errors
- [ ] Main application starts and functions properly
- [ ] No breaking changes to functionality

## Testing Strategy
- [ ] Unit tests: Run `python -m pytest tests/` from project root
- [ ] Integration tests: Execute demo scripts (`python src/demo.py`)
- [ ] Import tests: Verify all modules can be imported without errors
- [ ] Functionality tests: Run main application and verify core features work
- [ ] Regression tests: Ensure existing functionality is preserved

## Risk Assessment
- **High Risk:** Import statement updates could break module dependencies
  - **Mitigation:** Test imports after each change, maintain backup of original structure
- **Medium Risk:** Configuration files may contain hardcoded paths
  - **Mitigation:** Review all config files before changes, update paths as needed
- **Low Risk:** Tests may fail due to path changes
  - **Mitigation:** Run tests immediately after restructure to catch issues early

## Dependencies
- [ ] Python 3.x environment
- [ ] All current dependencies in requirements.txt
- [ ] Test framework (pytest) installed
- [ ] Access to run tests and demo scripts

## Database Changes (if applicable)
- [ ] No database schema changes required
- [ ] No migration scripts needed

## API Changes (if applicable)
- [ ] No API endpoint changes
- [ ] No new/modified/deprecated endpoints

## Notes
This refactor follows Python best practices for project structure. The `src/` directory layout is a common convention that:

1. Clearly separates source code from configuration and documentation
2. Makes it easier to package the application
3. Improves import organization
4. Follows standards seen in many Python projects

After completion, the project structure will look like:
```
chatvault/
├── src/
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   ├── demo.py
│   ├── litellm_router.py
│   ├── main.py
│   ├── models.py
│   └── streaming_handler.py
├── tests/
├── dev_notes/
├── doc/
├── migrations/
├── requirements.txt
├── config.yaml
└── ...
```

All import statements will need to be updated to use relative imports within the src package or absolute imports from the src package.