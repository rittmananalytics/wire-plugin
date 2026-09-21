---
description: Generate dbt Charts boards, one per warehouse subject area, from the dbt manifest and catalog (deterministic scaffold, then curation)
argument-hint: <release-folder> [--subject-area <folder>[,<folder>]] [--no-warehouse] [--force]
---

# Generate dbt Charts boards, one per warehouse subject area, from the dbt manifest and catalog (deterministic scaffold, then curation)

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
    'command': 'dbtcharts-generate',
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
artifact: dbtcharts
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--subject-area <folder>[,<folder>] scaffolds and designs only the named warehouse folders (default: every folder); --auto designs every board to completion without pausing for decisions, one lane per subject area; --theme <name>, --currency <symbol>, --title <text>, --logo <path> pass through to the scaffold's meta.yml and landing page; --no-warehouse skips the warehouse dry-run, the profiling and the renders; --force overwrites boards that already exist under charts/"
preconditions:
  - artifact: dbt
    action: validate
    outcome: PASS
auto_validate: false
produces:
  - type: document
    path: "<dbt_project_path>/charts/<subject_area>.yml"
    description: "One dbt Charts board per warehouse subject area, read through ref() from the dbt models"
  - type: document
    path: "<dbt_project_path>/dbt_charts.yml"
    description: "The dbt Charts project anchor with a dbt_profile source; written only if absent"
  - type: document
    path: "<dbt_project_path>/charts/meta.yml"
    description: "Project-wide board defaults (theme, frame width); written only if absent"
  - type: document
    path: "<dbt_project_path>/charts/index.yml"
    description: "The landing page dct serves at /, one card per board, optional logo; written only if absent"
  - type: report
    path: "dev/dbtcharts_generation_report.md"
    description: "What the scaffold proposed, what the agent kept, changed or dropped, and every needs_human item with its resolution"
delegates_to:
  - utils/precondition_gate
  - utils/semantic_layer_developer_delegate
  - utils/stale_artifact_check
  - utils/jira_sync
  - utils/docstore_sync
description: Generate dbt Charts boards, one per warehouse subject area, from the dbt manifest and catalog — a deterministic scaffold inventories the models, the agent designs each board into a dashboard (KPI row with deltas, hero trend, breakdowns, table), dct validates and renders them; --auto runs the design for every subject area without pausing
argument-hint: <release-folder> [--subject-area <folder>[,<folder>]] [--auto] [--theme <name>] [--currency <symbol>] [--title <text>] [--logo <path>] [--no-warehouse] [--force]
workload: judgment
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbtcharts Generate Command

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below, **unless `--auto` is given**. An auto run is a fan-out of one lane per subject area, and the orchestrating session dispatches those lanes itself under the lane contract in `specs/utils/director_operating_model.md` (Step 5); wrapping the whole run in one specialist agent that then spawns the lanes hides a stall from the orchestrator, because nothing records progress until that agent returns.

## Purpose

Produce a first set of dashboards for a release's warehouse layer in [dbt Charts](https://dbtcharts.com): YAML boards that live in the dbt project next to the models, query them through `ref()`, are validated by the `dct` CLI and rendered by it. One board per **subject area**, where a subject area is a folder under the warehouse layer (`models/warehouse/w_sales/`, `models/warehouse/wh_finance/`), which is how Wire's dbt conventions and most client projects already group facts and dimensions.

The command is in two halves, and the line between them is fixed:

1. **The scaffold is deterministic.** `scripts/dbtcharts_scaffold.py` reads dbt's own artifacts (`target/manifest.json`, and `target/catalog.json` for column types), classifies every model and column from the naming conventions (`_fact`/`_dim`/`_xa`, `_dt`/`_ts`, `_amount`, `_pk`/`_fk`, `is_`/`has_`), and writes the boards: for each fact a KPI row (record count and up to three formatted measures), a 24-month trend and a top-10 breakdown; for each dimension a record count and a breakdown. It also writes `charts/meta.yml` (theme, frame width) and `charts/index.yml` (the landing page) once. The same manifest and catalog always produce the same boards. Everything it could not decide goes to `needs_human.json` with a reason. Do not hand-write what it emits, and do not "improve" its SQL by hand before it has run.
2. **The design is judgement.** The scaffold's board is an inventory: one KPI per column, one line per month, one bar per category, for every table. Step 5 turns each into a dashboard to the shape in `skills/dbtcharts/board-design-brief.md`: the tables that matter, a KPI row with prior-period deltas, one hero trend over the last 24 months, a few breakdowns, a detail table, business names, and the data profiled first so nothing charts a null column. With `--auto` this runs to completion for every subject area, one lane each, without pausing for decisions; without it, the agent pauses per board where a choice is not obvious. Either way every choice is recorded, chart by chart, in the generation report.

