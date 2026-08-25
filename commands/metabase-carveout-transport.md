---
description: Transport signed-off carve-out cards and dashboards onto the separately-hosted tenant Metabase instance: executes the validated plan (id and SQL-text rewrites), dependency-ordered, idempotent by recorded target id
argument-hint: <release-folder> [--target-instance-url url] [--collection id] [--dashboard id] [--dry-run]
---

# Transport signed-off carve-out cards and dashboards onto the separately-hosted tenant Metabase instance: executes the validated plan (id and SQL-text rewrites), dependency-ordered, idempotent by recorded target id

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
description: Transport signed-off carve-out cards and dashboards onto the separately-hosted tenant Metabase instance, executing the validated transport plan (id-rewrites plus SQL-text rewrites), dependency-ordered, idempotent by recorded target id
argument-hint: <release-folder> [--target-instance-url <url>] [--collection <id> | --dashboard <id>] [--dry-run]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_carveout_transport` and `artifact_file_path: migration/metabase_carveout_transport_manifest.csv` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command CREATES objects on the tenant's target Metabase instance.
Three things it never does:

  1. It never writes to the source instance. Source access is read-only:
     serialization export or GET, nothing else.
  2. It never edits or deletes an existing object on the target instance.
     Transport is additive: it creates collections, cards, and dashboards,
     and it stops rather than overwrite.
  3. It never transports an unsigned row. The metabase-carveout-review
     sign-off is the write authorisation, row by row.

Source instance (read-only):  MB_HOST
Target instance (writes):     MB_TARGET_HOST
```

If `MB_TARGET_HOST` resolves to the same instance as `MB_HOST`, stop: transport moves objects between two independently-hosted deployments, and the same-instance cases are already covered by the carve-out's own layer paths. Report the conflict before creating anything.

---

# Metabase Carve-out: Transport

## Purpose

