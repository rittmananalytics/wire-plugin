---
description: Generate Metabase migration runbook — translate card SQL, remap permission groups, two-stage connection repoint
argument-hint: <release-folder>
---

# Generate Metabase migration runbook — translate card SQL, remap permission groups, two-stage connection repoint

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

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'metabase-migration-generate',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Automatic Validation (on by default)

---
description: Internal utility — injected auto-validate section so generate commands run their matching validate step automatically and fold the result into their output
---

Every `generate` command that has a matching `validate` command for the
same artifact runs that validate step automatically as part of generate —
by default, with no separate command to remember. This section only appears
on commands where that applies; artifacts with no separate validate step at
all (e.g. mockups, workshops, UAT) never carry this section.

## Step: Check `auto_validate`

Read this command's own `auto_validate` front-matter field, in the Workflow
Specification below. Two states:

- **Absent, or `true`** (the default — most artifacts): auto-validate runs.
- **`false`**: this artifact's validate step is expensive — it runs real
  code, queries a live warehouse or BI tool, or otherwise does IO beyond
  re-reading local files — so it does not run automatically. Skip to
  "If `auto_validate: false`" below.

## If `auto_validate` is absent or `true`: run validate automatically

Once this command finishes writing its artifact, before ending:

1. Run this artifact's own `/wire:<artifact-with-dashes>-validate` workflow
   in full, exactly as if the consultant had typed it themselves — same
   inputs, same `status.md` write to `artifacts.<artifact>.validate`, same
   report. This is not optional or an extra step layered on top; it is the
   default behavior for this artifact.
2. Fold the result into this command's own closing output rather than
   presenting it as a separate command run:
   - **PASS** — add a single closing line: `✅ Auto-validated — PASS`. The
     full report already went to `status.md`/`execution_log.md`, exactly as
     it would from a standalone validate run — no need to repeat it here.
   - **FAIL** — surface the validate command's own failure report in full,
     exactly as running validate standalone would show it, so the
     consultant sees what's wrong immediately without running anything
     else themselves.
3. This never blocks or undoes generate itself — the artifact is written
   either way, and its content is never rolled back because validate
   failed. Auto-validation only means validate has already run and its
   result is already on record by the time generate finishes, instead of
   waiting for the consultant to remember to run it separately.

## If `auto_validate` is `false`: state this plainly, don't run it

Do not run validate. End with a line naming why, as specifically as this
spec's own context makes possible (e.g. "runs `dbt run`/`dbt test`",
"queries the live target warehouse", "calls the Looker API directly") —
fall back to "performs live checks against an external system" only if no
more specific reason is evident from context:

```
⚠ This artifact's validate step [reason] and does not run automatically.
Run /wire:<artifact-with-dashes>-validate <release_folder> before
requesting review — review is blocked until it passes.
```

## Why this is always safe either way

`review` already requires `validate: PASS` for this same artifact as one of
its own declared preconditions (see `specs/utils/precondition_gate.md`) —
this is existing, independent enforcement, not something added by this
section. So an `auto_validate: false` opt-out never lets an artifact reach
review unvalidated; it only decides *when* the consultant pays validate's
cost — automatically on every draft (the default), or once, on their own
schedule, before requesting review (the opt-out). Auto-validation is a
convenience that closes the "forgot to run it" gap for the common case; the
gate that actually prevents unvalidated work from being reviewed was already
there.

## Workflow Specification

---
wire_schema: "1.0"
command: generate
artifact: metabase_migration
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
    action: review
    outcome: approved
  - artifact: metabase_audit
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate the Metabase reporting-layer migration runbook — translate card SQL to the target dialect, remap permission groups, validate on a decoy collection/connection, two-stage connection repoint with per-stage rollback

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_migration` and `artifact_file_path: migration/metabase_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before modifying any Metabase configuration, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source warehouse ([source_platform]): READ ONLY.
  Do NOT delete or repoint the production database connection during the
  migration phase. The existing Snowflake connection stays live as the
  rollback path until cutover.

Validation runs against a DECOY collection and a NON-PRODUCTION database
  connection only. Production cards, dashboards, and their consumers are
  never touched during validation.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not point any connection at these):
  [list each production project ID]
```

If any action would repoint or delete the production database connection outside the cutover sequence, or run validation against production cards, stop and report the conflict before proceeding.

---

# Metabase Migration — Generate

## Purpose

Generates the runbook for migrating the client's Metabase reporting layer from the source warehouse (Snowflake) to the target (BigQuery). The pivot is the **Metabase database connection** — cards follow the connection they reference, so the migration adds a target BigQuery connection, translates native-SQL cards to the target dialect, remaps permission groups, validates against a **decoy collection and non-production connection**, and cuts over by repointing the database connection in **two stages with per-stage rollback**.

This is a **reporting-layer** migration, the Metabase counterpart to reverse ETL migration. It is **not gated by `migration.scope`** — it runs for any migration where the client uses Metabase.

## Cannot proceed without a client-supplied query inventory

This command **requires a client-supplied Metabase query inventory** — the set of cards and their SQL the client confirms as in scope (the audit's catalog, validated and signed off, or a client export). Card SQL drives translation and validation, and inferring it is not safe enough to migrate against. If no client-supplied inventory is available, **stop**:

```
Metabase migration cannot proceed without a client-supplied query inventory.