`auto_validate: false`: the validate step runs `dct validate --warehouse`, a per-query dry run against the warehouse, so it is a separate command and a separate decision, as `dbt-validate` is.

## Usage

```bash
/wire:dbtcharts-generate 01-dbt-foundation
/wire:dbtcharts-generate 01-dbt-foundation --auto                  # design every board to completion, one lane per area
/wire:dbtcharts-generate 01-dbt-foundation --subject-area w_sales  # one subject area (its facts and the dimensions they join)
/wire:dbtcharts-generate 01-dbt-foundation --auto --currency '£' --theme vivid --title "Acme Warehouse" --logo docs/logo.svg
/wire:dbtcharts-generate 01-dbt-foundation --no-warehouse          # under warehouse_spend: none
/wire:dbtcharts-generate 01-dbt-foundation --force                 # rewrite boards that already exist
```

`--subject-area` takes the warehouse folder (`w_sales`) or its slug (`sales`). The board for an area covers every fact model in that folder and the dimensions those facts join to, regardless of the folder the dimension lives in (`wh_companies_dim` from `w_crm` is charted on the sales board when `wh_deals_fact` refs it or carries `company_fk`; the CRM board still carries it too).

## Prerequisites

- `dbt`: `validate: PASS` (enforced by the precondition gate). The boards read the models; unbuilt or failing models give charts of nothing.
- The `dct` CLI (`uv tool install dbt-charts`, or `pip install dbt-charts`). Step 2 checks and stops with the install line if it is missing.
- A dbt profile the boards can read through. `dbt_charts.yml` points at it by name; no credential is ever written into a board.

## Inputs

| Input | Where it comes from | Required |
|---|---|---|
| The dbt project | `status.md` `dbt_project_path` (or `migration.dbt_project_path`), else `dbt/`, `dbt_project/` or the repository root, whichever holds `dbt_project.yml` | always |
| `target/manifest.json` | `dbt parse` in that project (Step 3) | always |
| `target/catalog.json` | `dbt docs generate` in that project (Step 3); optional under `warehouse_spend: none` | recommended |
| `design/visualization_catalog.md`, `design/dashboard_visualization_catalog.csv` | `viz_catalog-generate`, `mockups-generate` | `dashboard_first` |
| The dashboards section of `requirements/requirements_specification.md` | `requirements-generate` | `full_platform`, `dbt_development` when present |
| `business_rules/register.md` | `business-rules-generate` | when present: measure names and definitions |
| `.wire/conventions/dbt.yml` or the framework default | conventions | always |
| `.wire/conventions/dbtcharts.yml` or `wire/conventions/dbtcharts.yml` | design conventions: theme, currency, windows, board shape, chart defaults, formats, naming and layout rules | always |
| `budget.warehouse_spend` | `status.md` | always |

## Workflow

### Step 1: Resolve the dbt project and the subject areas

1. Read `status.md`. Resolve `dbt_project_path` in the order given in Inputs. If no `dbt_project.yml` is found at any candidate, stop:

   ```
   Cannot generate dbt Charts boards without a dbt project.
   Paths checked: <each path>/dbt_project.yml
   Set dbt_project_path in status.md and re-run.
   ```

