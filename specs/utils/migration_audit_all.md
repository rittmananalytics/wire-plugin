---
wire_schema: "1.0"
command: utility
artifact: migration_audit_all
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Run all platform migration audits in parallel using dynamic workflow (5 core audits + optional reverse ETL audit)

---

# Migration Audit All — Utility

## Purpose

Fans out all platform migration audit commands simultaneously using parallel subagents. Five core audits always run; a sixth (reverse ETL) runs automatically when `migration.reverse_etl_tool` is set in `status.md`. This reduces total wall-clock time from sequential hours to roughly the duration of the slowest individual audit.

## Arguments

`$ARGUMENTS` — the release folder path (required)

## Workflow

### Step 1: Confirm release type

Read `.wire/releases/$ARGUMENTS/status.md`. Confirm `release_type: platform_migration`. If not, stop.

Check `migration.reverse_etl_tool` — if set (e.g. `hightouch`), the reverse ETL audit will run as a sixth parallel subagent.

Confirm no audits are already complete unless the user explicitly wants to re-run them. List any already-complete audits.

### Step 2: Token cost confirmation

Present the following confirmation prompt — adjust the count and list based on whether reverse_etl_tool is set:

```
This command will launch [5|6] parallel audit subagents simultaneously:
  1. ingestion_audit       — Fivetran connector catalog
  2. db_object_audit       — Database object catalog (INFORMATION_SCHEMA query)
  3. security_audit        — IAM roles and policies catalog
  4. dbt_audit             — dbt project model catalog
  5. orchestration_audit   — Orchestration job catalog
  6. reverse_etl_audit     — Hightouch sync catalog [only if reverse_etl_tool is set]

Estimated token usage: HIGH (particularly for large warehouses or dbt projects).

How would you like to proceed?

A) Run all audits in parallel (fastest — recommended for most engagements)
B) Run audits sequentially instead (lower peak token usage — use for very large projects)
```

Wait for user choice.

**If option B (sequential)** is chosen:
Output the individual commands in order and stop:

```
Run each audit in sequence:

1. /wire:ingestion-audit-generate $ARGUMENTS
2. /wire:db-object-audit-generate $ARGUMENTS
3. /wire:security-audit-generate $ARGUMENTS
4. /wire:dbt-audit-generate $ARGUMENTS
5. /wire:orchestration-audit-generate $ARGUMENTS
[6. /wire:reverse-etl-audit-generate $ARGUMENTS   ← only if reverse_etl_tool is set]

When all audits are complete, run:
/wire:migration-inventory-generate $ARGUMENTS
```

### Step 3: Launch parallel audit subagents (option A)

Dispatch parallel subagents — always launch these five:

- Subagent 1: Follow `specs/migration/ingestion_audit/generate.md` for `$ARGUMENTS`
- Subagent 2: Follow `specs/migration/db_object_audit/generate.md` for `$ARGUMENTS`
- Subagent 3: Follow `specs/migration/security_audit/generate.md` for `$ARGUMENTS`
- Subagent 4: Follow `specs/migration/dbt_audit/generate.md` for `$ARGUMENTS`
- Subagent 5: Follow `specs/migration/orchestration_audit/generate.md` for `$ARGUMENTS`

If `migration.reverse_etl_tool` is set in `status.md`, also dispatch:
- Subagent 6: Follow `specs/migration/reverse_etl_audit/generate.md` for `$ARGUMENTS`

Each subagent writes its own output file and updates status.md independently.

### Step 4: Collect results

Wait for all subagents to complete. Report outcomes:

```
Parallel audit results:

Audit                 | Status   | Output file
----------------------|----------|-------------
ingestion_audit       | complete | audit/ingestion_audit.md
db_object_audit       | complete | audit/db_object_audit.md
security_audit        | complete | audit/security_audit.md
dbt_audit             | complete | audit/dbt_audit.md (+ dbt_audit.csv)
orchestration_audit   | complete | audit/orchestration_audit.md
reverse_etl_audit     | complete | audit/reverse_etl_audit.md  [if applicable]

All audits complete. Next steps:

1. Validate each audit:
   /wire:ingestion-audit-validate $ARGUMENTS
   /wire:db-object-audit-validate $ARGUMENTS
   /wire:security-audit-validate $ARGUMENTS
   /wire:dbt-audit-validate $ARGUMENTS
   /wire:orchestration-audit-validate $ARGUMENTS
   [/wire:reverse-etl-audit-validate $ARGUMENTS]

2. Review each audit with the team.

3. When all audits are approved:
   /wire:migration-inventory-generate $ARGUMENTS
```

If any subagent fails, report the failure and provide the individual command to retry:
```
orchestration_audit failed: [error detail]
Retry: /wire:orchestration-audit-generate $ARGUMENTS
```
