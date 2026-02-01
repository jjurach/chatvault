# Planning Document Templates

This document provides templates for planning documents used in ChatVault.

## Agent Kernel Templates

The project follows the Agent Kernel template system. For complete template documentation, see:

-   **[Template Structure Guide](system-prompts/templates/structure.md)** - Standard templates for project plans, architecture decisions, and investigation reports

## Project-Specific Conventions

### Development Notes Directory

Development notes and session transcripts are stored in `dev_notes/` using the format:

```
dev_notes/[subdir]/YYYY-MM-DD_HH-MM-SS_description.md
```

-   `dev_notes/specs/`: Requirements and user intentions.
-   `dev_notes/project_plans/`: Detailed implementation strategies (require approval).
-   `dev_notes/changes/`: Records of actual implementation and verification.

### Quick Reference Templates

#### Spec File
```markdown
# Spec: [Description]

**Date:** YYYY-MM-DD HH:MM:SS
**Workflow:** @logs-first (optional)

## User Request
[Copy of user request]

## Goals
- [ ] Goal 1

## Acceptance Criteria
- [ ] Criterion 1
```

#### Project Plan
```markdown
# Project Plan: [Description]

**Date:** YYYY-MM-DD HH:MM:SS
**Status:** Draft

## Objective
[What we are doing]

## Implementation Phases
1. **Phase 1: [Name]**
   - [ ] Task 1
   - [ ] Task 2

## Verification Steps
- [ ] Step 1
```

#### Change Documentation
```markdown
# Change: [Description]

**Date:** YYYY-MM-DD HH:MM:SS
**Status:** Completed

## Implementation Details
[What was done]

## Verification Results
- **Command:** `pytest tests/test_feature.py`
- **Output:**
```
[Paste output here]
```

---
Last Updated: 2026-02-01
