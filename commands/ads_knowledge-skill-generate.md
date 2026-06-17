---
description: Generate per-domain reference files collocated with dbt models
argument-hint: <release-folder>
---

# Generate per-domain reference files collocated with dbt models

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
description: Generate per-domain reference files collocated with dbt models — the agent's knowledge base
argument-hint: <release-folder>
---

# Agentic Data Stack — Knowledge Skill Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Produce per-domain `DOMAIN_REFERENCE.md` files and colocate them with the dbt mart models they describe. These files are the agent's knowledge base — they narrow the search space from hundreds of tables to the specific entities, metrics, and query patterns relevant to a given domain. They live in the dbt repo and update when models change.

This directly implements the "knowledge skill" pattern from Anthropic's self-service analytics architecture: structured reference files maintained as engineering practice, not documentation overhead.

## Usage

```bash
/wire:ads_knowledge-skill-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `semantic_layer.review: approved`
- `canonical_models.review: approved`
- dbt project path accessible

## Workflow

### Step 1: Read Inputs

For each domain:
1. Read the canonical model schema.yml (column descriptions, tests, relationships)
2. Read `artifacts/governance_design.md` (canonical table, owner, tiering)
3. Read `artifacts/metric_audit.md` (metric definitions for this domain)
4. Read `artifacts/query_audit.md` (common question patterns for this domain — especially Raw-only patterns that need documentation)

### Step 2: Generate DOMAIN_REFERENCE.md for Each Domain

For each domain, write `<dbt_project_path>/models/marts/<domain>/DOMAIN_REFERENCE.md`:

```markdown
---
domain: orders
canonical_table: fct_orders
owner: data-platform@company.com
last_updated: YYYY-MM-DD
semantic_layer: dbt_semantic_layer  # or lookml | none
---

# Orders Domain Reference

## What This Domain Covers

Revenue from confirmed customer orders — net of returns and tax. Use this domain for 
questions about order volume, revenue, channels, and product performance.

**Not in this domain:** marketing attribution (see `marketing/DOMAIN_REFERENCE.md`), 
customer lifetime value (see `customers/DOMAIN_REFERENCE.md`).

## Canonical Table

**`project.analytics.fct_orders`**  
Grain: one row per order. Includes only confirmed and completed orders. Cancelled orders 
are excluded. Returns are captured via the `return_amount` field — they do not generate 
a separate row.

| Field | Type | Description |
|---|---|---|
| order_pk | STRING | Surrogate key (surrogate_key([order_id, source])) |
| order_id | STRING | Source system order identifier |
| customer_fk | STRING | FK → dim_customers.customer_pk |
| order_date | DATE | Date order was placed (not shipped) |
| net_revenue | NUMERIC | Revenue after returns and tax |
| gross_revenue | NUMERIC | Pre-deduction gross amount |
| channel | STRING | Acquisition channel: organic, paid_search, email, direct, affiliate |
| status | STRING | confirmed, shipped, delivered, returned |
| product_category | STRING | Top-level category from dim_products |

## Semantic Layer Metrics (use these first)

| Metric | dbt SL / LookML name | What it measures |
|---|---|---|
| Total Revenue | `total_revenue` | SUM(net_revenue) WHERE status = 'confirmed' |
| Order Count | `order_count` | COUNT DISTINCT order_pk WHERE status = 'confirmed' |
| Average Order Value | `avg_order_value` | total_revenue / order_count |
| Return Rate | `return_rate` | SUM(return_amount) / SUM(gross_revenue) |

Always query via the semantic layer for these metrics. Do not write raw SQL for `total_revenue` — 
the semantic layer filter is the canonical definition and raw SQL will silently include returns.

## Common Questions and How to Answer Them

### "What was revenue last month by channel?"
→ Semantic layer: `dbt sl query --metrics total_revenue --group-by channel,order__order_date__month`

### "How many orders were placed this week?"
→ Semantic layer: `dbt sl query --metrics order_count --group-by order__order_date__week`

