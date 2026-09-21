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
    'command': 'metabase-carveout-transport',
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

## Workflow Specification

---
wire_schema: "1.0"
command: utility
artifact: metabase_carveout
domain: migration
release_types:
  - platform_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: metabase_carveout
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
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

If `MB_TARGET_HOST` resolves to the same instance as `MB_HOST`, stop: transport moves objects between two independently-hosted deployments. The same-instance cases are `metabase-carveout-repoint`'s (#255) — duplicating a card into another collection on this instance, or repointing an existing card's warehouse project without moving it — and the two commands are mutually exclusive by design. Report the conflict, name the repoint pipeline, and create nothing.

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
