---
description: Validate Fivetran connections against the approved pipeline design
argument-hint: <project-folder>
---

# Fivetran Pipeline Validate

## Purpose

Verify that every Fivetran connection documented in `pipeline_connections.md` is correctly configured, healthy, and matches the approved pipeline architecture. Produces a PASS/FAIL checklist.

## Called by

`wire/specs/development/pipeline/validate.md` when `pipeline_tool == fivetran`

## Workflow

### Step 1: Read Inputs

1. Read `.wire/<project_id>/development/pipeline/pipeline_connections.md` — get all `connection_id` values
2. Read `.wire/<project_id>/design/pipeline_architecture.md` — get expected sources, schemas, sync frequencies, and in-scope tables
3. Verify the count of expected connections matches the count in `pipeline_connections.md`

### Step 2: Per-Connection Health Checks

For each connection listed in `pipeline_connections.md`:

**Check 1 — Setup state**
Call `mcp__fivetran__get_connection_details`.
- Expected: `status.setup_state == "connected"`
- Failure: `"broken"`, `"incomplete"`, `"paused"` → FAIL (Critical)

**Check 2 — Last sync**
From `get_connection_details`, check `succeeded_at`:
- If `succeeded_at` is null and `failed_at` is also null: connection has never synced → WARN (at least one sync should have run since generate)
- If `failed_at` is more recent than `succeeded_at`: last sync failed → FAIL (Critical), include `failed_reason`

**Check 3 — Setup tests pass**
Call `mcp__fivetran__run_connection_setup_tests` as a supplementary check.
- All tests must pass → if any fail: FAIL (Critical)
- If the tool returns `400 Request body must not be empty`: this is a known MCP wrapper bug — treat as inconclusive (not a failure). Health signal from Check 1 (`setup_state`) takes precedence.

**Check 4 — Schema matches design**
Call `mcp__fivetran__get_connection_schema_config`.
- Verify `schema` prefix matches what is specified in the pipeline design
- Verify in-scope tables are `enabled: true`
- Verify out-of-scope tables are `enabled: false`
- Any in-scope table that is disabled → FAIL (Major)
- Any out-of-scope table that is enabled → WARN (Info)

**Check 5 — PII columns hashed**
For each column flagged for hashing in the pipeline design:
Call `mcp__fivetran__get_connection_column_config` and verify `hashed: true`.
- Missing hash on a PII column → FAIL (Critical — data governance risk)

**Check 6 — Sync frequency**
From `get_connection_details`, check `sync_frequency`.
- Must match the cadence specified in the pipeline design (within one tier)
- Mismatch → WARN (Major)

**Check 7 — Sync not paused**
From `get_connection_details`, check `paused`.
- `paused: true` → FAIL (Major)

### Step 3: Destination Health Check

Call `mcp__fivetran__run_destination_setup_tests` on the destination group.
- Any failure → FAIL (Critical — all connections depend on this)

### Step 4: Generate Validation Report

```
## Pipeline Validation: [Project Name]

**Tool**: Fivetran
**Status**: PASS | FAIL
**Validated**: [date]

### Destination

| Check | Status | Notes |
|-------|--------|-------|
| Destination setup tests | ✅ / ❌ | |

### Connection Results

#### [Source System Name] (`[connection_id]`)

| Check | Status | Notes |
|-------|--------|-------|
| Setup state: connected | ✅ / ❌ | [state] |
| Last sync succeeded | ✅ / ⚠️ / ❌ | [succeeded_at or failed_reason] |
| Setup tests pass | ✅ / ❌ | |
| In-scope tables enabled | ✅ / ❌ | [list any disabled in-scope tables] |
| Out-of-scope tables disabled | ✅ / ⚠️ | [list any enabled out-of-scope tables] |
| PII columns hashed | ✅ / ❌ | [list any unhashed PII columns] |
| Sync frequency correct | ✅ / ⚠️ | [expected vs actual] |
| Not paused | ✅ / ❌ | |

[Repeat for each connection]

### Summary

| Severity | Count |
|----------|-------|
| Critical failures | [N] |
| Major warnings | [N] |
| Info | [N] |

### Issues Requiring Action

[List each FAIL with connection_id, check name, and remediation suggestion]
```

### Step 5: Update Status

If all Critical checks pass:
```yaml
pipeline:
  validate: pass
  validated_date: <today>
```

If any Critical check fails:
```yaml
pipeline:
  validate: fail
  validated_date: <today>
  validation_issues: "[summary of critical failures]"
```

### Remediation Guidance

For common failures:

| Failure | Likely cause | Fix |
|---------|-------------|-----|
| `setup_state != connected` | Wrong credentials or OAuth token expired | Call `mcp__fivetran__modify_connection` to update config/auth, then re-run setup tests |
| Last sync failed | Source unavailable, schema change, or permission error | Check `failed_reason` in connection details; fix at source |
| PII column not hashed | Column was added after initial config | Call `mcp__fivetran__modify_connection_column_config` with `hashed: true` |
| In-scope table disabled | Table added to conceptual model after initial config | Call `mcp__fivetran__modify_connection_table_config` with `enabled: true` |
| Destination tests fail | Destination credentials changed or permissions revoked | Call `mcp__fivetran__modify_destination` to update credentials |
