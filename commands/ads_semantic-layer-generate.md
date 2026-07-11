---
description: Implement semantic layer metrics from approved design
argument-hint: <release-folder>
---

# Implement semantic layer metrics from approved design

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
description: Implement semantic layer metrics from the approved design — MetricFlow YAML or LookML measures
argument-hint: <release-folder>
---

# Agentic Data Stack — Semantic Layer Generate

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.

## Purpose

Implement the metric and dimension definitions from `semantic_layer_design.md` in the client's semantic layer — either as MetricFlow/dbt Semantic Layer YAML, LookML measures and explores, or both where dual-layer configuration is in use.

## Usage

```bash
/wire:ads_semantic-layer-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `canonical_models.review: approved`
- `semantic_layer_design.review: approved`

## Workflow

### Step 1: Read Design

1. Read `artifacts/semantic_layer_design.md` — full metric and dimension specifications
2. Read `artifacts/semantic_layer_design_decisions.md` — any name changes from review
3. Read status.md `semantic_layer` field to confirm implementation target

### Step 2: Implement — dbt Semantic Layer (MetricFlow)

For dbt Semantic Layer projects, create or extend semantic model YAML files collocated with the dbt mart models:

```yaml
# models/marts/orders/fct_orders.yml (semantic extension)

semantic_models:
  - name: orders
    description: "Order-level fact model — grain is one row per order"
    model: ref('fct_orders')
    
    entities:
      - name: order
        type: primary
        expr: order_pk
      - name: customer
        type: foreign
        expr: customer_fk
    
    dimensions:
      - name: order_date
        type: time
        type_params:
          time_granularity: day
        expr: order_date
      - name: channel
        type: categorical
        expr: channel
      - name: status
        type: categorical
        expr: status
    
    measures:
      - name: total_revenue
        description: "Net revenue post-returns and tax"
        agg: sum
        expr: net_revenue
      - name: order_count
        description: "Distinct confirmed orders"
        agg: count_distinct
        expr: order_pk

metrics:
  - name: total_revenue
    description: "Net revenue from confirmed orders"
    label: "Total Revenue"
    type: simple
    type_params:
      measure:
        name: total_revenue
        filter: "{{ Dimension('order__status') }} = 'confirmed'"
  
  - name: active_customers_30d
    description: "Customers with at least one order in the last 30 days"
    label: "Active Customers (30d)"
    type: simple
    type_params:
      measure:
        name: customer_count
```

Verify after writing:
```bash
dbt parse
dbt sl list metrics
```

### Step 3: Implement — LookML (Looker)

For Looker-primary projects, add measures to the canonical explore views:

```lookml
# views/fct_orders.view.lkml

view: fct_orders {
  sql_table_name: `project.analytics.fct_orders` ;;
  
  # Dimensions
  dimension: order_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.order_pk ;;
  }
  
  dimension_group: order {
    type: time
    timeframes: [date, week, month, quarter, year]
    datatype: date
    sql: ${TABLE}.order_date ;;
  }
  
  dimension: channel {
    type: string
    sql: ${TABLE}.channel ;;
  }
  
  # Measures
  measure: total_revenue {
    type: sum
    sql: ${TABLE}.net_revenue ;;
    filters: [status: "confirmed"]
    description: "Net revenue post-returns and tax from confirmed orders"
    label: "Total Revenue"
    value_format_name: usd
  }
  
  measure: order_count {
    type: count_distinct
    sql: ${TABLE}.order_pk ;;
    filters: [status: "confirmed"]
    description: "Count of confirmed orders"
    label: "Orders"
  }
}
```

Verify by running the LookML validator in the Looker IDE, or:
```bash
lookml-lint <lookml_project_path>
```

### Step 4: Verify Metric Coverage

After implementation, verify that the semantic layer now covers the target questions from the query audit:

```bash
# For dbt Semantic Layer
dbt sl query --metrics total_revenue --group-by order__order_date__month --limit 5

# For LookML — use the Looker API or Explore in the UI
```

For each must-have SL-gap question from query_audit, confirm it is now answerable via the semantic layer. Mark `sl_coverage_pct` in status.md.

### Step 5: Update Status

```yaml
semantic_layer:
  generate: complete
  generated_date: YYYY-MM-DD
  metrics_implemented: N
  sl_coverage_pct: X  # % of must-have query patterns now answerable
  platform: dbt_semantic_layer  # or lookml
```

## Edge Cases

### No Existing Semantic Layer

If `semantic_layer: none` in status.md, initialise the semantic layer first:
- **dbt SL**: follow `/wire:semantic_layer-generate` to scaffold MetricFlow setup
- **Looker**: create the explore file and initial views before adding metrics

### Metric Fails After Implementation

If `dbt sl query` returns an error for a newly defined metric, check:
1. Entity join paths are fully specified (no ambiguous foreign key paths)
2. The referenced measure exists in the semantic model
3. The filter expression uses valid dimension references

## Output

- Modified YAML or LookML files in `<dbt_project_path>` or `<lookml_project_path>`
- Updated `status.md`

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
