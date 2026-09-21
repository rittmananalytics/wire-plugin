---
description: Generate dashboard mockups
argument-hint: <project-folder>
---

# Generate dashboard mockups

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
    'command': 'mockups-generate',
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
command: generate
artifact: mockups
domain: design
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Generate mockups from design and requirements
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# mockups Generate Command

Follow `specs/utils/dashboard_mock_delegate.md` before executing the workflow below.

## Purpose

Generate dashboard mockups based on requirements. Supports two modes:
- **Dashboard-first mode** (`dashboard_first` projects): Generates pixel-accurate interactive Looker HTML mockups directly using the `looker-dashboard-mockup` skill, along with a visualization catalog CSV and dashboard specification markdown for downstream use
- **Standard mode** (all other project types): Generates ASCII wireframe mockups directly from requirements

## Usage

```bash
/wire:mockups-generate YYYYMMDD_project_name
```

## Prerequisites

Enforced by the precondition gate (`preconditions: dynamic` — see
`wire/release-types/<project_type>.yaml`), release-type dependent:

- **`dashboard_first`**: `requirements`: `review: approved`. Mockups are built
  directly from the SoW/requirements — there's no separate data model yet at
  this point in the sequence (mockups feed `viz_catalog`, which in turn
  informs `data_model`).
- **`full_platform`** (and any other regular release type): `data_model`:
  `review: approved`. Mockups here illustrate an already-designed data model.

## Workflow

### Step 0: Determine Mode

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Parse YAML frontmatter to extract `project_type`
3. If `project_type` is `dashboard_first` → follow **Dashboard-First Mode** (Step 1A onwards)
4. Otherwise → follow **Standard Mode** (Step 1B onwards)

Also verify prerequisites:
- Check `artifacts.requirements.review` is `approved`
- If not, show error and suggest `/wire:requirements-review <project>`

---

## Dashboard-First Mode (for `dashboard_first` projects)

### Step 1A: Read Requirements and Plan Dashboards

**Process**:
1. Read `.wire/<project-folder>/requirements/requirements_specification.md`
2. Read any files in `.wire/<project-folder>/artifacts/` (SOW, supplementary materials)
3. From the requirements, extract:
   - The primary use case or domain (e.g., "student retention analytics", "retail sales dashboard")
   - Key questions to be answered / jobs-to-be-done
   - Known data sources and their general nature
   - Target audience and their roles
   - Suggested dashboard pages / tabs (group related questions)

4. Plan the dashboard structure:
   - Determine the number of dashboard pages/tabs (typically 2–5)
   - For each page, identify: KPI tiles (up to 6), charts (type, axes, series), data table columns
   - Identify filter dimensions that should appear as filter pills
   - Invent realistic but anonymised sample data consistent with the domain

### Step 2A: Read the Design System Reference

**Before writing any HTML**, read the Looker design system reference:

```
wire/skills/looker-dashboard-mockup/references/design-system.md
```

This file contains all CSS custom properties, component class definitions, Chart.js configuration
patterns, table markup patterns, and the full sidebar/header HTML structure.
Do not guess at colours or class names — use the reference verbatim.

### Step 3A: Generate HTML Mockup(s)

For each dashboard page (or for a single tabbed dashboard), generate a **complete, self-contained HTML file**:

**File output path**: `.wire/<project-folder>/design/mockups/<dashboard-slug>.html`

The HTML must include:
- Full Looker UI chrome: header with logo mark SVG, teal sidebar with nav sections, title bar with breadcrumb and action icons, filter pills bar, tab bar
- KPI stat cards with coloured top bars (`--card-accent` cycling through `--chart-1` to `--chart-6`)
- Chart.js-powered interactive charts (line, bar, doughnut, horizontal bar, area — as appropriate)
- A data table with bottom Data/Results/SQL tabs and row-count indicator
- Footer with dashboard name, disclaimer, "Prepared by Rittman Analytics · [date]"

**HTML structure**:
```html
<head>
  Google Sans font import
  Chart.js CDN (4.4.1 from cdnjs)
  <style> — full CSS from design-system.md
</style>
<body>
  <header>
  <div class="body">
    <aside class="sidebar">
    <main class="main">
      <div class="titlebar">
      <div class="filter-bar">
      <div class="tab-bar">
      <div class="content">
        <!-- KPI grid, chart rows, table, bottom chart row -->
  <footer>
  <script>
    Chart.defaults setup + one new Chart() per canvas
    toggleSidebar(), setActive(), switchTab() helpers
  </script>
```

**Layout rules**:
- KPI grid: `grid-template-columns: repeat(N, 1fr)` where N = number of KPIs (max 5)
- Two charts side by side: `grid-template-columns: 3fr 2fr`; three charts: `grid-template-columns: 2fr 1fr 1fr`
- Canvas heights: line/area `200px`, doughnut `200px` (cutout `62%`, legend right/bottom), horizontal bar `180px`, vertical bar `200px`
- Data realism: realistic domain values with K/M suffixes, trend arrows (↑↓→), RAG badge colours

If the project has multiple distinct dashboard areas, generate one HTML file per dashboard, saving each as `<dashboard-slug>.html` in the mockups folder. For a single multi-tab dashboard, use one file with tab switching.

Save each generated file to `.wire/<project-folder>/design/mockups/`.
Create a brief `mockups_index.md` in the same folder listing each file with one-line descriptions.

### Step 4A: Generate Visualization Catalog and Dashboard Spec

Immediately after generating the HTML mockup(s), produce the two downstream artifact files that the visualization catalog command needs. Since you have complete knowledge of what you just generated, produce these without further input:

