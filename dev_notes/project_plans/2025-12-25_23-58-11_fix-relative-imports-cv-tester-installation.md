# Project Plan: Fix Relative Imports and CV-Tester Installation

**Date:** 2025-12-25 23:58:11
**Estimated Duration:** 30 minutes
**Complexity:** Low
**Status:** Completed

## Objective
Fix the relative import error in the `chatvault serve` command and arrange for cv-tester to be installed alongside chatvault in the virtual environment's bin directory.

## Requirements
- [x] Fix relative import error in `chatvault serve` command
- [x] Make `cv-tester` available as an installed command alongside `chatvault`
- [x] Ensure both commands are executable after `pip install`
- [x] Maintain existing functionality

## Implementation Steps
1. **Update CLI Imports** (10 minutes)
   - Files to modify: `src/cli.py`
   - Change imports from `from cli_config import` to `from .cli_config import`
   - Change imports from `from cli_auth import` to `from .cli_auth import`
   - Change imports from `from cli_logging import` to `from .cli_logging import`
   - Change imports from `from cli_server import` to `from .cli_server import`
   - Status: [ ] Not Started

2. **Update Setup Configuration** (10 minutes)
   - Files to modify: `setup.py`
   - Add `scripts=['cv_tester.py']` to include cv-tester as an installable script
   - Status: [ ] Not Started

3. **Test Installation** (10 minutes)
   - Run `pip install -e .` to install in development mode
   - Verify `chatvault serve` works without import errors
   - Verify `cv-tester --help` is available in PATH
   - Status: [ ] Not Started

## Success Criteria
- [ ] `chatvault serve` runs without "attempted relative import" error
- [ ] `cv-tester` command is available in the virtual environment
- [ ] Both commands execute successfully
- [ ] No regression in existing CLI functionality

## Testing Strategy
- [ ] Manual testing of `chatvault serve` command
- [ ] Manual testing of `cv-tester --help` command
- [ ] Verify both are in venv/bin directory
- [ ] Test basic functionality of both tools

## Risk Assessment
- **Low Risk:** Import fixes are straightforward and well-understood
- **Low Risk:** Adding scripts to setup.py is standard practice
- **Mitigation:** Test in development mode first before committing

## Notes
The relative import issue occurs because when the package is installed, Python needs relative imports to properly resolve sibling modules within the package. The cv-tester script is standalone and can be installed directly as a script file.