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

## Workflow Specification

---
description: Generate mockups from design and requirements
argument-hint: <project-folder>
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

- `requirements.review` must be `approved` in status.md

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
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
