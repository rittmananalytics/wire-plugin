---
description: Experimental: Translate a batch of Tableau data sources, Metabase or Omni content to LookML views and explores on the migration branch (deterministic converter plus agent judgement)
argument-hint: <release-folder> [--batch N 
---

# Experimental: Translate a batch of Tableau data sources, Metabase or Omni content to LookML views and explores on the migration branch (deterministic converter plus agent judgement)

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
    'command': 'lookml-model-generate',
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
artifact: lookml_model
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> translates one model batch (default: the next incomplete batch); --all translates every incomplete batch in order"
produces:
  - type: document
    path: "migration/lookml_model/lookml_model.md"
    description: "Batch summary: per batch, views, explores and parameters emitted, needs_human items open, branch commit"
  - type: report
    path: "migration/lookml_model/<batch_id>/needs_human.json"
    description: "Converter report: every construct not emitted, with class, reason and proposal"
  - type: document
    path: "migration/lookml_model/<batch_id>/models/<model>.model.lkml"
    description: "Emitted LookML model file with explores (views under views/ and the conversion summary in the same batch folder)"
preconditions:
  - artifact: looker_target_setup
    action: review
    outcome: approved
auto_validate: false
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
description: "Experimental: Translate one batch of Tableau, Metabase, Looker Studio or Omni content into LookML views and explores on the migration branch; the deterministic converter writes the mechanical LookML and every construct it cannot emit becomes a needs_human item"
argument-hint: <release-folder> [--batch <id> | --all]

---

## Auto-Delegation

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: lookml_model` and `artifact_file_path: migration/lookml_model/lookml_model.md` before proceeding.

---

# LookML Model: Generate

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

The translation has two halves. The mechanical half is a script: `wire/scripts/twb_to_lookml.py convert` reads the snapshot, applies the pair's translation guide and emits LookML deterministically, including the row-level subset of the Tableau calculation language. The judgement half is what the script refuses: LOD expressions, table calculations, blends, sets, unmapped functions, and the cardinality of every join (Tableau physical joins declare none). Each arrives as a `needs_human` item. The agent resolves it from the plan's rulings or parks it. It never hand-writes LookML the script can emit.

```
⚠️  DATA SAFETY REMINDER
Tableau: read only (the snapshot). LookML: written to the migration branch only, never merged here.
Warehouse: no queries. Validation queries belong to /wire:lookml-model-validate.
```

## Pair: metabase_to_looker

The workflow applies with these differences.

- **Step 1.** A model batch is one Metabase database (one connection), optionally narrowed to the dashboards in the batch.
- **Step 2.** The converter is `mb_to_lookml.py`; it also writes the batch's LookML dashboards (one per dashboard tab, and a one-tile dashboard per question on no dashboard), which `looker-content-generate` takes from the batch output:

```bash
python3 <plugin-root>/scripts/mb_to_lookml.py convert \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/metabase \
  --out .wire/releases/$ARGUMENTS/migration/lookml_model/<batch_id> \
  --model <bi_migration.target.model> --connection <connection> --database <metabase database id> \
  [--dashboards <id,id>] [--include-root <folder>]
```

- **Step 3.** The `needs_human` items for this pair: native SQL questions and models that became views on their SQL (remodel onto shared views, or keep), fields lifted from simple native SQL (keep or remove), joins not to a primary key, custom columns not translated, binning by number of bins (choose a fixed width), multi-stage questions, dashboard filters that change date grouping, and content on a database Looker cannot connect to. Primary keys come from Metabase's metadata (`type/PK`); a joined view without one is listed.

## Pair: looker_studio_to_looker

The workflow applies with these differences.

- **Step 1.** A model batch is a set of reports (a report family, or the reports on one subject area).
- **Step 2.** The converter is `ls_to_lookml.py`, run on the batch's `report.json` files and the ruled metric catalogue; it also writes the batch's LookML dashboards, which `looker-content-generate` takes from the batch output:

```bash
python3 <plugin-root>/scripts/ls_to_lookml.py convert \
  --reports .wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>/report.json ... \
  --catalogue .wire/releases/$ARGUMENTS/audit/metric_catalogue.json --namespace <looker_studio_namespace> \
  --out .wire/releases/$ARGUMENTS/migration/lookml_model/<batch_id> \
  --model <bi_migration.target.model> --connection <connection> [--include-root <folder>]
```

- **What it writes.** A view per BigQuery table a data source reads and per custom SQL data source; measures for the aggregations the charts use; calculated fields translated to BigQuery SQL (a ruled catalogue entry names the measure; Looker Studio's division becomes `SAFE_DIVIDE`); charts on Looker Studio's Looker connector pointed at the existing explore, with no view; `parity_map.json` linking each chart to its element and its recording columns to Looker fields.
- **Step 3.** The `needs_human` items for this pair: custom SQL views (remodel or keep), calculated fields not translated, blends (model the join in an explore), data sources Looker cannot read (Search Console, GA4, Sheets, Funnel.io: a pipeline task or drop), date range control defaults (not in the capture), a chart's own date range ending today (Looker's nearest filter also takes in the rest of the current month), breakdown dimensions pivoted (Looker Studio draws only its top series), and dashboards on an existing Looker model (written to a folder of their own: add its include to that model).

## Pair: omni_to_looker

The workflow applies with these differences.

- **Step 1.** A model batch is a set of topics (with the views they join), optionally narrowed to the dashboards in the batch. One Omni shared model maps to one LookML model on one connection.
- **Step 2.** The converter is `omni_to_lookml.py`; it also writes the batch's LookML dashboards (one per Omni dashboard document) and `parity_map.json`, which `looker-content-generate` takes from the batch output:

```bash
python3 <plugin-root>/scripts/omni_to_lookml.py convert \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/omni \
  --out .wire/releases/$ARGUMENTS/migration/lookml_model/<batch_id> \
  --model <bi_migration.target.model> --connection <connection> \
  [--topics <name,name>] [--documents <id,id>] [--include-root <folder>]
```

- **What it writes.** A view per Omni view: a schema view keeps its table (`sql_table_name`, with the connection's project on BigQuery), a query view that is only `SELECT * FROM <table>` does too, other SQL becomes a derived table. Bare column names in field SQL are qualified with `${TABLE}`; `${field[month]}` becomes `${field_month}`. A time field (declared timeframes, Omni's own field list, or a DATE or TIMESTAMP column in `columns.json`) becomes a dimension group. Topics become explores on their base view, with the nested joins flattened and each join's `sql_on`, relationship and type taken from the relationship that connects it; an alias (`join_to_view_as`) joins with `from:`.
- **Step 3.** The `needs_human` items for this pair: query views built from a topic query, views with Mustache in their SQL (and the topics on them), nested fields, markdown and links, bins (Looker labels tiers differently), cross-view references, filter-only fields, a relationship declared from the other side (confirm the join type), custom aggregate SQL on a joined view (fan-out), default filters (not emitted: Looker's `always_filter` would also change saved tiles), access filters (the user attributes must exist), AI context (dropped), and timeframes with no LookML equivalent. Dimensions are typed from the snapshot's `columns.json` (read from `INFORMATION_SCHEMA` through Omni), else from their format and the filters that use them; the rest default to `string`. A DATE column's group gets `datatype: date`.

## Workflow

### Step 1: Resolve the batch

Read the plan's model batches (`migration/bi_migration_batches.csv`, `batch_kind: model`). A batch is a set of data source identities (one per fingerprint group the plan ruled to consolidate).

### Step 2: Run the converter

```bash
python3 <plugin-root>/scripts/twb_to_lookml.py convert \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/tableau \
  --out .wire/releases/$ARGUMENTS/migration/lookml_model/<batch_id> \
  --model <bi_migration.target.model> --connection <connection> --dialect <bigquery|snowflake> \
  --datasets <identity,identity,...> [--include-root <folder>]
```

When the client's LookML repository already has views (most do), pass `--include-root <folder>` (for example `tableau_migration`) and a model name that is not in use: views and dashboards are written under the folder and the model includes only it, so the project's existing `/views/` are not pulled in and view names cannot clash. A new model must be configured by a Looker admin (Admin, Projects) before it can be queried in production.

### Step 3: Resolve needs_human

Read `migration/lookml_model/<batch_id>/needs_human.json`. For each item: apply the plan's ruling (an LOD becomes a derived table or is dropped; a table calculation becomes a Looker table calculation on the tile; an extract is rebuilt as a dbt model or read live), confirm each join's `relationship:` (Tableau's default relationship declares no unique keys, so the converter proposes `many_to_many`) and each proposed `primary_key: yes` (taken from a view's single `*_pk` column), set one on any joined view listed without one, or park the item for the release director. Write the resolution against each item in the batch summary. Hand-written LookML goes in a separate `<batch_id>/hand/` folder, so the converter's output stays regenerable.

### Step 4: Write to the branch

The batch folder now holds `views/<view>.view.lkml`, `models/<model>.model.lkml`, `needs_human.json` and `conversion_summary.json`. Copy `views/`, `models/` and `hand/` into the LookML repo on the migration branch and commit. Record the commit.

### Step 5: Update status and output

```yaml
artifacts:
  lookml_model:
    generate: complete
    file: migration/lookml_model/lookml_model.md
    experimental: true
    batches_complete: [<batch_id>]
    needs_human_open: N
```

Output `/wire:lookml-model-lint $ARGUMENTS --batch <batch_id>`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact_id, `LookML Model` as artifact_name, and the `file` value from `artifacts.lookml_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `lookml_model` as artifact, `generate` as action.

Execute the complete workflow as specified above.