2. Resolve the warehouse layer path: `.wire/conventions/dbt.yml` `layers.warehouse.path` if the convention file names one, else `models/warehouse`. List its immediate subfolders; these are the subject areas. Models sitting directly in the layer folder are grouped by their `wh_<group>__` prefix, else under the layer folder's own name. A subject area's board covers the fact models in its folder **plus the dimensions those facts join to, wherever they sit**: the scaffold finds them from the manifest (the fact `ref()`s the dimension) and the catalog (a fact `<x>_fk` column matching a dimension's `<x>_pk`), and marks each one in `scaffold_summary.json` with `linked_from` and `linked_via`. A dimension can therefore appear on more than one board; its own folder's board still carries it.
3. Apply `--subject-area` if given. A name that matches no folder stops the command and lists the folders that exist.
3a. **Resolve the design convention.** `.wire/conventions/dbtcharts.yml` in the engagement repo if present (the client's house style wins), else the framework's `wire/conventions/dbtcharts.yml` (synced from the process registry; see `wire/schemas/convention-schema.md`). Read `presentation` (theme, frame width, currency, landing page title and logo), `windows` (KPI period, event period, trend months, stopped-feed anchor), `board_shape`, `chart_defaults`, `formats`, `render` and `profiling`. A command flag (`--theme`, `--currency`, `--title`, `--logo`) overrides the convention for this run and the report says so. Record which file resolved.
4. Say what will happen before it happens, in one sentence and a table: the subject areas, the model count in each, and whether the catalog will be generated (Step 3).

### Step 2: Check the dct CLI

Run `dct --version`. If it fails, stop:

```
dbt Charts CLI not found. Install it, then re-run:
  uv tool install dbt-charts      # or: pip install dbt-charts
```

Record the version in the generation report. Do not substitute another renderer; the deliverable is board YAML that `dct` validates and renders.

### Step 3: Produce the dbt artifacts the scaffold reads

In the dbt project directory:

1. `dbt deps` then `dbt compile` for `target/manifest.json`. `dct` derives model columns from `compiled_code`; a bare `dbt parse` writes none, and every Jinja-wrapped model then comes back as "contains no SELECT statement". Compile needs the profile but runs no model.
2. `dbt docs generate` for `target/catalog.json`, which is where column **types** come from. This reads the warehouse's information schema. Skip it when `budget.warehouse_spend` is `none` or `--no-warehouse` was passed, and say so: without the catalog the scaffold classifies columns by name convention only, and models with no `schema.yml` columns are reported as `no_column_metadata` rather than charted.

Use the release's dbt profile and target as `dbt-validate` does. A manifest older than the newest model file is regenerated, never reused.

3. **Keep `target/manifest.json` still while `dct` reads it.** On dbt Fusion every `dbt show` rewrites `target/manifest.json`, and `dct validate` and `dct render` read that file, so a lane profiling with `dbt show` while another lane or the orchestrator renders makes the render fail with `ERR-DBT-MANIFEST-UNREADABLE`. Every `dbt show` run during Step 5 therefore passes `--target-path <scratch dir>` (one directory per lane, outside the project's `target/`), and the orchestrator runs `dbt compile` once more before Step 6 so the shared manifest is current.

### Step 4: Run the scaffold

```bash
python3 <plugin>/scripts/dbtcharts_scaffold.py \
  --manifest <dbt_project_path>/target/manifest.json \
  --catalog  <dbt_project_path>/target/catalog.json \
  --out      <dbt_project_path>/charts \
  --layer-path <layer path from Step 1> \
  --dialect  <bigquery | snowflake | postgres | duckdb | redshift, from the dbt profile type> \
  --write-anchor <dbt_project_path>/dbt_charts.yml --profile <profile> --target <target> \
  --theme <presentation.theme> --currency <presentation.currency> --frame-width <presentation.frame_width> \
  --trend-months <windows.trend_months> --breakdown-limit <chart_defaults.ranking.limit> \
  --kpi-row-height <board_shape.kpi_row_height> \
  [--title <presentation.landing_page.title>] [--logo <presentation.landing_page.logo>] \
  [--subject-area <folders>] [--force]
```

The presentation flags carry the resolved convention's values (Step 1, 3a); a command flag given by the user overrides the convention's value. The scaffold itself reads no convention file and stays standard-library only.

The scaffold writes one board per subject area to `<dbt_project_path>/charts/<subject_area>.yml` (the folder name with its `w_`/`wh_` prefix stripped: `w_sales/` becomes `charts/sales.yml`), the anchor to `<dbt_project_path>/dbt_charts.yml` when none exists, and `charts/meta.yml` and `charts/index.yml` when absent. The anchor holds the sources registry only; dct 0.8 rejects any other key there. `--currency` defaults to `$` because that is the only symbol dct's presets carry; a GBP or EUR client passes its symbol and the scaffold switches to prefix formats. Read `charts/scaffold_summary.json` (boards, models, the date, measure and dimension columns chosen for each, chart counts) and `charts/needs_human.json` (every model not charted or charted with a gap: `unknown_role`, `no_column_metadata`, `no_date_column`, `no_measure_column`, `no_breakdown_dimension`, `empty_subject_area`).

The scaffold never overwrites an existing board without `--force`. A board the consultant has already curated is not regenerated silently; the summary lists it under `skipped_existing`, and the report says so.

### Step 5: Design each board

This is the judgement half. Work board by board to `skills/dbtcharts/board-design-brief.md`, and record every change in the generation report as a row: `board`, `chart`, `scaffold proposed`, `kept | changed | dropped | added`, `why`.

**With `--auto`:** the orchestrating session dispatches one lane per subject area (one subagent each, all at once, within `lanes_max`), each with the lane brief template from `specs/utils/director_operating_model.md` filled in:

```
Lane:          dbtcharts [<area>]
Release:       <release folder>
Task:          design charts/<area>.yml to skills/dbtcharts/board-design-brief.md, using <resolved convention>
Owns:          <dbt_project_path>/charts/<area>.yml; .wire/releases/<release>/dev/dbtcharts/<area>.png; .wire/releases/<release>/lanes/dbtcharts-<area>.md
State file:    .wire/releases/<release>/lanes/dbtcharts-<area>.md
Resume:        Read the state file first; skip every completed item. Rewrite it after each completed item, not at the end.
Budget:        <warehouse_spend setting>
Flat:          Do not spawn sub-agents.
Status:        Do not write status.md or execution_log.md.
Report:        Report once, at completion, at a stall, or at a decision you cannot make.
```

Each lane receives the brief, the reference board if one is curated already, the scaffold's board and its rows in `scaffold_summary.json` and `needs_human.json`, and the tool notes (the `--target-path` rule from Step 3). Its items, in order, each written to the state file as it completes: profiled, designed (`charts/<area>.yml` rewritten in place), warehouse-validated, rendered and inspected, linted, and `complete` with the report rows (`board`, `chart`, `scaffold proposed`, `kept | reshaped | dropped | added`, `why`), the tables kept and dropped, the profiling findings and the `needs_human` decisions for its area. Nothing pauses; a choice the brief does not settle is made and recorded in the state file.

The orchestrator watches the state files, not the lanes: a lane with no writes for 30 minutes is stalled and its remaining items are re-dispatched to a fresh lane with the same brief, which the resume contract makes safe. When every lane's state file says `complete`, the orchestrator reads them all, then does Step 6 over the whole set. The generation report (Step 7) is assembled from the state files, so no lane's work exists only in a conversation.

**Without `--auto`:** the same work, board by board in the foreground, pausing where the brief does not settle a choice (which fact leads the board, which of two measures is the headline) and asking.

0. **Profile.** `dbt show --inline` over each candidate model: null rates, distinct counts, date coverage, whether the feed still loads. A column that is mostly null, all zero, or a single snapshot is not charted; a feed that has stopped anchors its windows on its last loaded month and the board `notes:` says so. Record what was dropped and why.
1. **Names.** Replace the scaffold's mechanical titles with the business names the release already uses: the measure's name in the business rules register, the requirement's wording, the viz catalog's `visualization_name`. A KPI's `label:` and every other chart's `title:` must read as a person would say it ("Deal value by pipeline stage", not "Deals by pipeline stage (deal_amount)").
2. **Shape.** Rebuild to the brief: 4 to 6 KPIs from one query with prior-period deltas; one hero trend over the last 24 months; two to four breakdowns; one detail table; about 8 visualisations; no section headings. Pick the tables that matter to the subject area and drop the rest (mappings, bridge tables, `_xa` models the release did not ask for, dimension record counts) and record why. A subject area that will not fit one screen is split into `tabs:` by fact, or a second board.
3. **Add what the release asked for.** Where a viz catalog or a requirements dashboards section exists, every row in it becomes a chart, mapped with this fixed table, and a row that cannot be mapped is recorded as unmapped, never dropped:

   | Catalog `chart_type` | dbt Charts `type` |
   |---|---|
   | `KPI tile`, `KPI`, `single value`, `stat` | `kpi` |
   | `line`, `spline` | `line` |
   | `area` | `area` |
   | `bar`, `column`, `vertical bar` | `bar` with `style.orientation: vertical` |
   | `horizontal bar`, `hbar` | `bar` (horizontal by default) |
   | `doughnut`, `donut`, `pie` | `pie` |
   | `table`, `grid`, `data table` | `table` |
   | `scatter` | `scatter` |
   | `map`, `geo` | `map` |
   | `heatmap` | `heatmap` |
   | `text`, `markdown`, `note` | a `text:` row |
   | `funnel`, `gauge`, `waterfall`, `sankey`, `treemap` | not drawable in dbt Charts: record as unmapped with the reason |

4. **Resolve `needs_human`.** For each item decide: chart it (write the query by hand only for these, still through `ref()`), leave it out, or send it back to the dbt work (a fact with no date column is usually a modelling gap). Record the decision. An item with no recorded decision fails validate.
5. **Follow the convention, the brief and the dbt Charts design skill.** The resolved convention (Step 1, 3a) sets the numbers: KPI count and period, trend months, ranking limit, table limit, layout row splits, chart type per question, format presets, currency handling. `skills/dbtcharts/board-design-brief.md` is the checklist for applying them; `dct skills board-design` and `dct docs` are the reference for chart choice and every field name; never guess a key. Formats go in the family slot (`style.value.format`, `style.number_format`, `style.columns.<col>.format`), money takes the release currency, trends set `axis_x.time_unit: yearmonth` and `axis_y.position: left`. Keep the scaffold's rules that validate depends on: every query reads a model through `{{ ref('...') }}`; no `type: values` inline data; every query and chart carries `notes:`; every KPI has `label:` and every other chart `title:`; the board's `source:` is a name in `dbt_charts.yml`, never a connection.
6. **Conventions.** Run `scripts/lint_conventions.py --domain dbt` over any model the curation exposed as mis-named; a chart cannot fix a column called `amt`.

### Step 6: Validate and render

0. `dbt compile` once more in the dbt project, so `target/manifest.json` is current and no lane is still writing it (Step 3, point 3). Nothing below runs while a lane's `dbt show` can touch that file.
1. `dct validate <dbt_project_path>/charts/` (structure and, with the manifest present, `ref()` names and model columns). Fix every error and re-run until there are none. Record warnings by code in the report; `WARN-DBT-MODEL-COLUMNS-UNRESOLVED` on a model whose SQL `dct` cannot derive columns from is expected and is cleared by the warehouse run.
2. Unless `--no-warehouse` or `warehouse_spend: none`: `dct validate charts/ --warehouse`. On BigQuery this is a dry run and is not billed; on Snowflake, Postgres and Redshift it is an `EXPLAIN`. Fix every error.
3. Unless `--no-warehouse` or `warehouse_spend: none`: render each board for the reviewer, `dct render charts/<board>.yml --format png --output .wire/releases/<release>/dev/dbtcharts/<board>.png`, and render `charts/index.yml` the same way. Renders run the queries; under `warehouse_spend: estimate_required` or a cap, the cost governance rules of `specs/utils/director_operating_model.md` apply and the run is disclosed in the report.
4. **Lint against the convention.** `python3 <plugin>/scripts/lint_conventions.py --domain dbtcharts --convention <resolved convention> --path <dbt_project_path>/charts/` and the same over `dbt_charts.yml`. Fix every error (missing titles, labels or notes; a `serve:` key in the anchor; a raw-string regex). Warnings (KPI label length or prefix, a `## Section` row, a hidden endpoint label, a trend without `time_unit`, `DATE_TRUNC(d, MONTH)`) are fixed where the brief agrees and otherwise recorded with a reason.
5. **Render clean.** `dct render` prints `WARN-*` codes for what a reviewer would see: `WARN-KPI-LABEL-TRUNCATED`, `WARN-CHART-TITLE-TRUNCATED`, `WARN-SERIES-LABEL-TRUNCATED`, `WARN-LIKELY-CURRENCY-OR-PERCENT-MISSING-FORMATTER`, `WARN-Y-ENCODING-MOSTLY-NULL`, `WARN-QUERY-RETURNED-ZERO-ROWS`, `WARN-TEMPORAL-SINGLE-POINT`. Fix each in the board (shorter label, a format, a different column, a narrower window) and re-render until only `WARN-DBT-MODEL-COLUMNS-UNRESOLVED` remains. Look at every PNG; the warnings do not see a wrong-side axis or a chart that is technically clean and tells nothing.

### Step 7: Write the generation report

`.wire/releases/<release>/dev/dbtcharts_generation_report.md`:

- dct version, dialect, source name, profile and target
- the design convention that resolved (engagement override or framework default) and any flag that overrode a value
- the subject-area table from Step 1 with boards written, skipped and empty
- the curation table from Step 5, assembled from the lane state files under `lanes/` on an `--auto` run
- the catalog mapping table where a viz catalog exists, with unmapped rows
- every `needs_human` item and its decision
- the profiling findings per board: columns and tables dropped, stopped feeds and the windows chosen
- the validate results (structure, warehouse, or `not run` with the reason), the render warning count per board, and the render paths (boards and landing page)

### Step 8: Update Status

```yaml
dbtcharts:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: "{{TODAY}}"
  dct_version: "<x.y.z>"
  charts_dir: "<dbt_project_path>/charts"
  boards: []                 # one path per board written
  boards_skipped: []         # existing boards left alone (no --force)
  subject_areas: N
  charts_generated: N        # after design
  charts_scaffolded: N       # what the scaffold proposed
  design_mode: auto | guided # --auto lanes, or board by board in the foreground
  convention: ".wire/conventions/dbtcharts.yml | wire/conventions/dbtcharts.yml"   # which file resolved
  theme: vivid
  currency: "$"
  render_warnings: N         # across all boards, excluding WARN-DBT-MODEL-COLUMNS-UNRESOLVED; 0 to hand over
  needs_human: N             # items in needs_human.json
  needs_human_resolved: N    # must equal needs_human before validate can pass
  catalog_rows: N            # dashboard_first: viz catalog rows
  catalog_unmapped: N
  warehouse_validated: true | false | not_run
```

Then follow `specs/utils/stale_artifact_check.md` for artifacts downstream of this one.

### Step 9: Sync to Jira and the Document Store (Optional)

Follow `specs/utils/jira_sync.md` (artifact `dbtcharts`, action `generate`) and, if a document store is configured, `specs/utils/docstore_sync.md` with `artifact_id: dbtcharts`, `artifact_name: dbt Charts boards`, `file_path: .wire/releases/[release_folder]/dev/dbtcharts_generation_report.md`. A sync failure is logged and never blocks the command.

### Step 10: Report

```
## dbt Charts boards generated

**dct:**        <version> · dialect <dialect> · source <name> (profile <profile>, target <target>)
**Boards:**     N written under <charts_dir> (one per subject area), N skipped (existing)

| Subject area | Models | Charts proposed | Charts kept | needs_human |
|---|---|---|---|---|

### Design (<auto | guided>)
N charts scaffolded, N kept, N reshaped, N dropped, N added (viz catalog N), N needs_human items decided (N sent back to dbt)

### Validation
Structure: PASS / N errors fixed · Warehouse dry-run: PASS / not run (<reason>) · Renders: N PNGs under dev/dbtcharts/, N render warnings (0 to hand over)

### Next steps
1. /wire:dbtcharts-validate <release>
2. dct serve in <dbt_project_path> to walk the boards live
3. /wire:dbtcharts-review <release>
```

End with the commands that ran and the one that follows, in full (`specs/utils/director_operating_model.md` rule 7):

```
Ran: /wire:dbtcharts-generate <release> [flags]
Next: /wire:dbtcharts-validate <release>
```

## Edge Cases

### No `target/catalog.json` and models without `schema.yml` columns

The scaffold cannot see their columns and lists them as `no_column_metadata`. Either run `dbt docs generate` (Step 3) or document the models, then re-run. Do not write those boards by hand from memory of the SQL.

### A subject area folder with no fact or dimension

Reported as `empty_subject_area`; no board is written. Usually a folder of utility or mapping models; say so in the report.

### The client repository already has a `charts/` directory or a `dbt_charts.yml`

The anchor is never overwritten. Boards with the same file name are skipped without `--force`, and the report names them. Read the existing boards before curating; the scaffold's `source:` name must match a source the existing anchor declares.

### `warehouse_spend: none`

The catalog, the warehouse dry-run and the renders are skipped and each skip is named in the report and in `status.md` (`warehouse_validated: not_run`). The structural validation still runs. `dbtcharts-validate` records the warehouse check as `unverified`, which is not a pass.

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
