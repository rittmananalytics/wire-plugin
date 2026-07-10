---
description: Stakeholder sign-off on canonical table selections and deprecation list
argument-hint: <release-folder>
---

# Stakeholder sign-off on canonical table selections and deprecation list

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
description: Stakeholder sign-off on dataset audit findings and deprecation recommendations
argument-hint: <release-folder>
---

# Agentic Data Stack — Dataset Audit Review

## Purpose

Present dataset audit findings to the data platform owner and domain leads. Agree which tables are canonical, which are deprecated, and confirm the governance maturity assessment before proceeding to design.

## Usage

```bash
/wire:ads_dataset-audit-review YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `dataset_audit.validate: complete` with result `pass` or `pass_with_warnings`

## Workflow

### Step 1: Surface Meeting Context

Search Fathom (if available) for any prior conversations about data quality, table proliferation, or "which table should we use":

```
Search Fathom for: "[client] canonical tables OR data governance OR which table OR revenue definition"
```

Surface any relevant excerpts — stakeholders may have strong prior opinions about specific tables.

### Step 2: Present Findings

Present the audit findings as a structured summary, leading with the governance grade and the highest-risk duplicate groups:

```
## Dataset Audit Review

**Overall governance grade: [B]**
**[N] tables across [N] domains**
**[N] near-duplicate groups — [N] tables recommended for deprecation**

### Domain Grades

| Domain | Grade | Top Issue |
|---|---|---|
| orders | B | 3 competing revenue definitions |
| marketing | C | No dbt management — raw tables primary |
| ... | | |

### Highest-Priority Deprecation Recommendations

1. **Revenue/orders group** (4 tables → 1 canonical)
   - Retain: `fct_orders`
   - Deprecate: `orders_raw`, `revenue_v2`, `fct_orders_v3`
   
2. **[Next group]**
```

### Step 3: Gather Reviewer Feedback

Ask the reviewer to confirm or modify:

1. **Canonical table selections** — Are the proposed canonical tables correct? Any disagreements?
2. **Deprecation list** — Are all proposed deprecations safe? Any tables on the list still actively used by upstream processes?
3. **Domain grades** — Do the governance grades reflect the team's own assessment? Any surprises?
4. **Missing domains** — Any business domains not covered in the audit?
5. **Timeline** — Is the 90-day deprecation sunset acceptable? Any tables needing longer notice?

### Step 4: Record Decisions

Record all reviewer decisions in `.wire/<release-folder>/artifacts/dataset_audit_decisions.md`:

```markdown
# Dataset Audit — Review Decisions

Reviewer: [Name], [Role]
Review date: YYYY-MM-DD

## Canonical Table Confirmations

| Domain | Canonical Table | Decision | Notes |
|---|---|---|---|
| orders | fct_orders | Confirmed | |
| customers | dim_customers | Modified — use dim_customers_v2 | v2 has GDPR fields required |

## Deprecation List Adjustments

Removed from deprecation list:
- `orders_raw`: Still used by finance team's Looker Looks — needs migration plan before sunset

Added to deprecation list:
- `customer_snapshot_2023`: Confirmed stale, safe to archive

## Governance Grade Adjustments

- marketing: D → C — consultant confirmed 2 dbt models exist but undocumented

## Open Items for Governance Design Phase

- Finance team dependency on `orders_raw` needs dedicated migration sprint
- Marketing domain needs dbt onboarding before canonical models phase
```

### Step 5: Update Status

```yaml
dataset_audit:
  review: approved  # approved | approved_with_conditions | rejected
  reviewer: Name
  review_date: YYYY-MM-DD
  decisions_recorded: true
```

### Step 6: Confirm Next Steps

```
## Dataset Audit Approved ✓

Canonical tables confirmed for [N] domains. [N] tables cleared for deprecation.

**Conditions / open items:**
- [Any conditions to resolve before proceeding]

**Next steps:**
- /wire:ads_metric-audit-review — if metric audit is complete
- /wire:ads_governance-design-generate — once all three audits are approved
```

## Edge Cases

### Reviewer Rejects Canonical Recommendations

Record the rejection with the reviewer's preferred canonical table. Re-run validate against the updated selections before proceeding to governance design.

### Deprecation Dispute

If a table is contested — multiple teams claim to need it — escalate to the platform owner. Do not proceed with canonical_models until the dispute is resolved. Record the open item in the decisions document.

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
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