**File 1**: `.wire/<project-folder>/design/dashboard_visualization_catalog.csv`

```csv
dashboard_page,visualization_name,chart_type,measures,dimensions
[page],[viz name],[bar/line/doughnut/table/KPI/etc.],[measure1; measure2],[dim1; dim2]
```

One row per chart, KPI tile, and table in the mockup. For KPI tiles use `chart_type = KPI tile`.

**File 2**: `.wire/<project-folder>/design/dashboard_spec.md`

```markdown
# Dashboard Specification: [Dashboard Title]

## Purpose
[One paragraph describing what this dashboard is for and who uses it]

## Dashboard Pages

### [Page / Tab Name]
**Purpose**: [what this page shows]

#### Visualizations
1. **[Visualization Name]** — [chart type]
   - Measures: [list]
   - Dimensions: [list]
   - Description: [what it shows]

[Repeat for each visualization on this page]

## Filter Dimensions
[List of filter pills and their dimensions]

## Interaction Notes
[Drill-downs, cross-filtering, tab switching behaviour]
```

This spec is intentionally free of colour, font, and Looker chrome details — it captures only the
data visualization contents in enough detail for downstream LookML generation.

### Step 5A: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.mockups section:
   ```yaml
   mockups:
     generate: complete
     review: not_started
     generated_date: [today's date]
   ```
3. Write updated status.md

### Step 6A: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `mockups`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 7A: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `mockups`
- `artifact_name`: `Dashboard Mockups`
- `file_path`: `.wire/releases/[release_folder]/design/mockups/mockups_index.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 8A: Confirm and Suggest Next Steps

**Output**:
```
## Dashboard Mockups Generated Successfully

**Mockup file(s):** `design/mockups/<dashboard-slug>.html` (open in any browser)
**Index:** `design/mockups/mockups_index.md`
**Visualization Catalog:** `design/dashboard_visualization_catalog.csv`
**Dashboard Spec:** `design/dashboard_spec.md`

### Mockups Summary
[3–5 bullet points: tile names, chart types, table columns per page]

### Next Steps

1. **Open the HTML file(s)** in a browser to review — they are fully interactive
2. **Share with stakeholders** for visual feedback (attach the HTML or open in a browser together)
3. **Review mockups**: `/wire:mockups-review <project>`
4. After review approval, **generate visualization catalog**: `/wire:viz_catalog-generate <project>`
```

---

## Standard Mode (for non-dashboard_first projects)

### Step 1B: Read Inputs

**Process**:
1. Read `.wire/<project-folder>/requirements/requirements_specification.md`
2. Read any design documents in `.wire/<project-folder>/design/`
3. Identify the dashboards, reports, or UI screens that need mockups based on requirements

### Step 2B: Generate Wireframe Mockups

**Process**:
For each dashboard or screen identified in the requirements:

1. Create an ASCII wireframe mockup showing:
   - Dashboard layout with sections and panels
   - Chart/visualization placeholders with type labels (bar chart, line chart, KPI tile, table, etc.)
   - Filter bar with expected filter controls
   - Data labels showing which measures and dimensions power each visualization

2. Format each mockup as a markdown document with:
   - Dashboard title and purpose
   - Target audience
   - ASCII wireframe diagram
   - Data requirements table listing measures and dimensions per visualization
   - Filter specifications
   - Interaction notes (drill-downs, cross-filtering, etc.)

3. Save all mockups to `.wire/<project-folder>/design/mockups/`:
   - One file per dashboard: `mockup_[dashboard_name].md`
   - Summary file: `mockups_index.md` listing all mockups with links

### Step 3B: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.mockups section:
   ```yaml
   mockups:
     generate: complete
     review: not_started
     generated_date: [today's date]
   ```
3. Write updated status.md

### Step 4B: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `mockups`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 5B: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `mockups`
- `artifact_name`: `Dashboard Mockups`
- `file_path`: `.wire/releases/[release_folder]/design/mockups.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 6B: Confirm and Suggest Next Steps

**Output**:
```
## Mockups Generated Successfully

**File(s):** [list generated mockup files]
**Index:** `design/mockups/mockups_index.md`

### Next Steps

1. **Review mockups** with stakeholders: `/wire:mockups-review <project>`
2. After approval, proceed with data model design
```

---

## Edge Cases

### Prerequisites Not Met

If requirements not approved:
```
Error: Requirements must be approved first.

Current status: [status]

Complete requirements approval: /wire:requirements-review <project>
```

### Design System Reference Not Found

If `wire/skills/looker-dashboard-mockup/references/design-system.md` cannot be read:
- Proceed using built-in Looker design knowledge: teal sidebar (`hsl(195,55%,20%)`), white cards,
  Google Sans font, Chart.js 4.4.1 from cdnjs
- Note in output that the design system reference was unavailable

### Large Number of Dashboard Pages

If requirements indicate more than 5 dashboard pages:
- Consolidate related pages where possible
- Generate the most important 3–4 pages in full
- List the remaining pages in `mockups_index.md` as planned but not yet generated
- Recommend iterating with `/wire:mockups-review` to decide which to prioritise

## Output

This command creates:
- **Dashboard-first mode**: `design/mockups/<dashboard-slug>.html` (one or more interactive HTML files), `design/mockups/mockups_index.md`, `design/dashboard_visualization_catalog.csv`, `design/dashboard_spec.md`
- **Standard mode**: `design/mockups/mockup_*.md`, `design/mockups/mockups_index.md`
- Updates `status.md`

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
