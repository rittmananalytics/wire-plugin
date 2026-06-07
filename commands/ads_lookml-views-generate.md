---
description: Create or update LookML view files for new and restructured canonical models (Looker only)
argument-hint: <release-folder>
---

# Create or update LookML view files for new and restructured canonical models (Looker only)

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.7.5\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ads_lookml-views-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.7.5\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Create or update LookML view files for new and restructured canonical models — Looker projects only
argument-hint: <release-folder>
---

# Agentic Data Stack — LookML Views Generate

## Purpose

For every canonical model that was created or structurally changed during the `canonical_models` phase, create or update the corresponding LookML view file so the model is correctly exposed in Looker before `ads_semantic-layer-generate` adds metrics on top.

This step is **Looker-only**. When `bi_tool` is not `looker`, output a brief skip notice and set status to `skipped`.

## Usage

```bash
/wire:ads_lookml-views-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `canonical_models.review: approved`

## Workflow

### Step 1: Check BI Tool

Read `status.md`:

```yaml
bi_tool: looker   # must be "looker" to proceed
```

If `bi_tool` is not `looker`, output:

```
LookML Views — Skipped

bi_tool is not looker (found: <value>). This step is only required for Looker
projects. Proceeding directly to ads_semantic-layer-generate.
```

Then update status.md:

```yaml
lookml_views:
  generate: skipped
  validate: skipped
  review: skipped
```

Stop here.

---

### Step 2: Resolve LookML Project Path

Read `lookml_project_path` from status.md. If empty or not set, ask:

```
What is the path to the LookML project directory?
(The directory containing manifest.lkml or *.model.lkml files)
Examples: ./looker   ../analytics-looker   /workspace/looker-project
```

Once confirmed, store the path in status.md under `lookml_project_path`.

---

### Step 3: Read Canonical Model Changes

Read `.wire/<release-folder>/artifacts/canonical_models_lineage.md`.

Build two lists:

**New models** — created during `canonical_models` phase (did not exist before):
```
fct_orders        → project.analytics.fct_orders
dim_customers     → project.analytics.dim_customers
```

**Modified models** — restructured (columns renamed, added, or removed):
```
fct_subscriptions → columns: net_mrr renamed from mrr_amount; churn_date added
```

If `canonical_models_lineage.md` does not exist, read `artifacts/canonical_models.md` and ask the user to confirm which models are new vs pre-existing.

---

### Step 4: Scan Existing LookML Views

Scan `<lookml_project_path>` for all `.view.lkml` and `*.layer.lkml` files. For each file, extract `sql_table_name` or `derived_table` references to build a map of:

```
view_name → sql_table_name
```

Cross-reference against the new/modified model list to determine:

- **Missing views** — new canonical model, no existing view references its table
- **Stale views** — modified canonical model, existing view references its table (needs update)
- **Already covered** — view exists and matches; no action needed

---

### Step 5: Generate Views for New Canonical Models

For each missing view, generate a LookML view file following RA layered architecture conventions.

**File naming**: `<model_name>.view.lkml` in `<lookml_project_path>/views/` (or equivalent `base/` layer if the project uses the RA layered pattern).

**Template** — base view with dimensions only (measures added by `ads_semantic-layer-generate`):

```lookml
# Auto-generated by Wire Framework — agentic_data_stack / lookml_views phase
# Add measures in ads_semantic-layer-generate. Do not add measures here.

view: <model_name> {
  sql_table_name: `<fully_qualified_table_name>` ;;

  # ── Primary Key ──────────────────────────────────────────────────
  dimension: <pk_column> {
    primary_key: yes
    hidden: yes
    type: string
    sql: ${TABLE}.<pk_column> ;;
  }

  # ── Foreign Keys ─────────────────────────────────────────────────
  dimension: <fk_column> {
    hidden: yes
    type: string
    sql: ${TABLE}.<fk_column> ;;
  }

  # ── Dimensions ───────────────────────────────────────────────────
  dimension_group: <date_column> {
    type: time
    timeframes: [date, week, month, quarter, year]
    datatype: date
    sql: ${TABLE}.<date_column> ;;
  }

  dimension: <string_column> {
    type: string
    sql: ${TABLE}.<string_column> ;;
    label: "<Human Readable Label>"
    description: "<From schema.yml description>"
  }

  dimension: <numeric_column> {
    type: number
    sql: ${TABLE}.<numeric_column> ;;
    label: "<Human Readable Label>"
    value_format_name: decimal_2
  }
}
```

**Type mapping** — infer from dbt schema.yml column types:

| dbt / warehouse type | LookML dimension type |
|---|---|
| STRING, VARCHAR, TEXT | `string` |
| INTEGER, INT64, BIGINT | `number` |
| FLOAT, FLOAT64, NUMERIC | `number` (value_format_name: decimal_2) |
| BOOLEAN, BOOL | `yesno` |
| DATE | `time` (dimension_group, datatype: date) |
| DATETIME, TIMESTAMP | `time` (dimension_group, datatype: datetime) |
| ARRAY, STRUCT | omit — note in a comment for manual review |

Read column definitions from the model's `schema.yml` entry in the dbt project. Use `description` fields as the LookML `description` parameter. Convert `snake_case` column names to `Title Case` for labels.

**Primary key**: identify from `schema.yml` — look for the column with `_pk` suffix or a `unique` + `not_null` test combo. If ambiguous, add a comment: `# TODO: confirm primary_key — multiple candidates found`.

**Explore wiring**: after creating the view file, check whether an existing explore covers this domain. If yes, add a `join:` block referencing the new view in the explore file. If no explore covers this domain, note it in `artifacts/lookml_views_notes.md` — a new explore may be needed and is out of scope for this step.

---

### Step 6: Update Views for Modified Canonical Models

For each stale view (existing view where the underlying canonical model changed):

1. Open the existing view file.
2. For each **renamed column**: find the matching `dimension` or `dimension_group` block and update `sql: ${TABLE}.<new_column_name> ;;`. Add a comment: `# column renamed from <old_name> — Wire agentic_data_stack <date>`.
3. For each **removed column**: remove the matching dimension block. If the dimension is referenced in an existing measure (e.g. as a filter), add a `# TODO: dimension removed — review dependent measures` comment on the measure.
4. For each **new column**: add a new dimension block following the type-mapping table above.

Do not add or remove measures. Do not change explore join logic.

---

### Step 7: Write Notes File

Write `.wire/<release-folder>/artifacts/lookml_views_notes.md`:

```markdown
# LookML Views — Generation Notes

Generated: YYYY-MM-DD

## Views Created

| View | File | Canonical Model | Explores Updated |
|---|---|---|---|
| fct_orders | views/fct_orders.view.lkml | fct_orders | orders_explore |

## Views Updated

| View | File | Changes |
|---|---|---|
| fct_subscriptions | views/fct_subscriptions.view.lkml | mrr_amount → net_mrr renamed; churn_date added |

## Explores Needing Manual Review

List any new views not yet added to an explore. These must be wired into an
explore before the semantic layer step adds metrics — metrics on an unwired
view are unreachable in Looker.

## TODOs

Any ambiguous primary keys, ARRAY/STRUCT columns skipped, or complex joins
that need manual attention.
```

---

### Step 8: Update Status

```yaml
lookml_views:
  generate: complete
  generated_date: YYYY-MM-DD
  views_created: N
  views_updated: N
  explores_updated: N
  lookml_project_path: <path>
```

## Output

- New or updated `.view.lkml` files in `<lookml_project_path>`
- Updated explore files where new views were joined in
- `.wire/<release-folder>/artifacts/lookml_views_notes.md`
- Updated `status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

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
