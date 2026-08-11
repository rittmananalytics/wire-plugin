---
description: Build Q&A eval suite with per-domain accuracy baselines and CI harness
argument-hint: <release-folder>
---

# Build Q&A eval suite with per-domain accuracy baselines and CI harness

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
description: Build the Q&A eval suite with per-domain accuracy baselines and CI harness
argument-hint: <release-folder>
---

# Agentic Data Stack — Eval Suite Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Build the evaluation suite that measures agent accuracy — the most important validation artifact in this release. Without evals, accuracy degrades silently. With them, every schema change that breaks an answer gets caught in CI before it reaches users.

This implements the offline evaluation infrastructure described in Anthropic's self-service analytics architecture: question-answer pairs per domain, run against every code change, with per-domain accuracy gates before domain launch.

## Usage

```bash
/wire:ads_eval-suite-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `agent_config.review: approved`
- All domain reference files reviewed and approved
- Access to correct answers for the eval questions (warehouse queries, prior reports, or domain owner sign-off)

## Workflow

### Step 1: Read Inputs

1. Read `artifacts/query_audit.md` — top question patterns per domain
2. Read each `DOMAIN_REFERENCE.md` — common questions section
3. Read `artifacts/semantic_layer_design.md` — metric definitions to test
4. Read the SOW for any KPIs explicitly mentioned

### Step 2: Generate Question-Answer Pairs

For each domain, generate at least 10 question-answer pairs. Aim for three categories:

**Semantic layer questions (should route Tier 1):**
- Test that the agent uses the correct metric and filter
- Include time period variations (last month, last quarter, YTD, specific date)
- Include group-by variations (by channel, by category, by region)

**Knowledge file questions (should route Tier 2):**
- Questions not covered by a single metric (top-N, comparisons, complex filters)
- Edge cases documented in DOMAIN_REFERENCE.md (e.g. timezone behaviour, null handling)

**Boundary questions (confirm correct tier selection):**
- A question that looks like it could hit two tiers — confirm the agent picks the right one
- A question about a deprecated table — confirm the agent redirects to the canonical table

Format each pair in the eval template:

```yaml
# eval_suite/orders_domain.yaml

domain: orders
created: YYYY-MM-DD
questions:
  - id: orders_001
    question: "What was total revenue last month?"
    expected_tier: semantic
    expected_metric: total_revenue
    expected_filter: "order__status = 'confirmed'"
    correct_answer_sql: |
      SELECT SUM(net_revenue) FROM fct_orders 
      WHERE DATE_TRUNC(order_date, MONTH) = DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH)
      AND status = 'confirmed'
    correct_answer_value: 1247832.50  # verified against source at YYYY-MM-DD
    tolerance_pct: 1  # allow 1% difference for daily refresh timing
    
  - id: orders_002
    question: "Which channel had the highest order count last quarter?"
    expected_tier: semantic
    expected_metric: order_count
    expected_group_by: channel
    correct_answer: "paid_search (14,231 orders)"
    tolerance_pct: 2
    
  - id: orders_003
    question: "Show me the top 5 customers by spend this year"
    expected_tier: curated
    expected_table: fct_orders
    correct_answer_format: "table with customer_name and total_spend columns"
    verification: domain_owner_confirmed  # exact values change daily
```

### Step 3: Verify Correct Answers

For every numeric answer, run the expected SQL against the warehouse to establish a ground-truth baseline at a fixed point in time. Record the date the baseline was captured — eval scores are relative to this baseline.

For non-numeric answers (rankings, tables), have the domain owner confirm the answer is correct.

### Step 4: Write the Eval Runner Script

Write `<dbt_project_path>/.claude/eval/run_evals.sh` (or `.wire/<release-folder>/artifacts/eval_suite/run_evals.sh`):

```bash
#!/bin/bash
# Agentic Data Stack Eval Runner
# Usage: ./run_evals.sh [domain]

DOMAIN=${1:-all}
PASS=0
FAIL=0
ERRORS=0

echo "Running agentic data stack evals — domain: $DOMAIN"
echo "================================================"

run_eval() {
  local id=$1
  local question=$2
  local expected_tier=$3
  
  echo -n "[$id] $question ... "
  
  # In practice, this invokes the agent and checks the response
  # For CI, use the dbt sl query tool directly for tier 1 checks
  # Response checking is manual or via LLM judge for non-numeric answers
  
  echo "PASS"
  ((PASS++))
}

# Source domain evals
if [[ "$DOMAIN" == "orders" || "$DOMAIN" == "all" ]]; then
  # [generated eval calls per domain]
  run_eval "orders_001" "What was total revenue last month?" "semantic"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed, $ERRORS errors"
echo "Pass rate: $(echo "scale=1; $PASS * 100 / ($PASS + $FAIL + $ERRORS)" | bc)%"

[[ $FAIL -eq 0 && $ERRORS -eq 0 ]] && exit 0 || exit 1
```

### Step 5: Write Per-Domain Accuracy Targets

For each domain, set the minimum accuracy threshold required for launch:

```yaml
# eval_targets.yaml
default_target: 90  # % pass rate required for domain launch

domains:
  orders:
    target: 90
    question_count: 15
    notes: "Finance sign-off on revenue questions required before launch"
  customers:
    target: 85
    question_count: 12
    notes: "PII fields in SQL output — privacy review required"
  marketing:
    target: 80
    question_count: 10
    notes: "Attribution methodology still being finalised — lower threshold"
```

### Step 6: Update Status

```yaml
eval_suite:
  generate: complete
  generated_date: YYYY-MM-DD
  total_questions: N
  domains_covered: N
  ci_runner: true
```

## Edge Cases

### Cannot Verify Answers Against Warehouse

If warehouse access is not available to verify correct answers, get domain owner sign-off on each question-answer pair. Record `verification: domain_owner_confirmed` in each eval. This is less reliable than warehouse-verified baselines — note this explicitly in the launch gate review.

### Daily Variance in Correct Answers

For questions about "today" or "last week", anchor the eval to a specific date and document the baseline value. The eval runner should always compare against the baseline at the anchor date, not the current live answer.

## Output

- `eval_suite/` folder containing per-domain YAML question files
- `eval_suite/run_evals.sh` — CI runner script
- `eval_suite/eval_targets.yaml` — per-domain accuracy thresholds
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
