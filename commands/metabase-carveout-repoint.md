---
description: Execute the validated same-instance repoint plan: duplicate a card into its target collection, or swap the rewritten query into the existing production card in place, staged for review first
argument-hint: <release-folder> [--stage] [--promote] [--collection id] [--dashboard id] [--card id] [--dry-run]
---

# Execute the validated same-instance repoint plan: duplicate a card into its target collection, or swap the rewritten query into the existing production card in place, staged for review first

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
    'command': 'metabase-carveout-repoint',
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
description: Execute the validated same-instance repoint plan — duplicate a carve-out card into its target collection, or swap the rewritten query into the existing production card in place, staged for review first; requires source and target to be the same instance
argument-hint: <release-folder> [--stage | --promote] [--collection <id> | --dashboard <id>] [--card <id>] [--dry-run]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_carveout_repoint` and `artifact_file_path: migration/metabase_carveout_repoint_manifest.csv` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command WRITES to the Metabase instance the carve-out already runs on.
It is the only command in this pipeline that writes.

  1. It requires source and target to be the SAME instance. A different
     MB_TARGET_HOST is a hard stop — that is metabase-carveout-transport.
  2. In `duplicate` mode it is additive: it creates a new card and never
     touches the source card.
  3. In `in_place` mode it REPLACES an existing production card's query,
     keeping the card id. It does this only from a staged copy that has
     been reviewed and passed equivalency, and only with the card's
     pre-change query recorded verbatim as a rollback baseline.
  4. It never repoints an unsigned row. The metabase-carveout-review
     sign-off is the write authorisation, row by row.
  5. It never deletes a card, a collection, or a snippet.

Instance (reads and writes):  MB_HOST
```

If `MB_TARGET_HOST` is set and resolves to a **different** instance from `MB_HOST`, stop before writing anything: that is a cross-instance move, and `metabase-carveout-transport` is the command for it. This is the exact inverse of transport's guard — transport refuses a same-instance target, this refuses a cross-instance one — and the two are mutually exclusive by design.

---

# Metabase Carve-out: Repoint

## Purpose

