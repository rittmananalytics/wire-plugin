---
wire_schema: "1.0"
command: generate
artifact: knowledge_skill
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: canonical_models
    action: review
    outcome: approved
auto_validate: false          # validate exercises the live agent/semantic layer to test every "Common Questions" example
delegates_to:
  - utils/precondition_gate
description: Generate per-domain reference files collocated with dbt models — the agent's knowledge base
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

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

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `knowledge_skill`
- `artifact_name`: `Knowledge Skill`
- `file_path`: `.wire/[release_folder]/artifacts/knowledge_skill_index.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Edge Cases

### No dbt Project

If there is no dbt project, write the DOMAIN_REFERENCE files to `.wire/<release-folder>/artifacts/knowledge_skill/` instead. Note in the review that colocation with transformation code is not possible — the CI check for maintenance cannot be applied, and files will need manual updates when the warehouse schema changes.

## Output

- `DOMAIN_REFERENCE.md` files in `<dbt_project_path>/models/marts/<domain>/` (or artifacts folder)
- `.wire/<release-folder>/artifacts/knowledge_skill_index.md`
- `.github/workflows/check-domain-reference.yml` (if CI check requested)
- Updated `status.md`
