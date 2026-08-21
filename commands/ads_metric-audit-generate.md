---
description: Inventory metric definitions, identify conflicts and coverage gaps
argument-hint: <release-folder>
---

# Inventory metric definitions, identify conflicts and coverage gaps

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

## Workflow Specification

---
description: Inventory existing metric definitions, identify conflicts and coverage gaps
argument-hint: <release-folder>
---

# Agentic Data Stack — Metric Audit Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Map every metric definition that exists across the client's semantic layer, BI tool, and ad-hoc SQL — then identify definition conflicts, coverage gaps against the most common analytical questions, and which metrics are safe to promote as first-class semantic layer citizens.

## Usage

```bash
/wire:ads_metric-audit-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `.wire/<release-folder>/status.md` with `project_type: agentic_data_stack`
- Access to at least one of: dbt Semantic Layer / MetricFlow YAML, LookML project, BI tool metric definitions, or dbt schema.yml measures

## Workflow

### Step 1: Read Context

1. Read status.md for `semantic_layer`, `bi_tool`, `dbt_project_path`, `warehouse`
2. If dataset_audit is complete, read `artifacts/dataset_audit.md` for domain list

### Step 2: Enumerate Metric Definitions

Collect metric definitions from every available source:

**dbt Semantic Layer / MetricFlow:**
```bash
# List all metrics
dbt sl list metrics
# Or read YAML directly
find <dbt_project_path> -name "*.yml" | xargs grep -l "^metrics:" | head -20
```

**LookML (Looker):**
```bash
# Find all measure definitions
grep -r "type: \(sum\|count\|average\|count_distinct\|max\|min\)" <lookml_path> --include="*.lkml" -l
```

**dbt schema.yml measures (if using dbt Semantic Layer but not MetricFlow):**
```bash
find <dbt_project_path> -name "*.yml" | xargs grep -l "measures:"
```

For each metric/measure found, record:
- Name
- Source (dbt SL / LookML / schema.yml / BI tool)
- Definition (SQL expression or aggregation type + field)
- Grain / time dimensions available
- Description (if any)
- Domain

### Step 3: Identify Definition Conflicts

Flag conflicts when the same business concept is defined differently across sources. Common conflict patterns:

| Conflict type | Example |
|---|---|
| Filter difference | `active_users`: Looker filters last 30 days; dbt SL filters last 90 days |
| Aggregation difference | `revenue`: Looker uses SUM(gross); dbt SL uses SUM(net) |
| Grain difference | `orders`: Looker counts order lines; dbt SL counts order headers |
| Name collision | Two metrics named `conversion_rate` measuring different funnels |

For each conflict, document both definitions and flag for governance_design resolution.

### Step 4: Identify Coverage Gaps

Compare the metric inventory against the most frequently asked analytics questions. Derive the question list from:

1. `artifacts/query_audit.md` (if query_audit has already run)
2. The SOW and engagement context — any KPIs mentioned
3. Direct consultation: ask the data team "What are the ten questions your executives ask most?"

For each high-frequency question, classify:
- **Covered**: a semantic metric answers it directly
- **Partial**: a metric exists but needs modification (missing dimension, different time grain)
- **Gap**: no metric covers this — raw SQL required today

### Step 5: Write Metric Audit Document

Write `.wire/<release-folder>/artifacts/metric_audit.md`:

```markdown
---
artifact: metric_audit
generated: YYYY-MM-DD
---

# Metric Audit

## Summary

| Metric | Count |
|---|---|
| Total metric definitions found | N |
| Definition conflicts identified | N |
| High-frequency questions covered by semantic layer | N/N (X%) |
| New metrics recommended | N |

## Metric Inventory

### [Domain: Orders]

| Metric | Source | Definition | Conflicts |
|---|---|---|---|
| total_revenue | dbt SL | SUM(net_amount) on fct_orders | ⚠️ Looker uses gross_amount |
| order_count | LookML | COUNT(DISTINCT order_id) | None |

## Definition Conflicts

### Revenue Definition Conflict

**dbt Semantic Layer:** `SUM(net_amount)` — excludes tax and returns  
**Looker:** `SUM(gross_amount)` — pre-deduction gross  

**Recommendation:** Standardise on `SUM(net_amount)` as `total_revenue`; add `gross_revenue` as a separate named metric to avoid silent mismatches.

## Coverage Gap Analysis

| Question | Status | Gap Detail |
|---|---|---|
| Revenue by channel last 30 days | ✅ Covered | `total_revenue` + `channel` dimension |
| Active customers this month | ⚠️ Partial | Metric exists; 30-day window missing |
| Marketing spend by campaign | ❌ Gap | No metric — raw SQL against ad tables required |

## Recommended New Metrics

| Metric | Domain | Priority | Definition |
|---|---|---|---|
| active_customers_30d | customers | High | COUNT DISTINCT customer_id WHERE last_order >= CURRENT_DATE - 30 |
```

### Step 6: Update Status

```yaml
metric_audit:
  generate: complete
  generated_date: YYYY-MM-DD
  metrics_found: N
  conflicts_found: N
  coverage_pct: X
```

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `metric_audit`
- `artifact_name`: `Metric Audit`
- `file_path`: `.wire/[release_folder]/artifacts/metric_audit.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Edge Cases

### No Semantic Layer Exists

If `semantic_layer: none` in status.md, the metric audit is primarily a gap analysis. Record all BI tool measures (Looker measures, Tableau calculated fields, etc.) as the existing definitions, grade coverage against the question list, and set `semantic_layer_maturity: none` in the audit. The semantic_layer_design phase will build from scratch.

### LookML Access Not Available

If the consultant cannot access the LookML project directly, ask them to run:
```bash
lookml-lint --list-measures <project_path>
```
or export a list of explores and their measures from the Looker IDE.

## Output

- `.wire/<release-folder>/artifacts/metric_audit.md`
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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