Provide the confirmed card/SQL inventory (the approved metabase_audit catalog,
or a client export at migration/metabase_query_inventory.csv) and re-run:
/wire:metabase-migration-generate $ARGUMENTS
```

## Prerequisites

- `target_setup review: approved` — target warehouse objects exist
- `metabase_audit review: approved`
- A client-supplied query inventory is present (see above) — hard requirement
- `dbt_migration: complete` for any batch containing models referenced by in-scope cards (cannot validate those cards until their models exist on target)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`
- `.wire/releases/$ARGUMENTS/migration/metabase_query_inventory.csv` (or the approved audit catalog) — the client-supplied inventory
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/status.md`
- Canonical platform pair files at `wire/platform_pairs/<source>_to_<target>/` (translation guide, type mapping)

## Workflow

### Step 1: Confirm prerequisites

Confirm `target_setup review: approved` and `metabase_audit review: approved`. Confirm the client-supplied query inventory is present — if not, stop with the message above. If `dbt_migration` exists, confirm which batches are complete and which cards are thereby unblocked.

Activate the `metabase` skill for connection details and the object hierarchy.

### Step 2: Build the additive target connection and decoy environment

The production database connection is not touched during the migration phase. Work additively:

1. **Add a target BigQuery database connection** in Metabase alongside the existing Snowflake connection (`POST /api/database` or via the CLI). This is additive — the Snowflake connection stays in place.
2. **Create a throwaway decoy collection** to hold test copies of in-scope cards. Production cards and dashboards are left untouched.
3. **Use a non-production database connection for validation** — the test copies in the decoy collection run against the target BigQuery connection scoped to non-production data. No production card is repointed to validate.

### Step 3: Build the card manifest — the review gate (#184)

Before any transformation, write `migration/metabase_card_manifest.csv` — one row per in-scope card: `card_id, card_name, query_type, dashboards, shared, action, source_sql, proposed_sql, template_tag_remaps, snippets_used, card_references, status, notes`. This file is the review gate and the rollback record: **nothing is written to any card until a human signs off its row** (`status: proposed → signed_off → applied → validated`). `metabase-migration-review` presents it.

**Split MBQL out first.** MBQL cards are dialect-neutral — they regenerate against whatever connection they point at — and are usually the majority. They enter the manifest as `action: repoint` with no proposed SQL, so the manual effort is scoped to native cards only.

**Resolve the shared-card decision before any write.** From the audit's card-to-dashboards reverse index: a card on more than one dashboard is a shared object, and editing it changes every dashboard it appears on. Per shared card, record the decision in the manifest — `edit_in_place` (all dashboards move together) or `clone` (the target dashboard gets the converted copy; the others keep the original, which forks maintenance and is recorded as such). The decision is never made implicitly by a write.

### Step 3b: Transform native cards — five surfaces, in dependency order

Conversion order comes from the audit's object graph: **snippets first** (separate objects with their own SQL — convert before any card that uses them), then **leaf cards** (no `{{#id}}` references), then referencing cards. For each native card, five surfaces need attention, not just the query string:

1. **`dataset_query.native.query`** — transpile to the target dialect as a first pass (a mechanical transpiler draft), then correct against the platform-pair guide (`wire/platform_pairs/<pair>/translation_guide.md`). Expect the draft to fail on date arithmetic, window frame syntax, semi-structured access, regex functions, and UDFs — **treat transpiler output as a draft, never a result**. Record the before/after diff in the manifest.
2. **`dataset_query.database`** — must change to the target connection id. Translated SQL against the old connection still runs the old engine.
3. **`template-tags`** — field filters carry **field ids from the source database** which do not survive the connection change; remap each against the target database's field metadata, recorded per tag in the manifest.
4. **Snippets** — `{{snippet: name}}` bodies translated before their consumers (the ordering above).
5. **Card references** — `{{#id-name}}` targets converted before their referrers (the ordering above).

Also convert each affected **dashboard's own filter parameter mappings**, which reference field ids the same way template tags do.

**Cards that resist translation** are `rebuild` (source-only construct, rebuilt against the target connection; original definition captured first). A `repoint` card that fails on the target connection downgrades to `rewrite_sql` in the manifest, never silently.

### Step 3c: Write back — serialization for bulk, per-card PUT for touch-ups

For a whole-estate move, prefer **serialization export → transform the YAML tree → import to target**: it is diffable, reviewable as a change set, and reversible. Per-card `PUT /api/card/:id` is for surgical corrections. Either path applies only to manifest rows at `status: signed_off`, and applies to the **decoy collection test copies** during the migration phase — production cards stay on the source connection until cutover.

### Step 4: Remap permission groups

From the audit's permission group inventory, map each group's data permissions onto the target BigQuery connection and the migrated collections. Produce a permission-group remap table:

```
group_name, source_db_permission, target_db_permission, collection_permissions, notes
```

Apply the remap via the permission graph (`PUT /api/permissions/graph`) at cutover, not during the migration phase. Record the before/after graph so it can be reverted.

### Step 5: Validate on the decoy collection against a frozen baseline

Validate the test copies in the decoy collection only — never production cards. Compare against a **frozen source baseline** (not moving production), per the migration strategy's equivalency section. Per in-scope card:

1. **Result comparison** — run the test card on the target BigQuery connection and compare row count, key columns, and aggregates against the frozen source baseline result.
2. **Dashboard spot-check** — for dashboards built from migrated cards, confirm the decoy copies render with matching values.

No production card or dashboard is repointed to validate. Card-level **equivalence verdicts** (the model taxonomy, per card) come from `/wire:metabase-equivalency-validate` — the decoy check here confirms cards run; the equivalence command proves they return the same rows, and the Stage 2 connection cutover is gated on every in-scope card holding `pass`/`pass_qualified` (#184).

### Step 5b: Update the migration register (#184)

Upsert one register row per **native** card (`object_type: metabase_card`): `source_path` (collection path), `bq_target` (target connection + database: a reporting-layer reference, not a warehouse relation, so the fully-qualified `project.dataset.table` rule of #201 does not apply; `metabase-equivalency-validate` compares cards through the Metabase API and card queries, never by resolving a warehouse table from this column), `state: migrated` on a signed-off, applied manifest row (`failed` on a validation failure; `pending` while `proposed`). MBQL cards are repoint-only and are not tracked as register rows — the connection repoint carries them. Dashboards get `object_type: metabase_dashboard` rows whose `state` derives from their cards (migrated when every constituent card is). Skip silently if the register does not exist.

### Step 6: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/metabase_migration_runbook.md`

Structure:
1. Topology and rationale (additive target connection + decoy collection; connection is the cutover pivot)
2. Build steps (add target BigQuery connection, create decoy collection, copy test cards)
3. Pre-flight checklist (target objects exist, dbt batches complete, client inventory present, source baseline frozen, decoy collection + non-production connection in place)
4. Per-card translation — the card manifest (repoint / rewrite_sql with SQL diff and the five-surface record / rebuild with rebuild plan), in snippet → leaf-card → referencing-card order, with every shared-card edit-vs-clone decision stated
5. **Permission group remap table** (source → target permissions per group)
6. Decoy mapping (production card → test copy in decoy collection; production connection → target connection)
7. Validation procedure — result comparison vs frozen baseline on the decoy collection only
8. **Two-stage cutover sequence with per-stage rollback**:
   - **Stage 1 — pilot repoint.** Repoint a pilot subset of cards (or a pilot connection) from Snowflake to BigQuery, or promote the validated test cards. Validate the pilot on real (non-decoy) consumers. **Rollback:** repoint the pilot back to the Snowflake connection (`PUT /api/database/:id` with the original engine + details), restore any rewritten card SQL from the saved diffs.
   - **Stage 2 — full connection repoint.** Repoint the production Metabase database connection from Snowflake to BigQuery (`PUT /api/database/:id`), so all remaining cards/dashboards resolve against the target. Apply the permission-group remap. **Rollback:** repoint the production connection back to Snowflake details and revert the permission graph to the saved before-state.
9. Rollback procedures consolidated per stage, with the exact connection details and permission graph needed to revert each.

The production Snowflake connection stays live and untouched until Stage 1, and remains the rollback path through Stage 2.

### Step 7: Update status

```yaml
artifacts:
  metabase_migration:
    generate: complete
    file: migration/metabase_migration_runbook.md
    generated_date: "{{TODAY}}"
    repoint_count: N
    rewrite_sql_count: N
    rebuild_count: N
    permission_groups_remapped: N
    decoy_collection: "{{DECOY_COLLECTION_NAME}}"
    query_inventory_source: "approved_audit" | "client_export"
    card_manifest: migration/metabase_card_manifest.csv
    shared_cards_cloned: N          # shared-card decisions that chose clone (forked maintenance, recorded)
    shared_cards_edited: N          # shared-card decisions that chose edit_in_place
    snippets_converted: N
```

### Step 8: Output next command

```
/wire:metabase-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/metabase_migration_runbook.md`
- `.wire/releases/$ARGUMENTS/migration/metabase_card_manifest.csv`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv` (native-card and dashboard rows)
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_migration` as artifact_id, `Metabase Migration` as artifact_name, and the `file` value from `artifacts.metabase_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_migration` as artifact, `generate` as action.

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

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
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
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition, or an advisory gate satisfied by a director's ruling
  - `mode` — the director handed control over or took it back ("you drive" / "I'll drive"), per `specs/utils/director_operating_model.md`
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason
  - For a ruling-satisfied advisory gate: the precondition and the ruling id
- **By**: the git user (`git config user.name`), or `unknown` if git has no
  user configured. Who the run is attributable to, regardless of what typed it.
- **Session**: what invoked the run. One of:
  - `typed` — a person typed the command
  - `orchestrator` — the orchestrating session dispatched it, followed by its
    session id in brackets where one is available: `orchestrator [a1b2c3]`
  - a lane label — the lane that ran it, e.g. `dbt-developer [staging 1/2]`
  - `autopilot` — `/wire:autopilot` ran it

  This is the same value the `invoked_by` telemetry property carries
  (`specs/utils/telemetry.md`), read from `WIRE_INVOKED_BY` and defaulting to
  `typed`. The log records it per row so the record on disk answers the same
  question telemetry answers in aggregate.
- **Duration**: Wall-clock time the workflow took. As the first action of the
  workflow, run `date +%s` and note the value as the start time. When
  appending the log row, run `date +%s` again and format the difference as
  `42s`, `4m 12s`, or `1h 03m`. If the start time was not captured, write
  `n/a`. Skill activation entries write `n/a`.
- **Tokens**: Total model tokens the run consumed (input + output, including
  cache reads and writes). Write the literal `n/a` — a model cannot measure
  its own token usage, and an estimated figure must never be written. On
  Claude Code, the Wire plugin's metrics hook backfills this cell with the
  measured value from the session transcript after the turn ends (see
  Metrics Backfill below). On runtimes without the hook (e.g. Gemini CLI)
  the cell stays `n/a`.
- **Cost (USD)**: Estimated cost of the measured tokens, e.g. `$0.42`. Same
  rule as Tokens: write `n/a`; the metrics hook backfills it where token
  usage can be measured. Never compute or guess this yourself.

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column, with `n/a` in all three metric columns:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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

1. **Append only** — never modify or delete existing log entries, and never
   re-order them. A row is appended at the bottom, always. Rewriting the file
   to insert a row in timestamp order is a modification, not an append. One
   exception: the metrics hook (see Metrics Backfill below) may rewrite the
   Duration, Tokens, and Cost cells of the most recent row, and nothing else.
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise
6. **Timestamps must not go backwards.** Because rows are appended in the order
   things happened, each row's timestamp is greater than or equal to the row
   above it. A row whose timestamp precedes its predecessor's means either the
   clock moved or a row was inserted out of order; both are record defects.
   `/wire:status-sync` flags them, naming both rows. This does not block any
   command — the log is written either way, and the flag is a repair prompt.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.

## Metrics Backfill (Claude Code)

The Wire Claude Code plugin registers a `Stop` hook (`hooks/wire-metrics.sh`)
that runs after each turn ends. It reads the session transcript, sums the
measured token usage from the most recent `/wire:*` command invocation to the
end of the turn, estimates its cost from a built-in price table, and rewrites
the Duration (only if still `n/a`), Tokens, and Cost cells of the log's most
recent row — only when that row's Command matches the command found in the
transcript and the row already has the metric columns. It never touches any
other cell or row. Commands that span several turns (e.g. a review waiting on
feedback) are re-summed on each turn's hook run, so the final backfill covers
the whole command. If the cost table does not recognise the model, Tokens is
still filled and Cost stays `n/a`. On runtimes without this hook, the metric
cells keep the values the workflow wrote.

## Legacy five-column rows

Logs written before the `By` and `Session` columns existed have four data
columns, and logs written before the `Duration`, `Tokens`, and `Cost (USD)`
columns existed have four or six. They stay valid and are never rewritten:

- A reader parses columns positionally and treats a missing `By`, `Session`,
  or metric column as unknown. It does not treat a shorter row as malformed
  and does not backfill it.
- Missing columns are added on the next write. A file whose header still has
  the older shape gets the new header written once, at the point the first
  nine-column row is appended; existing rows are left as they are, so a log
  can legitimately hold several shapes.
- Nothing derives meaning from the absence of the columns. An old row is not
  "typed"; it is unknown. A row without metric cells is unmeasured, not free
  or instant — and the metrics hook skips rows that lack the metric columns.

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20 | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
```
