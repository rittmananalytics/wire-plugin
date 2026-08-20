---
description: Generate Fivetran connector migration runbook
argument-hint: <release-folder> [--wave id]
---

# Generate Fivetran connector migration runbook

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Execute ingestion connector migration via MCP server, or generate runbook if MCP unavailable
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

Follow `specs/utils/stale_artifact_check.md` with `artifact_id: ingestion_migration` and `artifact_file_path: migration/ingestion_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before creating any connectors, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  Do NOT modify, re-point, or delete any existing source connectors.
  Create new connectors pointing at the TARGET destination only.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not create connectors pointing to these):
  [list each production project ID]
```

If a tool call would modify an existing source connector, or create a connector pointing to a production project listed in `data_safety.production_projects`, stop immediately and report the conflict before proceeding.

---

# Ingestion Migration — Generate

## Purpose

Migrates every in-scope connector from the source ingestion platform to the target platform destination. When the relevant ingestion tool's MCP server is available, Wire executes the migration directly — creating new connectors and generating setup/connect card URLs for the user to enter credentials. A runbook is generated as a fallback only when no MCP server is reachable.

**Default behaviour**: always create new connectors for the target destination. Never edit or re-point an existing connector's destination — that risks interrupting the source pipeline during the parallel-run window.

## Ingestion tool connectivity map

A project may use multiple ingestion tools simultaneously. Each tool has its own connectivity method — MCP server, direct API call, or runbook-only. This table covers all tools the ingestion audit can surface:

| Ingestion tool | Connectivity method | Key probe | Fallback |
|---|---|---|---|
| Fivetran | MCP — `mcp__fivetran__` | `mcp__fivetran__get_account_info` | Runbook |
| RudderStack | MCP — `mcp__plugin_wire_rudderstack__` | `mcp__plugin_wire_rudderstack__user_details` | Runbook |
| Coupler.io | MCP — `mcp__claude_ai_Coupler_io__` | `mcp__claude_ai_Coupler_io__list-dataflows` | Runbook |
| Airbyte | API — `AIRBYTE_TOKEN` + `AIRBYTE_BASE` env vars | `GET $AIRBYTE_BASE/workspaces` | Runbook |
| Segment | API — `SEGMENT_TOKEN` + `SEGMENT_BASE` env vars | `GET $SEGMENT_BASE/sources` | Runbook |
| Stitch | *(no MCP or API — runbook only)* | — | Runbook |
| Custom / other | Check available MCP tools for a matching prefix | — | Runbook |

Handle each tool group separately. Never mix-apply one tool's MCP server to another tool's connectors.

## Prerequisites

- `target_setup review: approved`
- Target warehouse schemas exist (target_setup scripts executed)
- `migration/migration_batching.csv` exists — required only when running with `--wave`

## Flags