### "Show me the top 10 customers by order value"
→ Curated SQL (no semantic metric for customer-level ranking):
```sql
SELECT
  c.customer_name,
  SUM(o.net_revenue) AS total_spend,
  COUNT(DISTINCT o.order_pk) AS order_count
FROM `project.analytics.fct_orders` o
JOIN `project.analytics.dim_customers` c ON o.customer_fk = c.customer_pk
WHERE o.status = 'confirmed'
GROUP BY c.customer_name
ORDER BY total_spend DESC
LIMIT 10
```

### "What's the return rate by product category?"
→ Semantic layer: `dbt sl query --metrics return_rate --group-by product_category`

## Known Limitations and Edge Cases

- Revenue figures are **net** throughout this domain. For gross comparisons (e.g. to external ad platforms reporting gross), use `gross_revenue` explicitly.
- `channel = 'unknown'` accounts for ~3% of orders. These are orders placed directly via the API without attribution data. Do not exclude them from totals.
- Orders placed on the last day of a month may appear in the following month's figures due to UTC timezone handling in `order_date`. For finance reporting, use `order_date_adjusted` which applies the client's local timezone.

## Deprecated Tables — Do Not Use

| Table | Replacement | Sunset date |
|---|---|---|
| orders_raw | fct_orders | YYYY-MM-DD |
| revenue_v2 | fct_orders | YYYY-MM-DD |
```

### Step 3: Colocate in dbt Project

Place each file alongside the canonical model:
```
<dbt_project_path>/models/marts/
  orders/
    fct_orders.sql
    fct_orders.yml
    DOMAIN_REFERENCE.md   ← generated here
  customers/
    dim_customers.sql
    dim_customers.yml
    DOMAIN_REFERENCE.md
```

### Step 4: Add CI Check (Optional but Recommended)

Add a check to the dbt project CI that flags when a model PR does not update the collocated DOMAIN_REFERENCE.md. This keeps the skill files current as the models evolve.

Create `.github/workflows/check-domain-reference.yml` (or equivalent):

```yaml
name: Check domain reference files
on: [pull_request]
jobs:
  check-domain-refs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Check for reference file updates
        run: |
          changed_models=$(git diff --name-only origin/main...HEAD -- 'models/marts/**/*.sql')
          if [ -n "$changed_models" ]; then
            for model in $changed_models; do
              domain_dir=$(dirname "$model")
              if [ ! -f "$domain_dir/DOMAIN_REFERENCE.md" ]; then
                echo "WARNING: $model changed but no DOMAIN_REFERENCE.md exists in $domain_dir"
              fi
            done
          fi
```

### Step 5: Write Knowledge Skill Index

Write `.wire/<release-folder>/artifacts/knowledge_skill_index.md` — a single index of all domain reference files and their locations, used by agent_config to route questions to the right file:

```markdown
# Knowledge Skill Index

| Domain | File path | Key entities | Last updated |
|---|---|---|---|
| orders | models/marts/orders/DOMAIN_REFERENCE.md | fct_orders, revenue, channels | YYYY-MM-DD |
| customers | models/marts/customers/DOMAIN_REFERENCE.md | dim_customers, segments | YYYY-MM-DD |
```

### Step 6: Update Status

```yaml
knowledge_skill:
  generate: complete
  generated_date: YYYY-MM-DD
  domains_covered: N
  files_written: N
  ci_check_added: true  # or false
```

## Edge Cases

### No dbt Project

If there is no dbt project, write the DOMAIN_REFERENCE files to `.wire/<release-folder>/artifacts/knowledge_skill/` instead. Note in the review that colocation with transformation code is not possible — the CI check for maintenance cannot be applied, and files will need manual updates when the warehouse schema changes.

## Output

- `DOMAIN_REFERENCE.md` files in `<dbt_project_path>/models/marts/<domain>/` (or artifacts folder)
- `.wire/<release-folder>/artifacts/knowledge_skill_index.md`
- `.github/workflows/check-domain-reference.yml` (if CI check requested)
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
