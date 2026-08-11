---
description: Configure and test adversarial review sub-agent
argument-hint: <release-folder>
---

# Configure and test adversarial review sub-agent

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
description: Configure and test the adversarial review sub-agent
argument-hint: <release-folder>
---

# Agentic Data Stack — Adversarial Config Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Configure, calibrate, and test the adversarial review sub-agent — the Claude instance that challenges every answer before it reaches the user. Anthropic measured a 6% accuracy gain from this step (at 32% higher token cost and 72% higher latency). This command documents the trade-off for the client and configures it to their latency and cost tolerance.

## Usage

```bash
/wire:ads_adversarial-config-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `agent_config.review: approved`
- `eval_suite.generate: complete`

## Workflow

### Step 1: Discuss the Trade-off

Present the trade-off to the consultant and note the client's decision:

```
## Adversarial Review — Configuration Decision

Based on Anthropic's measured results on their own analytics platform:

| Configuration | Accuracy gain | Token cost increase | Latency increase |
|---|---|---|---|
| With adversarial review | +6% | +32% | +72% |
| Without adversarial review | baseline | baseline | baseline |

At your current query volume:
- Estimated additional cost per month: £[X] (at current pricing)
- Estimated latency impact: queries take ~8–15s instead of ~5–8s

Recommended for: dashboards, async reports, any query going to leadership
Not recommended for: high-volume live chat interfaces with latency SLAs

**Recommended configuration:** Adversarial review ON for all queries (default)
```

Record the client's decision in status.md.

### Step 2: Configure Adversarial Review Prompt

The adversarial review is already embedded in the agentic data stack SKILL.md (Step 5 of agent_config/generate.md). If the client chose a standalone adversarial reviewer (separate agent call), configure it here:

```markdown
# Adversarial Reviewer System Prompt

You are the adversarial reviewer for the [client] agentic data stack. Your job is to 
challenge every answer the agentic data stack provides before it reaches the user.

You receive: the original question + the agent's proposed answer + the SQL or metric 
query used.

Systematically check:

1. **Source**: Is the answer from the correct canonical table? Would a different table 
   give a different result?

2. **Filter**: Are the WHERE clauses correct for the question? Revenue questions must 
   exclude returns and cancelled orders. Verify the filter matches the canonical 
   definition in DOMAIN_REFERENCE.md.

3. **Grain**: Is the result at the right granularity? If the question asked for monthly 
   and the answer is daily, flag it.

4. **Plausibility**: Does the number make sense? Apply these sanity checks:
   - Revenue per day should be £X–£Y (ask domain owner to set bounds)
   - Order count per day should be N–M
   - Customer count should be less than total registered users
   
5. **Definition**: Does the metric definition match what the question asked? 
   "Active customers" may differ from "all customers".

If all checks pass: respond "APPROVED — no issues found."
If any check fails: respond "REVISION REQUIRED — [specific issue]" and provide 
the corrected query or answer.

Never approve an answer you suspect is wrong, even partially.
```

### Step 3: Run Calibration Tests

Run 5 adversarial calibration tests — questions where the naive answer would be wrong and the adversarial check should catch it:

| Test | Naive answer | Expected adversarial catch |
|---|---|---|
| "Revenue last month" against wrong table | Returns gross not net | Filter check catches wrong revenue definition |
| "Active customers" without time filter | Returns all customers | Filter check catches missing 30-day window |
| "Orders this week" with daily grain | Returns daily rows | Grain check catches wrong aggregation |

Record which checks fired and whether corrections were accurate.

### Step 4: Set Production Configuration

In `agentic-data-stack-SKILL.md`, confirm the adversarial review section is active. For standalone configuration:

```yaml
# agent_config.yaml
adversarial_review:
  enabled: true
  mode: inline  # inline (built into main agent) | standalone (separate agent call)
  checks:
    - source
    - filter
    - grain
    - plausibility
    - definition
  plausibility_bounds:
    daily_revenue_min: 10000
    daily_revenue_max: 500000
    daily_orders_min: 50
    daily_orders_max: 5000
```

### Step 5: Update Status

```yaml
adversarial_config:
  generate: complete
  generated_date: YYYY-MM-DD
  mode: inline
  client_decision: enabled
  calibration_tests: 5
  calibration_pass_rate: 100%
```

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `adversarial_config`
- `artifact_name`: `Adversarial Config`
- `file_path`: `.wire/[release_folder]/artifacts/adversarial_calibration_results.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Output

- Updated `agentic-data-stack-SKILL.md` (adversarial section confirmed)
- `.wire/<release-folder>/artifacts/adversarial_config.yaml`
- `.wire/<release-folder>/artifacts/adversarial_calibration_results.md`
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