- `--wave <id>` — restrict this run to the connectors `migration/migration_batching.csv` assigns to this wave. Resolution is identical to `dbt-migration-generate`'s Step 1w: normalise the wave id (zero-padded `B01` or bare `1`, both accepted) Wave-id form and normalisation are the shared contract in `specs/utils/wave_resolution.md` (normative; accepts `2`, `B02`, `b2`, or the `W02` display form)., load `migration_batching.csv` (abort if missing: `[wire] No migration_batching.csv found — run /wire:migration-batching-generate $ARGUMENTS first.`), filter to rows where `batch_id` matches **and** `object_type == "connector"` (rows for other object types in the same wave belong to other migration commands). Cross-reference each matched row's `object_id` against `ingestion_audit.md`'s connector identifiers to pull the actual per-connector detail (`service_type`, `complexity`, `include_in_migration`, destination schema). Print the mandatory resolved-connector preview before proceeding, exactly as `dbt-migration-generate` Step 1w does. If no rows match the wave at all, abort: `[wire] No rows found for wave <id> in migration_batching.csv.` If rows match the wave but none are `connector` rows, print `[wire] Wave <id> has no connector objects — nothing to migrate for this command.` and stop cleanly (not an error).
- No flag — process every connector with `include_in_migration: true` in the ingestion audit (today's behaviour, unchanged).

When `--wave` is supplied, every output below is wave-labelled: the runbook (if the runbook fallback path is used) is written to `migration/ingestion_migration_runbook_{wave_id}.md` instead of the unscoped filename, and status.md tracks the wave under `wave` / `waves_complete` (Step 5) rather than treating the run as covering the whole ingestion scope.

## Inputs

- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md`
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv` — consumed only by `--wave` mode

## Workflow

### Step 1: Confirm prerequisites

Confirm `target_setup review: approved`. If not, stop with message.

### Step 1w: Resolve `--wave` (only when `--wave` is used)

Resolve the in-scope connector set per the **Flags** section above. This replaces "every connector with `include_in_migration: true`" everywhere below with the wave-resolved subset — the rest of the workflow is otherwise unchanged.

### Step 2: Pre-flight — identify all in-scope tools and check connectivity

Read `ingestion_audit.md`. Collect every distinct `service_type` or `ingestion_tool` that has at least one connector with `include_in_migration: true` (or, under `--wave`, at least one connector in the Step 1w-resolved set). This is the in-scope tool list for this run.

For each tool in the in-scope list, determine its connectivity status using the table above:

- **MCP tools** (Fivetran, RudderStack, Coupler.io): run the key probe call with a 10-second timeout. Interpret the result:
  - Probe succeeds → `CONNECTED — will execute via MCP`
  - Auth error (401/403) → `AUTH REQUIRED — re-authenticate via /mcp before proceeding`
  - Timeout or tool unavailable → `NOT CONFIGURED — will fall back to runbook`
- **API tools** (Airbyte, Segment): check whether the required env vars are set (`AIRBYTE_TOKEN`/`AIRBYTE_BASE` or `SEGMENT_TOKEN`/`SEGMENT_BASE`). If set, attempt a lightweight API call. Interpret:
  - Call succeeds → `CONNECTED — will execute via API`
  - 401 / missing env var → `NOT CONFIGURED — will fall back to runbook`
- **Runbook-only tools** (Stitch, custom/other): mark as `RUNBOOK ONLY` without probing.

Output the pre-flight table before starting any migration work:

```
Ingestion Pre-flight Check
════════════════════════════════════════════════════════════════

  Tool          Connectors in scope   Connectivity              Migration path
  ──────────    ───────────────────   ──────────────────────    ──────────────
  Fivetran      18                    ✅ Connected (MCP)         Direct execution
  RudderStack   4                     ✅ Connected (MCP)         Direct execution
  Coupler.io    2                     ⚠️  Auth required (MCP)    Blocked — re-auth first
  Segment       3                     ❌ Not configured (API)    Runbook fallback

Total in scope: 27 connectors
MCP/API executable: 22   Runbook fallback: 5   Blocked: 2
```

If any tool shows `AUTH REQUIRED`, stop and instruct the user to re-authenticate that tool (run `/mcp` in Claude Code and re-authenticate, or re-set the env var). Do not proceed past this step until no tool is in a blocked state.

Once all tools are either CONNECTED or RUNBOOK fallback (none blocked), output:

```
Pre-flight complete. Proceeding with migration.
  Direct execution: [tools]
  Runbook fallback: [tools]
```

Then continue to Step 3 for each CONNECTED tool and Step 4 for each fallback tool.

### Step 3: MCP-driven migration (primary path)

For each connector in scope (Step 1w's resolved set under `--wave`, otherwise every connector with `include_in_migration: true`) where an MCP server is available, working in order of ascending complexity (Low first):

1. **Identify the target destination**: use the MCP server's list/group call (e.g. `mcp__fivetran__list_groups`, `mcp__airbyte__list_destinations`) to find the destination that corresponds to the target warehouse, as named in the target setup.

2. **Create a new connector**: call the MCP server's create connection tool (e.g. `mcp__fivetran__create_connection`, `mcp__airbyte__create_connection`) with:
   - The same service/connector type as the source connector
   - The target destination identifier
   - Schema / schema prefix matching the source connector (as mapped in the ingestion audit)
   - Do **not** modify or re-point the source connector — it stays active for the parallel run

3. **Generate a setup link**: call the MCP server's connect card or setup URL tool (e.g. `mcp__fivetran__create_connect_card`). Record the returned URL. For tools without a connect card API, use whatever credential-entry URL the MCP server provides.

4. **Present the setup URL** to the user immediately with clear instructions: "Open this link to enter credentials for `<connector_name>`. Once saved, the initial sync will start automatically."

5. **Track completion**: after the user confirms credentials entered (or after a reasonable wait), call the MCP server's connection state tool to confirm the connector reaches `connected` / `active` state. Note the result.

6. **Credential rotation checklist**: for this connector, note:
   - Service accounts or API keys that need new target-platform credentials
   - IP allowlists that need updating for the target platform

For High-complexity connectors: add a note listing common failure modes and resolution steps specific to that connector type.

Write a per-connector status summary as each one completes.

### Step 4: Runbook fallback (MCP unavailable)

If no MCP server is reachable for a given set of connectors, generate a step-by-step runbook for those connectors.

**Output location**: `.wire/releases/$ARGUMENTS/migration/ingestion_migration_runbook.md` — or `migration/ingestion_migration_runbook_{wave_id}.md` when run with `--wave`.

For each connector in scope (Step 1w's resolved set under `--wave`, otherwise every connector with `include_in_migration: true`):

1. **Identify destination mapping**: map the source destination schema to its target platform equivalent (from the target setup DDL)
2. **Connector steps**: always document **new connector creation** steps — never "edit destination" on the existing connector
3. **Activation steps**: source connector stays active; new target connector is created, activated, synced, and equivalency-checked
4. **Credential rotation**: list service accounts, API keys, and IP allowlist changes needed

For High-complexity connectors: include an expanded diagnostic section with common failure modes.

Structure:
1. Pre-flight checklist
2. Per-connector migration steps (Low complexity first)
3. Credential rotation checklist
4. Post-migration validation steps
5. Source connector deactivation procedure (deferred to cutover phase)

### Step 5: Update status

```yaml
artifacts:
  ingestion_migration:
    generate: complete
    method: mcp_executed | runbook_generated
    file: migration/ingestion_migration_runbook.md   # runbook path only; omit for MCP path
    generated_date: "{{TODAY}}"
    connectors_migrated: N
    connectors_pending_credentials: N   # connectors with connect card URL not yet confirmed
    wave: "B01"                        # set only when run with --wave; the wave id just processed
    waves_complete: ["B01"]            # set only when run with --wave; accumulates across runs
```

### Step 6: Output next command

```
/wire:ingestion-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/ingestion_migration_runbook.md` (runbook fallback only; `_{wave_id}` suffix when run with `--wave`)
- Per-connector connect card URLs and status summary (MCP path, printed to console)
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact_id, `Ingestion Migration` as artifact_name, and the `file` value from `artifacts.ingestion_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `ingestion_migration` as artifact, `generate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
