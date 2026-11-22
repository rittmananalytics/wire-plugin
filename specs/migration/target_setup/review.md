---
wire_schema: "1.0"
command: review
artifact: target_setup
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: target_setup
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Safety-gated approval before writing to target platform

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Target Setup — Review

## Purpose

Safety-gated review before any DDL is executed against the target platform. Once approved, the team has authorisation to run the generated scripts and activate the target warehouse.

## Prerequisites

- `migration/target_setup_scripts/` with `validate: pass`

## SAFETY GATE

This command writes to an external system. Before proceeding, the reviewer must explicitly confirm each of the following:

```
⚠️  SAFETY GATE — Target Platform Setup

The following actions will be authorised by approving this review:
  - CREATE DATABASE / SCHEMA statements will be executed on the target platform
  - CREATE TABLE statements for N tables will be executed
  - GRANT statements will be executed to configure roles and permissions
  - CREATE FUNCTION statements for N UDFs will be executed (if 05_udfs.sql exists)

No data is moved at this step. Fivetran connectors are NOT yet activated.

Please confirm:
[ ] I have reviewed the DDL scripts in migration/target_setup_scripts/
[ ] The target platform credentials are correctly configured
[ ] The target platform is a non-production environment OR
    a production environment with explicit client authorisation
[ ] Any TODO items in the DDL have been addressed or formally deferred
[ ] Each UDF in the "UDF redesign decisions" section has an agreed target
    approach (BigQuery ML / Vertex AI / remote UDF / in-model rewrite), or none exist
[ ] A rollback plan is in place (drop all created objects if target setup fails)
```

Ask the reviewer to confirm all checkboxes before proceeding.

If any checkbox is unchecked, stop and output:
```
Safety gate not cleared. Address the unchecked items and re-run:
/wire:target-setup-review $ARGUMENTS
```

## Workflow

### Step 1: Present scripts for review

Display the MANIFEST.md contents and summarise:
- Total schemas, tables, views, security objects, and UDFs to be created
- Any TODO items still open
- The **UDF redesign decisions** section, if present — each UDF with no direct target equivalent and the target approach proposed for it. These are architecture decisions the reviewer must sign off before the affected models can be translated.
- Rollback procedure from migration strategy

### Step 2: Safety gate confirmation

Present the safety gate checklist. Wait for explicit confirmation of all items.

### Step 3: Record decision

Append:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Safety gate confirmation
All checklist items confirmed by: {{REVIEWER_NAME}}

### Execution instructions
Scripts should be executed in this order:
1. 01_schemas.sql
2. 02_tables.sql
3. 03_views_stub.sql (manual TODOs only)
4. 04_security.sql
5. 05_udfs.sql (if present — deploys the batch-zero UDF layer before model batch 1)
```

### Step 4: Update status

```yaml
artifacts:
  target_setup:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 5: Output next command

If approved:
```
/wire:ingestion-migration-generate $ARGUMENTS
```
