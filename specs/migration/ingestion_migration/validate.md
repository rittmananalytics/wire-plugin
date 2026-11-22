---
wire_schema: "1.0"
command: validate
artifact: ingestion_migration
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
  - artifact: ingestion_migration
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate ingestion migration — MCP-executed connectors or runbook
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Ingestion Migration — Validate

## Flags

- `--wave <id>` — validate only the connectors `migration/migration_batching.csv` assigns to this wave. Resolution is identical to `ingestion-migration-generate`'s Step 1w. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative). Every check below reads "in scope" as this resolved connector set instead of every `include_in_migration: true` connector.

## Validation Checks

Read `status.md` to determine `method: mcp_executed | runbook_generated` before running checks. Also read the ingestion audit to identify which MCP server prefix applies (Fivetran → `mcp__fivetran__`, Airbyte → `mcp__airbyte__`, etc.) — use the correct prefix for all MCP calls below. Under `--wave`, read the wave-labelled runbook (`ingestion_migration_runbook_{wave_id}.md`) for the runbook fallback path instead of the unscoped file.

### MCP-executed path

**Check 1 — All in-scope connectors created**
For each connector with `include_in_migration: true` in the ingestion audit, use the ingestion tool's MCP list call (e.g. `mcp__fivetran__list_connections_in_group`, `mcp__airbyte__list_connections`) on the target destination and confirm a matching new connector exists.
PASS/FAIL with missing connectors listed.

**Check 2 — Connectors reached connected/active state**
Use the MCP server's state/status call (e.g. `mcp__fivetran__get_connection_state`, `mcp__airbyte__get_connection`) for each migrated connector. All should show `connected` or `active` (or `syncing` for an in-progress initial sync). Any in a broken or unconfigured state are flagged.
PASS/FAIL with broken connectors listed.

**Check 3 — Source connectors still active**
Use the MCP state call for each source connector. All should still be active — none paused or deleted.
PASS/FAIL.

**Check 4 — Schema mapping correct**
For each new connector, confirm the schema / schema prefix matches the expected target schema from the ingestion audit destination mapping.
PASS/FAIL with mismatches listed.

**Check 5 — Source deactivation deferred to cutover**
Confirm no source connectors were paused or deleted during migration.
PASS/FAIL.

### Runbook fallback path

**Check 1 — All in-scope connectors in runbook**
The count of connectors in the runbook matches the count of `include_in_migration: true` connectors in the ingestion audit.
PASS/FAIL.

**Check 2 — Each connector has destination mapping**
Every connector step includes the source destination schema and its target platform equivalent.
PASS/FAIL with gaps.

**Check 3 — All connector steps describe new connector creation (not destination editing)**
No connector step instructs the user to edit or re-point an existing connector's destination.
PASS/FAIL.

**Check 4 — High-complexity connectors have expanded diagnostic sections**
Every High-complexity connector has a diagnostic section in the runbook.
PASS/FAIL.

**Check 5 — Credential rotation checklist present**
The runbook includes a credential rotation section listing all service accounts and API keys.
PASS/FAIL.

**Check 6 — Source deactivation deferred to cutover**
The runbook explicitly notes that source connectors are NOT deactivated during ingestion migration — only during the cutover phase.
PASS: Note present.
FAIL: Deactivation steps found in ingestion runbook (should be moved to cutover).

**Check 7 — Post-migration validation steps present**
The runbook includes equivalency check steps to run after each connector's initial sync completes.
PASS/FAIL.

### Update status

```yaml
artifacts:
  ingestion_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    wave_validate:               # set only when run with --wave, keyed by wave id
      B01: pass | fail
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact_id, `Ingestion Migration` as artifact_name, and the `file` value from `artifacts.ingestion_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `ingestion_migration` as artifact, `validate` as action.
