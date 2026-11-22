---
wire_schema: "1.0"
command: validate
artifact: requirements
domain: requirements
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: requirements
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate requirements specification for completeness and clarity
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Requirements Validation Command

## Purpose

Validate a generated requirements specification against completeness criteria. Checks for required sections, clear acceptance criteria, and feasibility.

## Usage

```bash
/wire:requirements-validate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must exist at `<project>/requirements/requirements_specification.md`

## Workflow

### Step 1: Locate Project & Requirements

**Process**:
1. Parse `$ARGUMENTS` for project identifier
2. Search `.wire/` for matching folder
3. Verify `requirements/requirements_specification.md` exists

**If requirements not found**:
```
Error: No requirements found for project "[folder]"

Run `/wire:requirements-generate [folder]` first to generate requirements.
```

### Step 2: Run Validation Checks

**Validation Checklist**:

| Check | Criteria | Severity |
|-------|----------|----------|
| Executive Summary | Present and non-empty | Critical |
| Functional Requirements | At least 3 requirements with acceptance criteria | Critical |
| Non-Functional Requirements | Performance, security, availability defined | Major |
| Data Sources | All data sources identified with owners | Critical |
| Deliverables | All SOW deliverables documented | Critical |
| Acceptance Criteria | Each deliverable has clear acceptance criteria | Critical |
| Timeline | Milestones with dates | Major |
| Stakeholders | Roles and responsibilities defined | Major |
| Out of Scope | Explicitly documented | Major |
| Assumptions | Dependencies documented | Major |
| Reference legibility | Every reference code (FR-n, NFR-n, D-n) is defined at first use or resolved in a Reference key table — run the `reference_legibility` check per `specs/utils/reference_legibility.md` | Major |

**Severity Levels**:
- **Critical**: Must pass for validation to succeed
- **Major**: Should pass, will be flagged
- **Info**: Advisory only

### Step 3: Generate Validation Report

**Output Format**:

```
## Requirements Validation: [PROJECT_NAME]

**Status:** PASS | FAIL
**File:** .wire/[folder]/requirements/requirements_specification.md

### Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Executive Summary | ✅ | |
| Functional Requirements | ✅ | 12 requirements defined |
| Non-Functional Requirements | ✅ | |
| Data Sources | ✅ | 3 sources identified |
| Deliverables | ✅ | 5 deliverables (D1-D5) |
| Acceptance Criteria | ✅ | All deliverables have criteria |
| Timeline | ✅ | 2-week timeline with milestones |
| Stakeholders | ✅ | All roles defined |
| Out of Scope | ✅ | Documented |
| Assumptions | ⚠️ | Only 2 assumptions - consider adding more |
| Reference legibility | ✅ | reference_legibility: all 14 codes defined at first use or in the Reference key |

### Issues to Address

None - requirements are complete and ready for review.

### Next Steps

1. **Review requirements with stakeholders**: `/wire:requirements-review [folder]`
2. After approval, proceed to design: `/wire:pipeline_design-generate [folder]`
```

**If FAIL**:
```
### Issues to Address

**Critical Issues:**
- [ ] Missing data source owners
- [ ] Deliverable D3 lacks acceptance criteria

**Major Issues:**
- [ ] Performance requirements not quantified
- [ ] No timeline milestones defined

Fix these issues and re-run validation.
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.requirements section:
   ```yaml
   requirements:
     generate: complete
     validate: pass | fail
     review: not_started
     validated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `requirements`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Requirements Not Generated

If requirements file doesn't exist:
```
Error: Requirements not found

Generate requirements first: /wire:requirements-generate [folder]
```

### Partially Complete

If some critical checks fail:
- Set validate status to `fail`
- List all issues
- Suggest fixes
- User must regenerate or manually fix, then re-validate

## Output

This command:
- Validates requirements completeness
- Updates `status.md` with validation results
- Provides actionable feedback if issues found
