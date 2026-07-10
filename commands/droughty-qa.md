---
description: LangGraph data quality agent report
argument-hint: <release-folder>
---

# LangGraph data quality agent report

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
description: Run the LangGraph data quality agent against the warehouse and produce a structured quality report
argument-hint: <release-folder>
---

# Droughty QA Command

## Purpose

Run `droughty qa` to execute a LangGraph-based data quality agent against the configured warehouse schemas. The agent queries the live data, interprets results via an LLM, and produces a structured quality report covering null rates, value distributions, anomalies, and referential integrity signals. The report lands in Wire's artifact directory as evidence for discovery, problem definition, and sign-off phases.

**Important**: The QA agent uses the OpenAI API and produces non-deterministic results — output will vary between runs. Treat the report as a starting-point analysis that a consultant should review critically, not an automated pass/fail gate.

## Usage

```bash
/wire:droughty-qa <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete, with an OpenAI API key in `profile.yaml`
- Warehouse accessible with SELECT permissions on the schemas in scope
- LangSmith credentials optional (provide in `profile.yaml` for lineage tracing)

## Workflow

### Step 1: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete`
3. Check for OpenAI API key

If no OpenAI key:
```
Error: droughty qa requires an OpenAI API key.

Re-run /wire:droughty-setup [release] and provide your OpenAI API key when prompted.
```

### Step 2: Scope Check

For large schemas (> 100 tables), warn:
```
⚠️  [n] tables are in scope. The QA agent will query each table and call OpenAI for interpretation.
This may take 10–30 minutes and will incur OpenAI API costs.

Proceed with all [n] tables, or restrict to specific schemas?
(Type 'all' to proceed, or a comma-separated list of schema names to limit scope)
```

### Step 3: Run droughty qa

```bash
droughty qa \
  --profile-dir ~/.droughty \
  --project-dir .
```

Stream output to the console. The agent produces a Mermaid DAG showing the quality check flow alongside the narrative report.

If the command exits non-zero, surface the full error output. Common failure modes:
- OpenAI rate limit exceeded — retry after a pause
- Warehouse query timeout — check that the role has SELECT on `INFORMATION_SCHEMA`
- LangGraph import error — verify Droughty installation: `pip show droughty`

### Step 4: Copy Report to Artifact Directory

The QA agent writes output to the configured paths. Copy and rename to Wire convention:

```bash
cp [droughty_output_path]/qa_report.* .wire/releases/[release]/artifacts/droughty/qa_report.md
```

### Step 5: Summarise Findings

Read the report and extract a brief summary for the consultant:
- Total checks run
- Issues flagged (by severity if available: critical / warning / info)
- Top 3–5 findings worth highlighting

### Step 6: Update status.md

```yaml
droughty:
  qa:
    status: complete
    checks_run: [n]
    issues_flagged: [n]
    critical_issues: [n]
    artifact: .wire/releases/[release]/artifacts/droughty/qa_report.md
    completed_date: [today]
    review_notes: "Non-deterministic output — consultant review required"
```

### Step 7: Confirm Output

```
## Data Quality Report Generated ✅

[n] checks run — [n] issues flagged ([n] critical, [n] warnings)

Artifact: .wire/releases/[release]/artifacts/droughty/qa_report.md

Review guidance:
- The QA agent uses LLM interpretation — findings are probabilistic, not deterministic.
  Review all flagged issues before citing them in client-facing documents.
- Re-running the command may produce different findings. This is expected.
- Critical issues (if any): [brief list of top critical findings]

This report is available to:
  /wire:problem-definition-generate   — embed quality findings as evidence
  /wire:discovery-analyses-generate   — feed into the Maturity analysis
```

## Output

This command creates:
- `.wire/releases/[release]/artifacts/droughty/qa_report.md`
- Updated `droughty.qa` block in `status.md`

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
