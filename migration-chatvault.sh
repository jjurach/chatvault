#!/bin/bash
# Auto-generated migration script - REVIEW BEFORE EXECUTION
# Project: chatvault

set -e

# Create safety tag before migration
git tag -a -m 'pre-dev_notes-cleanup' pre-dev_notes-cleanup

# Move untracked files to tmp/ for review
mkdir -p tmp
mv dev_notes/project_plans/2025-12-24_19-19-12_chatvault-initial-implementation.md tmp/2025-12-24_19-19-12_chatvault-initial-implementation.md.untracked
mv dev_notes/project_plans/2025-12-25_23-58-11_fix-relative-imports-cv-tester-installation.md tmp/2025-12-25_23-58-11_fix-relative-imports-cv-tester-installation.md.untracked
mv dev_notes/project_plans/2025-12-25_22-56-32_cv-tester-testing-tool.md tmp/2025-12-25_22-56-32_cv-tester-testing-tool.md.untracked
mv dev_notes/project_plans/2025-12-25_23-18-00_cli-server-integration.md tmp/2025-12-25_23-18-00_cli-server-integration.md.untracked
mv dev_notes/project_plans/2025-12-26_00-04-23_fix-sqlalchemy-execute-error.md tmp/2025-12-26_00-04-23_fix-sqlalchemy-execute-error.md.untracked
mv dev_notes/project_plans/2025-12-25_21-41-48_directory-structure-refactor.md tmp/2025-12-25_21-41-48_directory-structure-refactor.md.untracked
mv dev_notes/project_plans/2025-12-25_22-15-43_chatvault-cli-implementation.md tmp/2025-12-25_22-15-43_chatvault-cli-implementation.md.untracked
mv dev_notes/project_plans/2025-12-26_02-30-42_remaining-features-implementation.md tmp/2025-12-26_02-30-42_remaining-features-implementation.md.untracked

# Create planning directory structure
mkdir -p planning/inbox

# Migrate project_plans → planning/*-plan.md
git mv dev_notes/project_plans/2025-12-24_19-19-12_chatvault-initial-implementation.md planning/2025-12-24_19-19-12_chatvault-initial-implementation-plan.md
git mv dev_notes/project_plans/2025-12-25_21-41-48_directory-structure-refactor.md planning/2025-12-25_21-41-48_directory-structure-refactor-plan.md
git mv dev_notes/project_plans/2025-12-25_22-15-43_chatvault-cli-implementation.md planning/2025-12-25_22-15-43_chatvault-cli-implementation-plan.md
git mv dev_notes/project_plans/2025-12-25_22-56-32_cv-tester-testing-tool.md planning/2025-12-25_22-56-32_cv-tester-testing-tool-plan.md
git mv dev_notes/project_plans/2025-12-25_23-18-00_cli-server-integration.md planning/2025-12-25_23-18-00_cli-server-integration-plan.md
git mv dev_notes/project_plans/2025-12-25_23-58-11_fix-relative-imports-cv-tester-installation.md planning/2025-12-25_23-58-11_fix-relative-imports-cv-tester-installation-plan.md
git mv dev_notes/project_plans/2025-12-26_00-04-23_fix-sqlalchemy-execute-error.md planning/2025-12-26_00-04-23_fix-sqlalchemy-execute-error-plan.md
git mv dev_notes/project_plans/2025-12-26_02-30-42_remaining-features-implementation.md planning/2025-12-26_02-30-42_remaining-features-implementation-plan.md

# Remove empty directories
rmdir dev_notes/specs 2>/dev/null || true
rmdir dev_notes/project_plans 2>/dev/null || true
rmdir dev_notes/inbox 2>/dev/null || true

echo '✓ Migration complete for chatvault'