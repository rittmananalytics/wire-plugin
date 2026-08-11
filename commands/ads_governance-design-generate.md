---
description: Produce canonical dataset model, deprecation plan, and tiering policy
argument-hint: <release-folder>
---

# Produce canonical dataset model, deprecation plan, and tiering policy

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
description: Produce the canonical dataset model, deprecation plan, ownership register, and tiering policy
argument-hint: <release-folder>
---

# Agentic Data Stack — Governance Design Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Convert the dataset audit findings into a concrete governance model: one canonical table per entity, a deprecation schedule, ownership assignments, and a tiering policy that the agent_config will enforce. This document is the authority that makes concept-entity ambiguity resolvable.

## Usage

```bash
/wire:ads_governance-design-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `dataset_audit.review: approved`
- `dataset_audit_decisions.md` exists with confirmed canonical table selections

## Workflow

### Step 1: Read Audit Decisions

Read:
- `.wire/<release-folder>/artifacts/dataset_audit.md`
- `.wire/<release-folder>/artifacts/dataset_audit_decisions.md`
- `.wire/<release-folder>/artifacts/metric_audit_decisions.md` (if approved)

### Step 2: Build the Canonical Dataset Model

For each domain, produce a canonical model entry:

```markdown
## Domain: Orders

**Canonical entity table:** `project.analytics.fct_orders`  
**Grain:** One row per order  
**Owner:** data-platform@company.com  
**Tier:** Curated  

**Key fields:**
| Field | Type | Description |
|---|---|---|
| order_id | STRING | Unique order identifier (surrogate key) |
| customer_id | STRING | FK to dim_customers |
| order_date | DATE | Date order was placed |
| net_revenue | NUMERIC | Revenue net of returns and tax |
| gross_revenue | NUMERIC | Pre-deduction gross amount |
| channel | STRING | Acquisition channel |

**Deprecation schedule:**
| Table | Sunset date | Migration notes |
|---|---|---|
| orders_raw | YYYY-MM-DD (+90 days) | Replace with fct_orders |
| revenue_v2 | YYYY-MM-DD (+90 days) | Replace with fct_orders |
```

Repeat for every domain confirmed in the audit review.

### Step 3: Write the Tiering Policy

Define the three-tier routing rule explicitly — this becomes a section in the agent_config skill:

```markdown
## Tiering Policy

When answering an analytical question, the agent MUST follow this routing order:

1. **Semantic tier** — check for a defined metric in the semantic layer first
   - dbt Semantic Layer: call `dbt sl query --metrics <metric_name>`
   - LookML / Looker: use the defined measure in the canonical explore
   - If a metric exists and answers the question: use it. Do not fall through to raw SQL.

2. **Curated tier** — if no semantic metric covers the question
   - Use only canonical tables listed in this governance design
   - Do not query deprecated tables even if they are more convenient
   - Write SQL against the canonical table and note the tier in the provenance footer

3. **Raw tier** — only if curated tables cannot answer the question
   - Document why the curated/semantic tiers were insufficient
   - Flag the gap as a potential semantic layer addition
   - Include the provenance footer tier: "Raw"
```

### Step 4: Write the Ownership Register

```markdown
## Ownership Register

| Domain | Canonical Table | Owner | Slack / contact | Review cadence |
|---|---|---|---|---|
| orders | fct_orders | data-platform | #data-platform | Monthly |
| customers | dim_customers | analytics-eng | #analytics | Monthly |
| marketing | fct_ad_spend | marketing-analytics | #marketing-data | Bi-weekly |
```

### Step 5: Write Governance Design Document

Write `.wire/<release-folder>/artifacts/governance_design.md` containing:
- Executive summary (one paragraph)
- Canonical dataset model (one entry per domain)
- Tiering policy
- Deprecation schedule with dates
- Ownership register
- Implementation checklist for canonical_models phase

### Step 6: Update Status

```yaml
governance_design:
  generate: complete
  generated_date: YYYY-MM-DD
  domains_covered: N
  tables_deprecated: N
  canonical_tables: N
```

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `governance_design`
- `artifact_name`: `Governance Design`
- `file_path`: `.wire/[release_folder]/artifacts/governance_design.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Output

- `.wire/<release-folder>/artifacts/governance_design.md`
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
