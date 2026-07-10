---
description: Synthesise all audits into unified catalogue with dependency graph
argument-hint: <release-folder>
---

# Synthesise all audits into unified catalogue with dependency graph

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Synthesise all audits into a unified catalogue with dependency graph
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_inventory` and `artifact_file_path: migration/migration_inventory.md` before proceeding.

---

# Migration Inventory — Generate

## Purpose

Synthesises all approved audits into a single unified migration inventory. The five core audits (ingestion, db_object, security, dbt, orchestration) are always required. The reverse ETL audit is required when `migration.reverse_etl_tool` is set in `status.md`. The inventory is the canonical scope document — every object that will be migrated, its complexity, its migration approach, and its dependencies. It is the primary input to migration strategy and the reference point for all subsequent generate commands.

## Prerequisites

The following five audits must always have `review: approved`:
- `ingestion_audit`
- `db_object_audit`
- `security_audit`
- `dbt_audit`
- `orchestration_audit`

If `migration.reverse_etl_tool` is set in `status.md`, this audit must also be `review: approved`:
- `reverse_etl_audit`

If any required audit is not yet approved, output the list of incomplete audits and stop:
```
The following audits are not yet approved — complete them before generating the inventory:
[list of pending audits]

Run all audits in parallel: /wire:migration-audit-all $ARGUMENTS
```

## Inputs

- All required audit files under `.wire/releases/$ARGUMENTS/audit/`
- `.wire/releases/$ARGUMENTS/status.md`
- **Optional** `migration.connector_alias_patterns` in `status.md` — a list of regex or affix patterns to strip from connector/object identifiers and model `source()` references before matching them in Step 2 (see the alias-normalization note there). Examples: per-market prefixes such as `uk_`/`de_`/`es_`, or connector-suffix short-codes such as `__eu1`. These are documented examples, not a fixed list — set whatever patterns match the engagement's actual naming convention. If unset, Step 2 matches identifiers literally, as before.

## Workflow

### Step 1: Load all audit outputs

Read each approved audit file. Extract:
- Ingestion audit: connector list with complexity and migration approach
- DB object audit: object catalog with type, volume tier, migration approach, feature tags
- Security audit: role and policy inventory
- dbt audit: model catalog with complexity, batch number, feature tags (from CSV)
- Orchestration audit: job inventory
- Reverse ETL audit (if present): sync catalog with migration approach, warehouse object dependencies, Lightning engine flags

### Step 2: Cross-reference and deduplicate

Identify objects that appear in multiple audits and link them:
- Each ingestion connector/source writes to one or more schemas → link to db objects in those schemas
- dbt models reference source tables → link dbt models to db objects
- Orchestration jobs run dbt commands → link jobs to dbt models
- Service accounts in security audit → link to ingestion connectors/sources and orchestration jobs
- Hightouch syncs reference warehouse objects → link each sync to the db objects and dbt models it reads from (using the `warehouse_objects` field from the reverse ETL audit)
- Hightouch `dbtModel`-type syncs → link to the specific dbt models in the dbt audit

**Alias normalization before matching.** A regionalized or multi-tenant connector often carries an alias its consuming model's `source()` call doesn't literally repeat — a UK-market connector suffixed `_uk`, a German instance prefixed `de_`, a connector-suffix short-code like `__eu1`. Matched as bare strings, that alias makes a connector with a real downstream consumer look orphaned, which is exactly the kind of false orphan Fix W-7 (`migration_batching`'s `NO-DEP` bucket) exists to catch honestly rather than paper over. Before linking a connector or db-object identifier to a model's `source()` reference, strip any pattern listed in `migration.connector_alias_patterns` (see Inputs) from both sides, then match on the normalized form. If no patterns are configured, match literally as today — this normalization is additive and engagement-specific, never a fixed list of one client's naming scheme.

### Step 3: Build the dependency graph

Construct a directed dependency graph where:
- Edges point from dependency to dependent (data flows downstream)
- Node types: `connector`, `table`, `view`, `dbt_model`, `job`, `role`, `reverse_etl_sync`, `reverse_etl_destination`

The graph now spans the full data flow: ingestion sources → warehouse objects → dbt models → reverse ETL syncs → SaaS destinations.

Output the graph in two formats:
1. Text adjacency list (always)
2. Mermaid diagram (if total nodes ≤200)

The Mermaid diagram should represent the six layers left-to-right:
```
[Ingestion] → [Raw Tables] → [dbt Models] → [Warehouse Views/Tables] → [Hightouch Syncs] → [Destinations]
```

### Step 4: Calculate migration effort estimate

For each object type, apply effort weights:

| Object type | Complexity | Est. hours |
|------------|-----------|-----------|
| Ingestion connector/source | Low | 0.5 |
| Ingestion connector/source | Medium | 2 |
| Ingestion connector/source | High | 4 |
| dbt model | Simple | 0.25 |
| dbt model | Moderate | 1 |
| dbt model | Complex | 3 |
| View (translate) | Low feature count | 0.5 |
| View (translate) | High feature count | 2 |
| Security object | recreate | 0.1 |
| Security object | translate/evaluate | 1 |
| Orchestration job | recreate | 0.5 |
| Orchestration job | translate/evaluate | 2 |
| Hightouch sync | repoint (Low) | 0.5 |
| Hightouch sync | rewrite_model (Medium) | 2 |
| Hightouch sync | rebuild (High) | 8 |
| Lightning schema provisioning | per workspace | 0.5 |

Sum the estimates by phase and produce a total effort estimate.

### Step 5: Write the inventory

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_inventory.md`

Use the template at `TEMPLATES/migration/migration_inventory.md`. Include:
- Executive summary: total objects, total effort estimate, migration duration estimate (assuming 6 hours/day productive migration work)
- Phase breakdown: audit → strategy → ingestion → dbt batches → orchestration → reverse ETL → equivalency → cutover
- Unified object catalog (linked across audits)
- Dependency graph
- Risk summary: count of High-complexity and evaluate objects; count of rebuild-type reverse ETL syncs
- Recommended phasing approach — note that reverse ETL syncs cannot be re-pointed until their dependent warehouse objects and dbt models are migrated in earlier phases

### Step 6: Update status

```yaml
artifacts:
  migration_inventory:
    generate: complete
    file: migration/migration_inventory.md
    generated_date: "{{TODAY}}"
    total_objects: N
    estimated_hours: N
    reverse_etl_syncs: N   # 0 if not applicable
```

### Step 7: Output summary

Print: total objects, effort estimate, recommended migration duration, and next command:

```
/wire:migration-inventory-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_inventory.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_inventory` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_inventory` as artifact_id, `Migration Inventory` as artifact_name, and the `file` value from `artifacts.migration_inventory` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_inventory` as artifact, `generate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

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
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
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
