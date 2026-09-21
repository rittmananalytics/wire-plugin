---
description: Produce the same-instance repoint plan as a dry-run artifact: per warehouse-layer card, the write mode, destinations, database-id and template-tag remaps, and SQL-text rewrites of hardcoded source-project references
argument-hint: <release-folder> [--collection id] [--dashboard id] [--mode duplicate/in_place] [--include-layer card_edit]
---

# Produce the same-instance repoint plan as a dry-run artifact: per warehouse-layer card, the write mode, destinations, database-id and template-tag remaps, and SQL-text rewrites of hardcoded source-project references

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
    'command': 'metabase-carveout-repoint-generate',
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
description: Produce the same-instance repoint plan as a dry-run artifact — per warehouse-layer card, the target collection, the write mode, the database-id and template-tag remaps, and every SQL-text rewrite of a hardcoded source-project table reference, writing nothing to the instance
argument-hint: <release-folder> [--collection <id> | --dashboard <id>] [--mode duplicate|in_place] [--include-layer card_edit]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_carveout_repoint_plan` and `artifact_file_path: migration/metabase_carveout_repoint_plan.csv` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command writes NOTHING to the Metabase instance.

Instance reads (MB_HOST):  card definitions, collection tree, database
                           details, field metadata, snippet bodies
Local writes only:         migration/metabase_carveout_repoint_plan.csv
                           migration/metabase_db_mapping.csv
```

The plan is the dry-run. `metabase-carveout-repoint` is the only command in this pipeline that writes, and it executes only a plan that `metabase-carveout-repoint-validate` has passed.

---

# Metabase Carve-out: Repoint Plan Generate

## Purpose

