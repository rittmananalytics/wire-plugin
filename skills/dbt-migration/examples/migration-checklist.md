# Migration Checklist Template

**Project:** {project_name}
**Source Platform:** {source_platform} (dbt {source_dbt_version})
**Target Platform:** {target_platform} (dbt {target_dbt_version})
**Date Started:** YYYY-MM-DD
**Migration Lead:** {name}

---

## Pre-Migration

- [ ] Migration assessment completed (model inventory, platform-specific code catalogue)
- [ ] All stakeholders informed of migration plan
- [ ] Target platform credentials configured
- [ ] `dbt debug` passes on target platform
- [ ] Packages audited for target platform compatibility
- [ ] `packages.yml` updated with compatible versions
- [ ] Pre-migration unit tests created on source platform
- [ ] All pre-migration unit tests pass on source platform
- [ ] Pre-migration test baseline documented: _{count}_ tests, all passing
- [ ] Jira tasks created for migration work (if using Wire/Atlassian)

## Assessment Results

| Category | Count | Complexity |
|----------|-------|------------|
| Total models | | |
| Staging models | | |
| Integration models | | |
| Mart models | | |
| Custom macros | | |
| Platform-specific functions found | | |
| Packages to update | | |

## Platform-Specific Code Inventory

| File | Line(s) | Function/Syntax | Category | Estimated Fix |
|------|---------|----------------|----------|---------------|
| | | | | |
| | | | | |
| | | | | |

---

## Migration Execution

### Step 1: Environment Setup
- [ ] New target added to `profiles.yml`
- [ ] `dbt debug --target {target}` passes
- [ ] Target database/schema/catalog exists
- [ ] `dbt_project.yml` updated for target platform config
- [ ] `dbt deps` succeeds with updated packages

### Step 2: Initial Compilation
- [ ] `target/` directory cleared
- [ ] `dbt compile --target {target}` run
- [ ] All compilation errors catalogued
- [ ] Errors classified by category
- [ ] Error counts by category:
  - Data types: ___
  - Date/time functions: ___
  - String functions: ___
  - NULL handling: ___
  - Identifier quoting: ___
  - Array/Struct/JSON: ___
  - Window functions: ___
  - Custom macros: ___
  - Package-specific: ___
  - Other: ___

### Step 3: Fix — Data Types
- [ ] All data type issues identified
- [ ] Fixes applied
- [ ] `target/` cleared and recompiled
- [ ] Error count reduced: ___ -> ___
- [ ] Changes documented in migration_changes.md

### Step 4: Fix — Date/Time Functions
- [ ] All date/time issues identified
- [ ] Fixes applied (using dispatch macros where appropriate)
- [ ] `target/` cleared and recompiled
- [ ] Error count reduced: ___ -> ___
- [ ] Changes documented in migration_changes.md

### Step 5: Fix — String Functions
- [ ] All string function issues identified
- [ ] Fixes applied
- [ ] `target/` cleared and recompiled
- [ ] Error count reduced: ___ -> ___
- [ ] Changes documented in migration_changes.md

### Step 6: Fix — NULL Handling
- [ ] All NULL handling issues identified
- [ ] Fixes applied
- [ ] `target/` cleared and recompiled
- [ ] Error count reduced: ___ -> ___
- [ ] Changes documented in migration_changes.md

### Step 7: Fix — Identifier Quoting
- [ ] All quoting issues identified
- [ ] Fixes applied
- [ ] `target/` cleared and recompiled
- [ ] Error count reduced: ___ -> ___
- [ ] Changes documented in migration_changes.md

### Step 8: Fix — Array/Struct/JSON
- [ ] All complex type issues identified
- [ ] Fixes applied
- [ ] `target/` cleared and recompiled
- [ ] Error count reduced: ___ -> ___
- [ ] Changes documented in migration_changes.md

### Step 9: Fix — Custom Macros
- [ ] All macro issues identified
- [ ] Macros rewritten or dispatch macros created
- [ ] `target/` cleared and recompiled
- [ ] Error count reduced: ___ -> ___
- [ ] Changes documented in migration_changes.md

### Step 10: Fix — Package-Specific & Other
- [ ] All remaining issues identified
- [ ] Fixes applied
- [ ] `target/` cleared and recompiled
- [ ] **0 compilation errors achieved**
- [ ] Changes documented in migration_changes.md

---

## Validation

- [ ] `dbt build --target {target}` succeeds (0 errors)
- [ ] All unit tests pass on target platform
- [ ] Unit test results match pre-migration baseline
- [ ] All data tests pass on target platform
- [ ] Row count comparison completed for key models:

| Model | Source Row Count | Target Row Count | Match? |
|-------|-----------------|-----------------|--------|
| | | | |
| | | | |

- [ ] Key aggregate comparisons completed:

| Model | Metric | Source Value | Target Value | Difference | Acceptable? |
|-------|--------|-------------|-------------|------------|-------------|
| | | | | | |

- [ ] No unexpected NULL values introduced
- [ ] Timestamp/timezone behavior verified

---

## Post-Migration

- [ ] `migration_changes.md` finalized with all changes
- [ ] Rollback plan documented
- [ ] Old target profile retained (for rollback capability)
- [ ] Team notified of migration completion
- [ ] CI/CD updated to use new target
- [ ] Jira tasks updated/closed (if using Wire/Atlassian)
- [ ] Performance baseline captured on new platform

---

## Sign-Off

| Role | Name | Date | Approved? |
|------|------|------|-----------|
| Migration Lead | | | |
| Data Engineer | | | |
| Analytics Engineer | | | |
| Stakeholder | | | |

---

## Notes

_Use this section for any migration-specific observations, known differences in behavior between platforms, or follow-up items._