The write step of the same-instance repoint pipeline (#255). Where a carve-out's target is a separate warehouse project reachable from the same Metabase instance rather than a separate Metabase deployment, this command is the mechanic behind the `warehouse_layer` layer decision: it duplicates a signed-off card into a target collection with its query rewritten, or replaces an existing card's query in place while keeping the card id and every reference to it.

It decides nothing. The layer decision was made at `metabase-carveout-generate` and adjudicated at `metabase-carveout-review`; the rewrites, the write mode and the destinations were fixed at `metabase-carveout-repoint-generate` and checked at `metabase-carveout-repoint-validate`. This command executes a validated plan and records what it did.

## The dev/prod path

An `in_place` repoint rewrites a card other things already reference — dashboards, subscriptions, other cards. It therefore runs in two halves, and never in one:

1. **`--stage`**: create the rewritten card in the plan's restricted-access `stage_collection_id`. The production card is untouched. The staged card id is recorded in the manifest, and the production card's current `dataset_query` is recorded verbatim alongside it, with its SHA-256, as the rollback baseline. Outcome `staged`.
2. **`--promote`**: swap the staged card's query into the existing production card, preserving the card id. Outcome `repointed`.

`--promote` requires, per card: a `staged` row in the manifest, a recorded `baseline_query_sha256`, and a passing card-level equivalency verdict for the staged card. A card missing any of the three is `not_attempted` with the reason naming which (`not_staged`, `baseline_not_recorded`, `equivalency_not_passed`), and the production card is left exactly as it was.

A `duplicate` repoint may take the same two halves, and does when the plan names a `stage_collection_id`. Where the plan does not, the new card goes straight to its target collection in one step: nothing references it yet, so there is nothing to review it against.

Run with neither flag: `duplicate` rows without a staging collection are written to their target collection; every other row is staged only. An `in_place` row is never promoted by a run that did not ask for it.

## Prerequisites

- `migration.scope == tenant_carveout`
- `metabase_carveout review: approved`. If not, stop: nothing is written and every worklist row is recorded `not_attempted` with reason `review_not_approved`. The manifest sign-off is the write authorisation, exactly as it gates the carve itself.
- `migration/metabase_carveout_manifest.csv` present, with rows at `signed_off` or later
- Instance credentials: `MB_HOST` + `MB_API_KEY`, write-scoped. Credentials are never written into any file this command produces.
- Same instance, per the guard above.
- `migration/metabase_db_mapping.csv` confirmed
- `migration/metabase_carveout_repoint_plan.csv` present, with `metabase_carveout_repoint_plan validate: pass` in status.md. The command refuses to run against a plan the validate has not passed, a plan changed after its pass (compare the plan's mtime to `validated_date`), or a plan older than the manifest it was generated from: stop with reason `plan_stale` and re-run `metabase-carveout-repoint-generate` then `metabase-carveout-repoint-validate`. Nothing is written against an unvalidated or stale plan.

## Flags

- `--stage`: run the staging half only. Every in-scope card is created in its `stage_collection_id`; no production card is changed. A card whose plan row has no `stage_collection_id` is `not_attempted`, reason `stage_collection_missing`.
- `--promote`: run the promotion half only, under the three requirements above. Never combined with `--stage` in one run: a card is staged, reviewed, then promoted, and a single run that did both would skip the review that staging exists for.
- `--collection <id>` / `--dashboard <id>` / `--card <id>`: narrows within the plan, resolved the same way as `metabase-carveout-generate` Step 1.
- `--dry-run`: print the per-card action (write mode, half, mapped database id, staged or production target) and write nothing. The full dry-run artifact is `metabase-carveout-repoint-generate`'s plan; this flag is a quick print of the same worklist.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_plan.csv`: the validated rewrite plan
- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_manifest.csv`: the signed-off worklist
- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_manifest.csv`: prior repoint state, when it exists (idempotency record, staged ids, rollback baselines)
- `.wire/releases/$ARGUMENTS/migration/metabase_db_mapping.csv`: the confirmed database mapping
- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`: collection tree, snippet bodies, the card-to-dashboards reverse index
- `.wire/releases/$ARGUMENTS/status.md`: scope, tenant project, plan validation state

## Workflow

### Step 1: Confirm the gates and derive the worklist

Confirm the same-instance guard, then `metabase_carveout review: approved`, then `metabase_carveout_repoint_plan validate: pass`; stop with the rules above on any of them. Then derive one worklist row per plan card in scope, in this order per card:

1. **Row not signed off** in the carve-out manifest (`status: proposed`): `not_attempted`, reason `row_not_signed_off`. Only signed rows are ever written, mirroring the carve's own rule.
2. **Parked in the plan** (`out_of_scope` or `blocked_reference`): `not_attempted`, carrying the plan's own reason (`removed_no_tenant_data`, `layer_not_repointed`, `layer_requires_opt_in`, `shared_snippet_reference`). A parked card is a decision the consultant has yet to make; this command never makes it for them.
3. **Already repointed**: the repoint manifest records a `repointed_id` for this card from a prior run — for `duplicate` the created card, for `in_place` the card's own id with a `promoted_date`: `skipped_duplicate`, reason `already_repointed`. Matched by the recorded id, confirmed with a GET against it, never matched by name. A name match proves nothing: one instance can hold several cards called "Revenue by month".
4. **No confirmed database mapping** for the card's source database id: `not_attempted`, reason `missing_db_mapping`. Never name-guessed.
5. **Everything else**: queued for Step 2 at its plan `write_mode`.

If the repoint manifest is absent but the plan's target collection already holds cards, stop and reconcile with the consultant before writing: without the recorded ids there is no safe way to tell a prior repoint from unrelated content, and guessing by name is the exact failure this manifest exists to prevent.

### Step 2: Apply the rewrites to each card's query

For each queued card, take the **carved definition** — the applied copy where the carve-out row is `applied`/`validated`; for a `signed_off` row not yet applied, the source definition with the manifest's signed-off transformation applied in flight; never a filter re-derived from the registry at write time, the reviewed one is the one that ships — and apply the plan's rows for that card, and only those rows:

1. **`dataset_query.database`**: the confirmed target database id from the `database_id` row.
2. **Template tags and field filters**: each tag's field id replaced with the `template_tag_field` row's target, recorded per tag in the manifest.
3. **SQL-text rewrites**: each `sql_table_reference` row applied, source project to target project exactly as the plan maps it (`rewrite` rows), or the reference left as it is (`no_change_needed` rows, reason recorded at plan time).

A reference found at write time that the plan does not carry is a hard stop for that card, `failed`, reason `plan_stale`, never an improvised rewrite: the plan was validated, an unplanned rewrite was not. Nothing else about the card changes — not its name, not its visualisation settings, not its description. Snippet bodies and referenced cards are never edited: on one instance those are the same objects other cards use, and the plan parks any card that would need one changed.

### Step 3: Write, per mode and half

**`duplicate`, unstaged**: create a new card in `target_collection_id` with the rewritten query. Record `repointed_id`. Outcome `repointed`.

**`duplicate`, staged**: under `--stage`, create the new card in `stage_collection_id` and record `staged_card_id`; outcome `staged`. Under `--promote`, move (or re-create) it in `target_collection_id` and record `repointed_id`; outcome `repointed`.

**`in_place`, `--stage`**: read the production card's current `dataset_query`, record it verbatim in the manifest with its SHA-256 as `baseline_query_sha256`, then create the rewritten copy in `stage_collection_id`. The production card is not touched. Outcome `staged`.

**`in_place`, `--promote`**: check the three requirements (staged row, recorded baseline, passing equivalency verdict), then update the production card's `dataset_query` to the staged query, keeping the card id, its collection, its name and everything referencing it. Record `repointed_id` as the card's own id and the `promoted_date`. Outcome `repointed`.

Per-card outcomes are the closed set: `staged` (created in the staging collection; nothing in production changed), `repointed` (written to production — a new card created, or an existing card's query swapped), `skipped_duplicate` (already repointed, by recorded id), `failed` (the write or a required remap errored; the reason names the error, and the card can be retried on a re-run because no id was recorded and, for `in_place`, the baseline is intact), `not_attempted` (never tried; the reason names why, per Step 1). Every non-`repointed` row carries its reason; a blank reason is itself a defect.

### Step 4: Rollback

The baseline is the rollback. To revert a promoted `in_place` card, write the manifest's recorded baseline query back to the card id and clear the `promoted_date`; the recorded SHA-256 proves the baseline is the query that was there before the promotion. A promoted card whose recorded baseline does not hash to `baseline_query_sha256` is reported and not rolled back automatically: the card has been edited by someone else since, and overwriting that edit is the consultant's decision.

A `duplicate` repoint needs no rollback path: the source card was never touched, and the created card can be archived in Metabase.

### Step 5: Write the repoint manifest

**Output location**: `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_manifest.csv`

```
object_type, source_id, name, layer_decision, write_mode,
source_database_id, target_database_id, stage_collection_id,
target_collection_id, staged_card_id, repointed_id,
baseline_query_sha256, outcome, reason, tag_remaps,
staged_date, promoted_date
```

One row per in-scope card. The `source_id -> repointed_id` pairs and the baselines are the durable record: re-runs key on them (Step 1 rule 3), rollback reads them (Step 4), and `metabase-equivalency-validate` resolves each card's repointed copy through them. The manifest is upserted, never rewritten from scratch, so a killed run resumes where it stopped. The baseline query is recorded verbatim in a sidecar file per card (`migration/repoint_baselines/<source_id>.sql`) with only its hash in the CSV, so the manifest stays readable.

Update register rows where the register exists (`object_type: metabase_card`, `origin: carveout`): record the write mode and the repointed id in `notes` for each `repointed` card. Skip silently if the register does not exist.

### Step 6: Update status

```yaml
artifacts:
  metabase_carveout_repoint:
    generate: complete
    file: migration/metabase_carveout_repoint_manifest.csv
    repointed_date: "{{TODAY}}"
    instance: "{{MB_HOST}}"
    staged: N
    repointed: N
    skipped_duplicate: N
    failed: N
    not_attempted: N
    not_attempted_reasons: {review_not_approved: N, row_not_signed_off: N, removed_no_tenant_data: N, layer_not_repointed: N, layer_requires_opt_in: N, shared_snippet_reference: N, missing_db_mapping: N, stage_collection_missing: N, not_staged: N, baseline_not_recorded: N, equivalency_not_passed: N}
```

### Step 7: Output next command

```
Prove the repointed cards return the tenant's rows before anyone relies on them:
/wire:metabase-equivalency-validate $ARGUMENTS
```

A `staged` card is not done: it is waiting for its equivalency verdict and the consultant's review before `--promote`. A `failed` or `not_attempted` card blocks the carve-out's go-live the same way an unresolved card does.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_manifest.csv`
- `.wire/releases/$ARGUMENTS/migration/repoint_baselines/<source_id>.sql` (one per `in_place` card staged)
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv` (notes only, where present)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout_repoint` as artifact, `generate` as action.

3. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout_repoint` as artifact, `generate` as action.

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