`metabase-carveout-transport` moves cards to a second, separately-hosted Metabase deployment, and hard-stops when `MB_TARGET_HOST` resolves to the same instance as `MB_HOST` (#255). That guard is correct for transport, but it left two same-instance cases with no supported command: duplicating a card into a different collection on the same instance, and repointing an existing card's underlying warehouse project without moving or duplicating it at all. Both arise when a carve-out's target is a separate BigQuery project reachable from the *same* Metabase instance rather than a separate Metabase deployment — the `warehouse_layer` layer decision, which names the tenant view and the repoint but has never had a mechanic behind it.

This command is the plan step of the same-instance sibling to the transport pipeline: same plan → validate → write shape, same rewrite discipline, no cross-instance machinery. It produces the complete rewrite plan before anything is written: the database-id remap, the template-tag field remaps, and a SQL-text rewrite for every fully-qualified `project.dataset.table` reference to a source or shared project. That last class is the same gap #221 found and fixed for the cross-instance case, and it applies here unchanged: on BigQuery, `` `project.dataset.table` `` in a card's native SQL is a literal, not resolved through the Metabase connection, so repointing `dataset_query.database` alone leaves the card reading the shared project's data while the manifest reports it repointed. Being on one instance does not make the literal resolve differently.

`metabase-carveout-repoint-validate` then re-derives the scan independently and checks the plan; `metabase-carveout-repoint` executes only the validated plan. The rewrite is mechanical once the database mapping is confirmed, so the plan gets deterministic validation, not a second human sign-off: the `metabase_carveout review: approved` gate remains the only write authorisation.

## Scope: cards, not dashboards

The pipeline plans **cards only**. On one instance a dashboard already points at the card ids it uses, so an `in_place` repoint needs no dashboard change at all — preserving the card id is the point. A `duplicate` set that also needs its own dashboard is out of scope here: duplicate the dashboard in Metabase and record the resulting ids, rather than have this pipeline assemble one.

## Prerequisites

- `migration.scope == tenant_carveout`
- `metabase_carveout review: approved`. The plan is derived from the signed-off manifest; there is nothing to plan before sign-off.
- `migration/metabase_carveout_manifest.csv` present, with rows at `signed_off` or later
- Instance credentials: `MB_HOST` + `MB_API_KEY` (read-only use here)
- **Same instance.** If `MB_TARGET_HOST` is set and resolves to a different instance from `MB_HOST`, stop: that is a cross-instance move and belongs to `metabase-carveout-transport-generate`. Report both hosts before planning anything. This is the exact inverse of transport's guard, and the two commands are mutually exclusive by design.

## Flags

- `--collection <id>` / `--dashboard <id>`: narrows within the signed-off set, resolved the same way as `metabase-carveout-generate` Step 1 (a dashboard resolves to its deduped card set).
- `--mode duplicate|in_place`: the default write mode for every planned card. Omitted, the mode is per-row from the manifest's `repoint_mode` column where the consultant has set it, and `duplicate` where they have not. A flag value overrides the column for this run and is recorded per row, so the plan always states the mode rather than leaving it to the write step.
- `--include-layer card_edit`: widens the in-scope layer set (Step 1).

## Inputs

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_manifest.csv`: the signed-off worklist, with its `layer_decision` per row
- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`: collection tree, snippet bodies, card references, the card-to-dashboards reverse index
- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_manifest.csv`: prior repoint state, when it exists (recorded staged and repointed ids)
- `.wire/releases/$ARGUMENTS/migration/metabase_db_mapping.csv`: the database mapping, confirmed here if not already
- `.wire/releases/$ARGUMENTS/status.md`: scope, tenant project, target collection ids

## Workflow

### Step 1: Derive the worklist

Start from the carve-out manifest rows in scope, then apply these rules in order per row:

1. **Row not signed off** (`status: proposed`): no plan rows, recorded `out_of_scope`, reason `row_not_signed_off`.
2. **`action: remove_dashcard`**: no plan rows, reason `removed_no_tenant_data`. The card has no tenant data; repointing it at the tenant project would produce an empty card, not a correct one.
3. **Layer not repointed**: `layer_decision` of `sandboxing` or `dashboard_parameter` gets no plan rows, reason `layer_not_repointed`. Those layers scope a card without changing its query, so there is nothing to repoint.
4. **In scope**: `layer_decision: warehouse_layer` always, and `layer_decision: card_edit` only when `--include-layer card_edit` was passed. A `card_edit` card can carry a hardcoded source-project reference of its own, but including it is the consultant's call, not an inference: without the flag it is `out_of_scope`, reason `layer_requires_opt_in`.

`warehouse_layer | card_edit | sandboxing | dashboard_parameter` is the closed layer vocabulary, unchanged from `metabase-carveout-generate`. Any other value is an error naming the value and the card, never a fall-through to planning a write.

### Step 2: Confirm the database mapping

Write (or re-read) `migration/metabase_db_mapping.csv`, the same file and columns the transport pipeline uses — on a same-instance repoint both sides are databases on one instance:

```
source_database_id, source_database_name, source_project,
target_database_id, target_database_name, target_project, confirmed
```

`source_project` and `target_project` are the GCP projects each database connection points at, read from the instance's database details, never typed from memory. Present the table to the consultant and require `confirmed: yes` per row. Never map by name: a database named like the source one is a hint for the consultant, not a mapping. A shared project that hosts no mapped database but appears in card SQL (a pre-carve-out shared project) is added by the consultant as a mapping row with the target it rewrites to, or the plan cannot account for its references.

A trial repoint at a scratch or playground dataset is an ordinary mapping row: the target database is the connection that reaches the playground project, confirmed like any other. The plan does not distinguish a trial from a production target — the target collection and the write mode do.

The **source/shared project set** is the set of `source_project` values on confirmed rows. It defines the scan scope in Step 4, and `metabase-carveout-repoint-validate` re-reads it from the same confirmed file.

### Step 3: Resolve the destinations and the write mode

Per in-scope card, resolve three things and record them on every plan row for that card:

- **`write_mode`**: `duplicate` (create a second card, leaving the source card untouched) or `in_place` (replace the existing card's query, preserving the card id and everything that already references it). Closed set; the flag or the manifest column decides it, per Step 1's rule.
- **`target_collection_id`**: where the repointed card ends up. For `duplicate`, the collection that receives the new card; it must already exist on the instance (a missing collection is recorded, never created at plan time). For `in_place`, the card's existing collection, unchanged — an in-place repoint never moves a card.
- **`stage_collection_id`**: the restricted-access collection the change is staged in for review before it reaches production. **Required for every `in_place` row**: a production card with existing dependents is never rewritten without a staged copy to review first. Optional for `duplicate` rows, where the new card can go straight to its target collection because nothing references it yet.

A missing or unreadable destination is recorded on the row (`target_collection_missing` / `stage_collection_missing`) rather than assumed. Validate fails those rows; that is the point.

### Step 4: Scan each card's native SQL for fully-qualified references

For each in-scope card with a native query, scan the SQL text using the rules in `specs/migration/metabase_carveout/transport_generate.md` Step 3, unchanged:

1. **Strip comments first.** Remove `/* ... */` blocks and `--` line remainders before scanning (the #200 rule: a reference inside a comment is not a reference).
2. **Match two forms.** Backtick-quoted `` `project.dataset.table` `` (project ids may contain hyphens; BigQuery then requires the backticks), and unquoted three-part `project.dataset.table` (letters, digits, underscores only; a hyphenated project cannot appear unquoted).
3. **Two-part references are out of scope.** `dataset.table` resolves through the card's connection; remapping `dataset_query.database` already handles it.
4. **Only source/shared projects are in scope.** A reference whose project is not in Step 2's source/shared project set (a public dataset, an unrelated third project) is out of scope and gets no plan row.

The scan is textual after comment stripping: it does not parse string literals, so a three-part path inside a literal (a label such as `'see <project>.x.y'`) can surface as a candidate. The scanner never decides that case; it surfaces the reference and the consultant dispositions it (`no_change_needed`, reason naming the literal), rather than the scanner guessing.

One same-instance rule is additional to the transport scan. A card whose SQL uses a `{{snippet: name}}` or `{{#id-name}}` reference whose **body itself** carries an in-scope source-project reference cannot be repointed by rewriting that body: on one instance the snippet is the same object every other card uses, so the rewrite would silently repoint cards outside the carve-out. The card is recorded `blocked_reference`, reason `shared_snippet_reference`, and it stays a parked decision for the consultant (copy the snippet and point the repointed card at the copy, or inline it) rather than an improvised rewrite. Cross-instance transport never meets this, because there the snippet is a separate object created on the target.

### Step 5: Build the plan rows

One plan row per rewrite, `rewrite_type` from the closed vocabulary:

| rewrite_type | source_value | target_value | how the target resolves |
|---|---|---|---|
| `database_id` | source `dataset_query.database` | confirmed target database id | Step 2 mapping row |
| `template_tag_field` | source field id (per tag) | target field id | target database's field metadata |
| `sql_table_reference` | source project | target project | Step 2 mapping row's `target_project` |

Field ids are per-database in Metabase, not per-instance, so a card moving from one database connection to another needs its field-filter tags remapped even though nothing crossed an instance boundary. That is why `template_tag_field` stays in the vocabulary here.

Three of transport's rewrite types are deliberately **absent**: `snippet_ref`, `card_ref` and `collection_id`. Snippet and card ids do not change on one instance, and a repointed card's collection is a destination, not a rewritten reference. Nothing in this pipeline rewrites an id to make it resolve on another deployment, and nothing creates a permission group or a sandboxing policy — that complexity is specific to crossing an instance boundary.

`disposition` is the closed set:

- `rewrite`: `target_value` populated from the confirmed mapping or the target database's metadata.
- `no_change_needed`: the reference deliberately stays as it is, with a recorded reason (e.g. genuinely shared reference data that stays on the shared project). Valid only for `sql_table_reference`, and a blank reason is a defect.

Every `sql_table_reference` row's target project comes from the confirmed mapping row for that source project, never from name similarity. An in-scope reference the consultant cannot yet disposition stays in the plan as `rewrite` with a blank `target_value`; validate will fail it, which is the point: no reference leaves the plan unaccounted.

### Step 6: Write the plan

**Output location**: `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_plan.csv`

```
object_type, source_id, name, layer_decision, write_mode,
target_collection_id, stage_collection_id, rewrite_type, reference,
source_value, target_value, disposition, reason
```

`reference` carries the matched text for `sql_table_reference` rows (the canonical `project.dataset.table`) and the tag name for `template_tag_field` rows. A card that is `out_of_scope` or `blocked_reference` gets a single row carrying its reason and no rewrite, so the plan accounts for every signed-off card rather than silently omitting it. The plan is a derived artifact: rewritten from scratch on every run, unlike the repoint manifest, which is the durable upserted record.

### Step 7: Update status

```yaml
artifacts:
  metabase_carveout_repoint_plan:
    generate: complete
    file: migration/metabase_carveout_repoint_plan.csv
    generated_date: "{{TODAY}}"
    planned_cards: N
    write_modes: {duplicate: N, in_place: N}
    sql_references_in_scope: N
    sql_rewrites: N
    no_change_needed: N
    out_of_scope: N
    blocked_reference: N
```

### Step 8: Output next command

```
/wire:metabase-carveout-repoint-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_plan.csv`
- `.wire/releases/$ARGUMENTS/migration/metabase_db_mapping.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout_repoint_plan` as artifact, `generate` as action.

3. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout_repoint_plan` as artifact, `generate` as action.

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