The carve-out triad decides what moves and how each card becomes tenant-only; nothing then created those objects on a second Metabase application (#203). `metabase-migration`'s cutover repoints a database connection inside one app, and the carve-out's layer paths (sandboxing, warehouse view, dashboard parameter, card edit) all assume the cards stay where they are. On a live tenant carve-out the target was a brand-new, separately-provisioned Metabase deployment, and no command could put a card there.

This command is the transport mechanic, deliberately separate from the layer decision so the decision and the mechanic stay separately testable: it takes the signed-off manifest from `metabase-carveout-review` as its worklist, exports each object's carved definition from the source instance, rewrites the ids that do not survive an instance boundary plus the SQL-text project references the plan maps (#221), and creates the object on the target instance. It decides nothing about tenant scoping; that was decided at generate and adjudicated at review.

From #221 the transport is the write step of a plan/validate/write pipeline: `metabase-carveout-transport-generate` produces the complete rewrite plan as a dry-run artifact, `metabase-carveout-transport-validate` re-derives the SQL scan independently and checks every rewrite, and this command executes only a plan the validate has passed. The rewrite is mechanical once the database mapping is confirmed, so the plan gets deterministic validation, not a second human sign-off: the review approval remains the only write authorisation.

## Prerequisites

- `migration.scope == tenant_carveout`
- `metabase_carveout review: approved`. If not, stop: no object is transported and every worklist row is recorded `not_attempted` with reason `review_not_approved`. The manifest sign-off is the write authorisation, exactly as it gates the carve itself.
- `migration/metabase_carveout_manifest.csv` present, with rows at `signed_off` or later
- Target instance credentials present as environment variables: `MB_TARGET_HOST` and `MB_TARGET_API_KEY` (write-scoped). Source reads use the audit's `MB_HOST` + `MB_API_KEY`. Credentials are never written into any file this command produces.
- `migration/metabase_db_mapping.csv` confirmed (Step 2)
- `migration/metabase_carveout_transport_plan.csv` present, with `metabase_carveout_transport_plan validate: pass` in status.md. The command refuses to run against a plan the validate has not passed, a plan changed after its pass (compare the plan's mtime to `validated_date`), or a plan older than the manifest it was generated from (compare the plan's mtime to the manifest's): stop with reason `plan_stale` and re-run `metabase-carveout-transport-generate` then `metabase-carveout-transport-validate`. Nothing is created against an unvalidated or stale plan.

## Flags

- `--target-instance-url <url>`: must equal `MB_TARGET_HOST` when both are set. A mismatch is a hard stop naming both values: it means the consultant and the environment disagree about which instance receives writes.
- `--collection <id>` / `--dashboard <id>`: narrows within the signed-off set, resolved the same way as `metabase-carveout-generate` Step 1 (a dashboard resolves to its deduped card set).
- `--dry-run`: seed or refresh the transport manifest, print the per-object plan (transport action, mapped database id, dependency position), and create nothing. The full dry-run artifact, including the SQL-text rewrite mapping, is `metabase-carveout-transport-generate`'s plan; this flag is a quick print of the same worklist.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_manifest.csv`: the signed-off worklist
- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`: object graph (snippets, card references), reverse index, collection tree, permission groups
- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_transport_manifest.csv`: prior transport state, when it exists (idempotency record)
- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_transport_plan.csv`: the validated rewrite plan from `metabase-carveout-transport-generate`
- `.wire/releases/$ARGUMENTS/status.md`: scope, tenant project, target instance

## Workflow

### Step 1: Confirm the gate and derive the worklist

Confirm `metabase_carveout review: approved`; stop with the rule above if not. Then derive one worklist row per carve-out manifest row in scope, in this order per row:

1. **Row not signed off** (`status: proposed`): `not_attempted`, reason `row_not_signed_off`. Only signed rows are ever transported, mirroring the carve's own rule.
2. **`action: remove_dashcard`**: `not_attempted`, reason `removed_no_tenant_data`. The card has no tenant data and must never appear on the tenant instance; its dashboards are assembled without it.
3. **Already transported**: the transport manifest records a `target_id` for this object from a prior run: `skipped_duplicate`, reason `already_transported`. Matched by the recorded id, confirmed with a GET against that id on the target, never matched by name. A name match proves nothing: two instances can each hold a "Revenue by month" that are different cards.
4. **`transport_action: skip_duplicate`**: the consultant has marked the object as already existing on the target through another channel (a restore, a prior serialization import). The row must carry the consultant-recorded target id: with one, `skipped_duplicate`, reason `consultant_recorded_target`; without one, `not_attempted`, reason `skip_duplicate_missing_target_id`, because a dashboard cannot remap a dashcard onto an id nobody recorded.
5. **Everything else**: `transport_action: duplicate`, queued for Steps 3 and 4.

`duplicate` and `skip_duplicate` are the closed transport-action vocabulary. Any other value is an error naming the value and the object, never a fall-through to creating something.

If the transport manifest is absent but the target instance already holds cards or dashboards, stop and reconcile with the consultant before running: without the recorded ids there is no safe way to tell a prior transport from unrelated content, and guessing by name is the exact failure this manifest exists to prevent.

### Step 2: Confirm the database mapping

Every card carries a `dataset_query.database` id that is meaningless on the target instance. Re-read `migration/metabase_db_mapping.csv`, normally confirmed at plan time (`metabase-carveout-transport-generate` Step 2), writing it here only if the plan pipeline has not:

```
source_database_id, source_database_name, source_project,
target_database_id, target_database_name, target_project, confirmed
```

Populate the source side from the audit and the target side from the target instance's database list, then **present the table to the consultant and require `confirmed: yes` per row** before any card transports. A card whose source database id has no confirmed mapping row is `not_attempted`, reason `missing_db_mapping`. Never map by name: a target database named like the source one is a hint for the consultant, not a mapping.

### Step 3: Transport in dependency order

An object cannot be created before the objects it references exist on the target. The order is fixed:

1. **Collections**: the collection tree for the in-scope objects, parents before children.
2. **Permission groups and sandboxing policies**: for `sandboxing`-layer card groups, create the permission group and apply the manifest's policy spec (group, table, filter expression) on the target before any of that group's cards. A group whose policy cannot be created blocks its cards: each is `not_attempted`, reason `sandboxing_policy_missing`, because an unsandboxed card on a shared-warehouse target shows other tenants' rows.
3. **Snippets, then leaf cards, then referencing cards**: the same object-graph ordering as `metabase-migration` Step 3b; a `{{snippet: name}}` or `{{#id-name}}` reference must resolve on the target before its consumer is created.
4. **Dashboards last**: a dashboard is assembled only when every surviving card (the signed-off set minus `remove_dashcard` rows) holds a target id, from this run, a prior run, or a consultant-recorded `skip_duplicate` id. If any surviving card is `failed` or `not_attempted`, the dashboard is `not_attempted`, reason `cards_incomplete`: a partially-assembled dashboard on the tenant instance reads as done and is not. A dashboard whose surviving card set is empty is `not_attempted`, reason `no_surviving_cards`; flag it to the consultant rather than create an empty shell.

### Step 4: Create each object, ids rewritten

For each `duplicate` card, export the **carved definition** (the applied decoy copy where the row is `applied`/`validated`; for a `signed_off` row not yet applied, the source definition with the manifest's signed-off transformation applied in flight; never a filter re-derived from the registry at transport time, the reviewed one is the one that ships) and rewrite before `POST`:

1. **`dataset_query.database`**: the confirmed target database id from Step 2.
2. **Template tags and field filters**: field ids from the source database do not survive the boundary; remap each against the target database's field metadata, recorded per tag in the transport manifest, the same surface rule as `metabase-migration` Step 3b.
3. **Snippet and card references**: rewritten to the target ids created in Step 3's ordering.
4. **Collection id**: the target collection created in Step 3.
5. **SQL-text rewrites** (#221): apply the plan's `sql_table_reference` rows for this card. Each fully-qualified `project.dataset.table` reference to a source/shared project is rewritten source project to target project exactly as the plan maps it (`rewrite` rows), or left as it is (`no_change_needed` rows, reason recorded at plan time). A reference found at write time that the plan does not carry is a hard stop, reason `plan_stale`, never an improvised rewrite: the plan was validated, an unplanned rewrite was not. Without this rewrite a repointed connection changes nothing, and the transported card keeps reading the source project's data while reporting `transported`.

For each `duplicate` dashboard: create it, add the surviving dashcards by target card id, and remap the dashboard's filter parameter mappings to the target database's field ids; `dashboard_parameter`-layer dashboards carry the tenant parameter and its per-dashcard mappings exactly as signed off.

Per-object outcomes are the closed set: `transported` (created; source id and target id recorded), `skipped_duplicate` (already on the target, by recorded id), `failed` (the create or a required remap errored; the reason is the named error, and the object can be retried on a re-run because no target id was recorded), `not_attempted` (never tried; the reason names why, per Steps 1 to 3). Every non-`transported` row carries its reason; a blank reason is itself a defect.

### Step 5: Write the transport manifest

**Output location**: `.wire/releases/$ARGUMENTS/migration/metabase_carveout_transport_manifest.csv`

```
object_type, source_id, name, layer_decision, transport_action,
source_database_id, target_database_id, target_id, outcome, reason,
tag_remaps, transported_date
```

One row per in-scope card and dashboard, plus one per created collection. The `source_id -> target_id` pairs are the durable record: re-runs key on them (Step 1 rule 3), and `metabase-equivalency-validate` resolves each card's target copy through them. The manifest is upserted, never rewritten from scratch, so a killed run resumes where it stopped.

Update register rows where the register exists (`object_type: metabase_card` / `metabase_dashboard`, `origin: carveout`): record the target instance and target id in `notes` for each `transported` object. Skip silently if the register does not exist.

### Step 6: Update status

```yaml
artifacts:
  metabase_carveout_transport:
    generate: complete
    file: migration/metabase_carveout_transport_manifest.csv
    transported_date: "{{TODAY}}"
    target_instance: "{{MB_TARGET_HOST}}"
    transported: N
    skipped_duplicate: N
    failed: N
    not_attempted: N
    not_attempted_reasons: {row_not_signed_off: N, removed_no_tenant_data: N, missing_db_mapping: N, sandboxing_policy_missing: N, cards_incomplete: N, no_surviving_cards: N, skip_duplicate_missing_target_id: N}
```

### Step 7: Output next command

```
Prove the transported cards return the tenant's rows before go-live:
/wire:metabase-equivalency-validate $ARGUMENTS
```

A `failed` or `not_attempted` card blocks the tenant instance's go-live the same way an unresolved card does: the equivalency gate cannot pass a card that is not there.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_transport_manifest.csv`
- `.wire/releases/$ARGUMENTS/migration/metabase_db_mapping.csv`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv` (notes only, where present)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout_transport` as artifact, `generate` as action.

3. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout_transport` as artifact, `generate` as action.

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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
