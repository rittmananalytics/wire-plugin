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
