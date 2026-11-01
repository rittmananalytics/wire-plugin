---
description: Experimental: Generate a Looker Data App (Google's Data Apps toolkit, Lit) from the approved mockup chain and the semantic layer; one widget per catalog row, fields resolved against the explore, previewed locally. Looker only
argument-hint: <release-folder> [--app <slug>] [--slice <slice>]
---

# Experimental: Generate a Looker Data App (Google's Data Apps toolkit, Lit) from the approved mockup chain and the semantic layer; one widget per catalog row, fields resolved against the explore, previewed locally. Looker only

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
    'command': 'data_app-generate',
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
artifact: data_app
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - dashboard_extension
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: app
      description: "--app <slug>. Build one app when the catalog has several dashboard pages (default: one app per page, in catalog order)"
    - name: slice
      description: "--slice <slice>. In a release built from tickets, work on one slice of the release only (specs/utils/ticket_delivery.md)"
produces:
  - type: document
    path: "dev/data_app/<slug>/data_app.md"
    description: "What was built: the widget plan, the mockup cross-check, the preview address and every unmapped or unresolved item"
  - type: report
    path: "dev/data_app/<slug>/plan.json"
    description: "The deterministic widget plan from the catalog (wire/scripts/data_app_plan.py): one entry per catalog row, with the widget, chart type, resolved fields and every unmapped or unresolved item"
preconditions: dynamic
auto_validate: false
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
description: "Experimental: Generate a Looker Data App (Google's Data Apps toolkit, Lit) from the approved mockup chain and the semantic layer; one widget per catalog row, fields resolved against the explore, previewed locally. Looker only"
argument-hint: <release-folder> [--app <slug>] [--slice <slice>]

---

## Auto-Delegation

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding.

---

# data_app Generate Command

**Experimental.** Looker Data Apps is a Looker preview feature (Looker 26.18 or later, Looker-hosted instances only), and Google's toolkit changes between releases. Keep this marker until the artifact has run end to end on a client estate. `bi_tool: omni` is not supported yet: Omni apps are a later change with the same command names.

## Purpose

Build a Looker Data App on the approved semantic layer: a freeform, interactive page (KPI strip, charts with cross-filtering, a detail table, tabs where the mockup has them) that Looker serves as a dashboard-mounted extension. The app is written in Google's Lit runtime, one file per app, and every widget queries through the LookML explore as the viewing user. Google's toolkit does the authoring, preview and publish; this command adds the record, the gates, field resolution against the approved semantic layer, and the cross-check against the mockup the stakeholder signed off.

A Data App is not a LookML dashboard. It cannot be embedded, printed, scheduled or exported as LookML (the preview's limits), and a published app's dashboard must never be copied in Looker, because copies share one extension. Where the client needs any of those, `dashboards` is the right artifact; the two can run side by side on the same catalog.

## Usage

```bash
/wire:data_app-generate 20260115_acme_dashboards
/wire:data_app-generate 20260115_acme_dashboards --app sales-overview
```

## Prerequisites

Enforced by the precondition gate (`preconditions: dynamic`, see `wire/release-types/<project_type>.yaml`): the same gates as `dashboards` in each release type (the semantic layer validated or approved, or the mockups approved on `dashboard_extension`).

Outside Wire's record, on the consultant's machine and the client's Looker instance:

| Requirement | Who | How it is checked |
|---|---|---|
| Looker-hosted instance, 26.18 or later, Data Apps preview switched on (Admin, General, Previews) and the `inline_extensions` feature | Looker admin | `scripts/verify-install.py` in the toolkit; a publish fails with HTTP 404 on `/data_app_extension` otherwise |
| API keys enabled for the builder's user; `access_data`, `explore`, `see_user_dashboards`, `save_content`, `save_dashboards`; Manage Access, Edit on the publish folder | Looker admin | Google's `check-credentials.py` (Step 0) |
| Google's Data Apps toolkit installed (`bash <(curl -fsSL https://dl.google.com/looker-data-apps/install.sh)`), Python 3.9 or later | Consultant | Step 0 |

## Inputs

| Input | Where it comes from | Required |
|---|---|---|
| `design/dashboard_visualization_catalog.csv` | `mockups-generate` Step 4A | `dashboard_first`, `dashboard_extension`; used when present elsewhere |
| `design/dashboard_spec.md` | `mockups-generate` Step 4A (filters, interaction notes) | same |
| `design/mockups/*.html` | `mockups-generate` Step 3A (layout, reading order, palette) | same |
| the dashboards section of `requirements/requirements_specification.md` | `requirements-generate` | `full_platform`, `dbt_development` when there is no catalog |
| the semantic layer field list | `explore-model.py` against the live explore (Step 2) | always |
| `bi_tool`, `semantic_layer_model`, `semantic_layer_explore`, `data_apps_path` | `status.md` front matter, else `.wire/engagement/context.md` `data_apps:` | always |
| the toolkit path | `.wire/local/data_apps.yml` (`toolkit_path:`, git-ignored, per person) or `WIRE_DATA_APPS_TOOLKIT` | always |

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this command takes `--slice <slice>` and builds the one app the slice names (`specs/utils/ticket_delivery.md`, "The `--slice` option"). The slice must be in `tickets.yaml`; the gate evaluates the slice's dependencies; on a ticket branch the result goes to the ticket record and the ticket run log, not to `status.md` and `execution_log.md`.

## Workflow

### Step 0: Target and toolkit check

1. Read `bi_tool` from `status.md`. If it is not `looker`, stop:

   ```
   data_app supports Looker only in this release.
   bi_tool is <value>. Omni apps are planned under the same commands; nothing was written.
   ```

2. Check the toolkit. Never read `data-apps-config.json` yourself and never print its values:

   ```bash
   python3 <wire>/scripts/data_app_toolkit.py check
   ```

   It reports the toolkit path, its `VERSION` against `wire/data_apps/pinned_toolkit_version.txt`, whether `data-apps-config.json` is present (keys only, values masked) and whether `apps/` exists. An older toolkit than the pin stops the command and names the upgrade (`skills/toolkit-updater/SKILL.md` in the toolkit, run by the consultant, never by this command). A newer one is a warning, recorded in status. No toolkit, or no config, stops with the install one-liner above and `bash scripts/bootstrap.sh`.

3. Credentials, Google's own gate, run from the toolkit root:

   ```bash
   cd <toolkit> && python3 skills/data-app-creator/tools/check-credentials.py --json
   ```

   Exit 1 is a hard stop: report the tool's hint and the human action it names, and end the turn. Do not look for other credentials, do not write code.

### Step 1: Resolve the target

Read `status.md` and establish, stopping rather than guessing any of them:

1. **`project_type`**, which decides the tile source (Step 2).
2. **The semantic layer target**: `semantic_layer_model` and `semantic_layer_explore` from `status.md`, else from the approved `semantic_layer` artifact, else ask.
3. **`data_apps_path`**: where the app source lives in the client repo. From `status.md`, else `.wire/engagement/context.md` `data_apps.path`, else `<bi_project_path>/data_apps`; if none of those resolve, ask. The toolkit's own `apps/` folder is a working copy, never the source of truth: it is outside the repo and the installer may replace everything around it.
4. **The app slug(s)**: `--app <slug>`, else one app per `dashboard_page` in the catalog (slug: lower case, hyphens, from the page name). A single-page catalog is one app.

```
Cannot generate a data app without a semantic layer target and a source path.

Resolved so far:
  bi_tool:                  looker
  semantic_layer_model:     [value or MISSING]
  semantic_layer_explore:   [value or MISSING]
  data_apps_path:           [value or MISSING]
  toolkit:                  [path, version]

Set the missing values in status.md (or context.md) and re-run, or supply them now.
```

### Step 2: Resolve the inputs

**The widget list is read, never invented.** Its source depends on `project_type`, exactly as for `dashboards`:

| `project_type` | Widget source | If absent |
|---|---|---|
| `dashboard_first`, `dashboard_extension` | `design/dashboard_visualization_catalog.csv`, one widget per row | stop, and name `mockups-generate` as the command that writes it |
| `full_platform`, `dbt_development` | the catalog when present; otherwise the dashboards section of `requirements/requirements_specification.md`, written out as a catalog CSV in `dev/data_app/<slug>/catalog.csv` first, so the plan has one input shape | stop, and name the missing artifact |

**The field list** comes from the live explore, through Google's tool, run from the toolkit root, and is kept in the release record so validate and review read the same list:

```bash
cd <toolkit> && python3 skills/data-app-creator/tools/explore-model.py <model> <explore> --json \
  > <release>/dev/data_app/<slug>/fields.json
```

Do not pass `--probe` or `--sample` without `--fields`: an unscoped probe runs one query per field. The file holds field names, types and descriptions only; it carries no credential.

Read `design/dashboard_spec.md` for the filter list (`## Filter Dimensions`) and the interaction notes (`## Interaction Notes`: tabs, cross-filter, drill), and the mockup HTML for reading order and palette.

### Step 3: The widget plan (deterministic)

```bash
python3 <wire>/scripts/data_app_plan.py plan \
  --catalog design/dashboard_visualization_catalog.csv \
  --spec design/dashboard_spec.md \
  --fields dev/data_app/<slug>/fields.json \
  --model <model> --explore <explore> --app <slug> \
  --out dev/data_app/<slug>/plan.json
```

The script is the fixed part of this command, so two people generating from the same approved catalog get the same plan. It does four things:

1. **Maps each catalog row to a widget.** `chart_type` is mockup vocabulary; the table is fixed. Matching is case-insensitive and ignores surrounding whitespace and hyphens.

   | Catalog `chart_type` | Widget | `type` |
   |---|---|---|
   | `KPI tile`, `KPI`, `single value`, `stat` | `<app-kpi>` | |
   | `line`, `spline` | `<app-chart>` | `line` |
   | `area`, `areaspline` | `<app-chart>` | `areaspline` |
   | `bar`, `column`, `vertical bar` | `<app-chart>` | `column` |
   | `horizontal bar`, `hbar` | `<app-chart>` | `bar` |
   | `doughnut`, `donut` | `<app-chart>` | `donut` |
   | `pie` | `<app-chart>` | `pie` |
   | `table`, `grid`, `data table` | `<app-grid>` | |
   | `scatter` | `<app-chart>` | `scatter` |
   | `funnel` | `<app-chart>` | `funnel` |
   | `treemap` | `<app-chart>` | `treemap` |
   | `gauge` | `<app-chart>` | `gauge` |
   | `text`, `markdown`, `note` | a `.da-section-card` with the text, no query | |

   **An unrecognised `chart_type` is not a guess** (`map` and `geo` included: the runtime has no map widget). The row becomes an `<app-grid>` (a table shows the values without reshaping them) and is listed under `unmapped`. `data_app-validate` fails while any remains.

2. **Resolves every measure and dimension** against `fields.json`. A name is resolved when it matches a field exactly (`view.field`), or when it is a bare name and exactly one field in the explore ends in `.<name>`. Anything else is `unresolved`, and the widget is planned without that field. A field the semantic layer does not define is never written into the app.

3. **Gives each widget a stable id**, `da-<tag>-<slug of the title>` (`-1`, `-2` on a collision), the form Google's publisher uses, so the published widget ids match the plan and "Explore from here" resolves per widget.

4. **Carries the filters, tabs and cross-filter flags** from the spec: each filter dimension resolved the same way, each becoming an `<app-select>`; tabs from the interaction notes; `cross_filter: true` unless the notes rule it out.

Read `plan.json`. The counts at the bottom (`catalog_rows`, `widgets`, `unmapped`, `unresolved_fields`, `filters`, `filters_unresolved`) go into status unchanged.

### Step 4: Write the app

Read Google's authoring skill first, as a file: `<toolkit>/skills/data-app-creator/SKILL.md`, with `reference/LIT_DATA_APPS.md` and the recipes it names for the chart types in the plan (`python3 skills/data-app-creator/tools/get-recipe.py <recipe...>` from the toolkit root). Its rules apply in full. On top of them, Wire's rules are the ones `conventions/data_apps.yml` lists and the lint checks (Step 5); the rest of this step is what the plan fixes.

Write `<data_apps_path>/<slug>/app.js`, one file, in a single pass:

- **The JSDoc header** (`@title`, `@description`). Never remove the publish tags the publisher adds later (`@looker-dashboard-id` and the rest).
- **One widget per plan entry, in the mockup's reading order** (KPI strip, then chart rows, then the table), each with the plan's `id`, its catalog `visualization_name` as `title` or `label`, `looker-model` and `explore` (or `this.lookerModel` and `this.explore` in the constructor), and a `.query` whose `fields` are exactly the plan's resolved fields. A comment above each widget names the catalog row.
- **A widget with an unresolved field is written without that field** and keeps its id, so the gap is visible in the preview as well as in the plan. If every field of a widget is unresolved, write the card with the title and the text "field not in the semantic layer" and no query.
- **Filters through `getEffectiveFilters()`**, spreading `this.dashboardFilters` and `this.crossFilters` so Looker's own filter bar and cross-filtering reach every widget. One `<app-select>` per plan filter, with the spec's default value; no other dropdowns.
- **A widget's own filter (a `-NULL`, a fixed status) goes through `getEffectiveFilters(local)`**, never under `.query.filters`: the runtime takes a query's own `filters` in place of the shared `.filters`, and the widget silently loses the date window, the dropdowns and the cross-filters.
- **`cross-filter`** on every segmented chart (`column`, `bar`, `pie`, `donut`, `treemap`, `funnel`) when the plan says so; never on line, area, scatter or gauge charts.
- **Formats** from the field types in `fields.json`: `percent1` for a ratio measure, `usd` (or the client's currency) for an amount, `int` for a count. Ids and years unformatted.
- **Layout** as the mockup: the responsive `.da-*` grid classes by default; the coordinate grid (`cell="x y w h"`) only when the mockup's tiles must hold fixed positions. Tabs only where the spec has them.
- **Palette** from the mockup where the catalog or spec records it, through the runtime's `--app-*` tokens, so the delivered app matches what was approved.
- **Nothing invented.** No `.data=${[...]}` literal rows, no field the plan did not resolve, no credential, no second import, no `fetch()`.

Write the record, `dev/data_app/<slug>/data_app.md`: the plan summary, the choices made (layout, palette, formats), every unmapped and unresolved item, and the preview address (Step 5).

### Step 5: Lint, push to the toolkit, verify, preview

1. Wire's rules, from the repo:

   ```bash
   python3 <wire>/scripts/lint_conventions.py --domain data_apps \
     --convention <.wire/conventions/data_apps.yml if present, else <wire>/conventions/data_apps.yml> \
     --path <data_apps_path>/<slug> --new-project
   ```

   Fix every error. Each remaining warning gets a disposition in `data_app.md`: `fixed`, `justified` with a reason, or `acknowledged`.

2. Copy the source into the toolkit's working folder (the preview server refuses symlinks outside its root):

   ```bash
   python3 <wire>/scripts/data_app_toolkit.py push --app <slug> --source <data_apps_path>/<slug>
   ```

3. Google's verification, stages 1 to 3 (syntax, tile safety, query dry run against Looker):

   ```bash
   python3 <wire>/scripts/data_app_toolkit.py verify --app <slug>
   ```

   On a failure, read the hint, fix the repo copy, push and verify again; do not ask the user. Give up after five rounds and report what remains. Delegate the loop to a subagent when one is available, as Google's skill says, so the verify output stays out of this session.

4. Preview, from the toolkit root: `python3 skills/data-app-previewer/tools/start-preview.py apps/<slug>/app.js`. Open the preview in the tile sandbox mode (`&sandbox=true`) once: no `.loading` widgets left, no console errors. Record the two addresses in `data_app.md`: `http://localhost:8765/preview-server/?app=apps/<slug>/app.js` and the same with `&sandbox=true`.

### Step 6: Cross-check against the approved mockup

```bash
python3 <wire>/scripts/data_app_plan.py check \
  --plan dev/data_app/<slug>/plan.json --app-js <data_apps_path>/<slug>/app.js \
  --fields dev/data_app/<slug>/fields.json
```

| Check | Rule |
|---|---|
| Widget count | one widget id in `app.js` per plan entry, no more and no fewer |
| Titles | each widget's `title` or `label` is the catalog's `visualization_name` |
| Filters | every spec filter is an `<app-select>` or is listened to through `dashboardFilters` |
| Fields | every `fields` literal in `app.js` is in `fields.json` |
| Model and explore | the literals in `app.js` are the ones in `status.md` |

Differences are recorded in `data_app.md`, never silently accepted.

### Step 7: Update status

```yaml
artifacts:
  data_app:
    generate: complete
    validate: not_started
    review: not_started
    generated_date: "{{TODAY}}"
    bi_tool: looker
    experimental: true
    toolkit_version: "<VERSION>"       # the toolkit the app was written against
    semantic_layer_model: "<model>"
    semantic_layer_explore: "<explore>"
    data_apps_path: "<path>"
    apps:
      - slug: <slug>
        source: "<data_apps_path>/<slug>/app.js"
        record: "dev/data_app/<slug>/data_app.md"
        catalog_rows: N
        widgets: N                    # must equal catalog_rows
        unmapped: N                   # chart_type not in the Step 3 table, written as a table
        unresolved_fields: N          # measures or dimensions with no semantic layer field
        filters: N
        filters_unresolved: N
        lint_errors: 0
        lint_warnings: N
        verify: pass | fail | unverified
        preview: "http://localhost:8765/preview-server/?app=apps/<slug>/app.js"
        looker_dashboard_id: null     # written by /wire:data_app-publish
        published_date: null
```

### Step 8: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md`: artifact `data_app`, action `generate`, status as written.

### Step 9: Sync to Document Store (Optional)

Follow `specs/utils/docstore_sync.md` with `artifact_id: data_app`, `artifact_name: Data App`, `file_path: .wire/releases/[release_folder]/dev/data_app/<slug>/data_app.md`. A failure is logged and does not block.

### Step 10: Confirm and suggest next steps

```
## Data App Generated (experimental)

**App:**      <slug>  ·  source <data_apps_path>/<slug>/app.js
**Model:**    <model> · explore <explore>
**Toolkit:**  <version> (pinned <pin>)
**Preview:**  http://localhost:8765/preview-server/?app=apps/<slug>/app.js

### Coverage
Catalog rows:        N
Widgets:             N
Unmapped chart type: N   [row, chart_type given]
Unresolved fields:   N   [widget, field]
Spec filters:        N   (N unresolved)

### Verification
Lint:    N errors, N warnings
Verify:  stages 1-3 pass | fail [hint] | unverified

### Mockup cross-check (Step 6)
[PASS, or one line per difference]

### Next Steps

1. Open the preview, in the sandbox mode too, and check it against the mockup
2. **Validate**: /wire:data_app-validate <release>
3. **Review with stakeholders**: /wire:data_app-review <release>
4. Publishing to Looker is a separate, confirmed step: /wire:data_app-publish <release>
```

Any non-zero `unmapped` or `unresolved_fields` count is stated here and in status. The app is not finished while either is above zero, and `data_app-validate` fails on both.

## Gemini CLI

The same steps. Gemini reads `<toolkit>/skills/data-app-creator/SKILL.md` and Wire's `skills/data-apps/SKILL.md` as files, and runs the scripts as shown.

## Edge Cases

### `bi_tool` is not `looker`

Step 0 stops. Nothing is written. Record the request in `decisions.md` if the client wants an Omni app, so the later change has a reader.

### The toolkit is older than the pin

Step 0 stops and names the upgrade. An app written against an older runtime may publish and still miss a rule this spec relies on (widget ids, the `cross-filter` attribute, `pivot-by`).

### Google's credential check fails

Hard stop, as Google's skill requires. Report the hint verbatim and end the turn.

### A catalog row's `chart_type` is not in the Step 3 table

The widget is written as `<app-grid>` and listed under `unmapped`. `data_app-validate` Check 3 fails while any remains, so the fallback cannot become the delivered app by default.

### A measure or dimension does not exist in the explore

Listed under `unresolved_fields`; the widget is written without it. `data_app-validate` Check 4 fails while any remains. The fix is in the semantic layer, or in the catalog, never an invented field name.

### The catalog is missing on a `dashboard_first` or `dashboard_extension` release

Stop and name `mockups-generate`. Do not fall back to the requirements on a release type whose widget source is the catalog: that substitutes an unapproved widget list for the one the stakeholder signed off.

### `verify-app.py` stage 4 (headless browser)

Not run by this command (`--no-browser`). The consultant looks at the preview; stage 4 is a convenience, not evidence.

## Output

This command creates:

- `<data_apps_path>/<slug>/app.js`, the app source, in the client repo
- `dev/data_app/<slug>/plan.json`, `fields.json`, `data_app.md` in the release
- a copy of `app.js` in `<toolkit>/apps/<slug>/`, for preview and publish only
- `status.md` `artifacts.data_app` with the counts above
- one row in `execution_log.md`

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
| YYYY-MM-DD HH:MMZ | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
```

### Field Definitions

- **Timestamp**: Current date and time **in UTC**, written `YYYY-MM-DD HH:MMZ`
  (24-hour, a literal `Z` after the minutes, no `T`, no seconds, no offset):
  `2026-10-17 14:05Z`. Get it with `date -u +"%Y-%m-%d %H:%MZ"` (or
  `python3 <wire>/scripts/log_time.py now`), never from the local clock. The
  same form is used for every time written into a log row, including an
  original time quoted in Detail (`ran 2026-10-17 14:28Z`), in the release log
  and in ticket run logs. From Wire 4.4.3; see "Time zones" below.
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
  - `blocked` — `specs/utils/precondition_gate.md` Step 2 stopped the command on an unmet blocking precondition and the consultant chose not to override; Detail is `gate: <dep_artifact>.<dep_action> required <outcome>, was <actual>` and the Command cell carries the command in full. The Wire mod's commands band shows these rows as `Not run: <command>, gate: <...>`
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

  When a persona is set for the run (`specs/utils/personas.md`), add
  ` as <persona>` to the value: `typed as delivery-manager`,
  `orchestrator [a1b2c3] as delivery-manager`. No persona: the value alone.

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
| YYYY-MM-DD HH:MMZ | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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
   Rows are compared as "Time zones" below says.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Update `status.md` keys in place, then check the file.** When a command
   records a result in `status.md`, it changes the existing key; it never adds
   a second copy of a key in the same block. A value worth keeping (an earlier
   approval date) moves to a `prior_<key>` field or stays in this log, never
   in a duplicate key, because YAML keeps only the last copy and ignores the
   first without an error (wire-plugin#2). The same applies to anyone editing
   the file by hand or by script. After writing `status.md` and before
   appending the row, run `python3 <wire>/scripts/status_file.py check
   .wire/releases/<release_folder>`. If it reports a problem in a line this
   command just wrote, fix it now. If the problem was there before, leave it,
   say so in the output and point to `/wire:status-sync <release_folder>`
   (`specs/utils/status_sync.md` Step 1b). In orchestrated mode the
   orchestrating session runs the check when it writes `status.md` from a
   lane's state file.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.
9. **One time zone.** Every Timestamp, and every time quoted in Detail, is UTC
   with the `Z` suffix. A row is never written in local time, and a time
   with no zone is never converted by guessing the zone it was written in.
10. **Review rows say what they are.** A review result recorded from a merged
    pull request, not from a review command run, follows
    `specs/utils/status_sync.md` Step 4g: By is the approver, Detail says
    `recorded from PR #<n> approved by <name>`, and Session is what ran the
    roll-up.

## Time zones

From Wire 4.4.3 every Timestamp is UTC, `YYYY-MM-DD HH:MMZ`. Before that the
rule said local time, and logs mixed UTC rows with rows in the writer's local
time, so a ticket could appear to close before it opened.

- **Writing.** `date -u +"%Y-%m-%d %H:%MZ"`. A row's time is the UTC time the
  command finished. A roll-up row's Timestamp is the UTC time of the roll-up.
- **Rows with no zone.** `YYYY-MM-DD HH:MM` without `Z` is a row written
  before 4.4.3. It stays valid, is never rewritten, and is read as "zone
  unknown": it may be in any zone from UTC-12 to UTC+14.
- **Anything else** (`2026-10-17T14:05Z`, `14:05+01:00`, `14:05 BST`) is
  unparseable and reported as such.
- **Ordering** (rule 6, `/wire:status-sync` Step 4f). Two rows in the same
  form compare on the values written. A UTC row next to a zone-unknown row is
  out of order only when no zone in that range puts the pair in order; when
  some zones do and some do not, the pair is `zone_unknown`, listed for
  information and not a defect. A log that changes from local time to UTC in
  British summer time (`15:05` then `14:10Z`) is therefore not flagged.
- **Never earlier than the last row.** A roll-up stamps its rows with the
  later of now and the last row's time when the last row is UTC. A last row
  with no zone is not copied into a new row.

The rule is implemented in `<wire>/scripts/log_time.py` (`now`,
`check <execution_log.md>`), used by `ticket_delivery.py merge-log` and tested
by `wire/tests/core/validate_execution_log_order.py`. The Wire mod's metrics
backfill (below) reads both forms: it matches a row on its command and date,
with a day's slack, not on its time.

## Metrics Backfill (Claude Code)

From 4.1.0 the Wire mod (`hooks/register.ts`, a function hook in the Claude
Code plugin) fills the metric cells. It replaces the `Stop` settings hook
(`hooks/wire-metrics.sh` and `wire_metrics.py`), which re-read the session
transcript after each turn.

1. Each Wire command opens a run when it starts: a typed `/wire:` command, or
   a Wire command called through the Skill tool by the orchestrating session,
   a lane or Autopilot.
2. Every model request adds its measured usage to the run open in its own
   loop (the main session, or one subagent). Counts come only from the usage
   the API reports, never estimates.
3. When that loop's turn ends, the run closes and the mod fills the
   Duration (only if still `n/a`), Tokens and Cost cells of the newest row
   whose Command cell names the command, whose Tokens cell is still `n/a`, and
   which is dated no earlier than the day before the run started (a date, not
   a time, because commands write the row's time themselves and it is often
   rough). It
   never touches another cell or row, and never widens a row without the
   metric columns.
4. A row written after the run closed (an orchestrating session writing a
   lane's row once the lane reports) is filled when that write happens.
5. Cost comes from the mod's price table; an unrecognised model leaves Cost
   at `n/a` with Tokens filled.

`/wire-usage` prints the session's runs with their duration, tokens and cost;
`/wire-ran` prints each run in full with its result (4.5.0), as the band above
the prompt draws it. The plugin's `metrics` option, or `WIRE_METRICS=false`,
turns the backfill off. On runtimes without the mod (Gemini CLI), the metric cells keep the
values the workflow wrote.

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
| 2026-02-22 14:30Z | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35Z | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40Z | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12Z | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00Z | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15Z | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30Z | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00Z | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15Z | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00Z | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30Z | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45Z | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00Z | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05Z | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20Z | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
| 2026-02-25 11:02Z | /wire:data_model-generate | complete | ticket CUS-199, ran 2026-02-25 09:40Z: 4 tables | Jane Smith | orchestrator [d4e5f6] | 9m 12s | 201544 | $1.51 |
| 2026-02-25 11:02Z | /wire:data_model-review | approved | recorded from PR #64 approved by John Doe (ticket CUS-199, approved 2026-02-25 10:55Z) | John Doe | orchestrator [d4e5f6] | n/a | n/a | n/a |
```

The last two rows are a ticket roll-up (`specs/utils/status_sync.md` Step 4g)
run by an orchestrating session: the first was rolled up from the ticket's run
log; the second records a review result from the ticket's merged pull request,
so By is the approver, Session is the session that ran the roll-up, and the
metric cells stay `n/a` because no review command ran.
