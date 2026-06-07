---
name: snowflake-semantic-views
description: Skill for creating, altering, validating, auditing, and debugging Snowflake semantic views for Cortex Analyst. Auto-activates when the user wants to build or maintain a Snowflake semantic layer, run Cortex Analyst, or validate verified queries. Covers SQL DDL workflow, YAML workflow, FastGen, and VQR validation.
---

# Snowflake Semantic Views Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | snowflake-semantic-views | activated | Snowflake semantic view work triggered this skill |
```

## Purpose

Snowflake semantic views are the metadata layer that powers Cortex Analyst — Snowflake's natural-language-to-SQL service. A semantic view maps business concepts (entities, facts, dimensions, metrics, relationships) onto physical tables so Cortex can generate accurate SQL from plain English questions.

This skill governs how we create, modify, validate, and audit them. It operates via the Snowflake MCP server (`mcp__claude_ai_Snowflake__sql_exec`) and the Snowflake CLI (`snow`) where available.

## When This Skill Activates

- "Create a semantic view for..."
- "Add a metric / dimension / fact to this semantic view..."
- "Validate the semantic view against our schema..."
- "Why is Cortex Analyst generating wrong SQL?"
- "Audit our semantic views..."
- "Add a verified query to..."
- References to `CREATE SEMANTIC VIEW`, `CORTEX ANALYST`, or `SYSTEM$CORTEX_ANALYST_FAST_GENERATION`
- Files ending in `.semantic.yaml` or `semantic_view.sql`

---

## Instructions

### Step 0: Establish Context

Before any work:

```sql
SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();
```

Confirm role has `CREATE SEMANTIC VIEW` privilege on the target schema. If not, advise the user on the grant needed:

```sql
GRANT CREATE SEMANTIC VIEW ON SCHEMA my_db.my_schema TO ROLE analyst_role;
```

Check if FastGen is available (Snowflake Enterprise / Business Critical, 2024+):

```sql
SELECT SYSTEM$CORTEX_ANALYST_FAST_GENERATION IS NOT NULL;
```

If this returns an error rather than TRUE/FALSE, FastGen is not available — fall back to SQL DDL or YAML workflow.

---

### Step 1: Choose Creation Mode

| Mode | When to use |
|------|-------------|
| **FastGen** (preferred) | New view from existing tables; FastGen available; tables have comments and PKs |
| **SQL DDL** | Full control needed; FastGen unavailable; complex relationship graph |
| **YAML** | Iterative editing; version-controlled definitions; `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML` available |
| **Existing view retrieval** | Editing or auditing an existing semantic view |

---

### Step 2: Inspect Before Creating

Always run schema discovery before authoring DDL or YAML.

**Get table structure:**
```sql
DESCRIBE TABLE my_db.my_schema.orders;
```

**Get existing column comments:**
```sql
SELECT column_name, data_type, comment
FROM information_schema.columns
WHERE UPPER(table_schema) = UPPER('MY_SCHEMA')
  AND UPPER(table_name) = UPPER('ORDERS')
ORDER BY ordinal_position;
```

**Get primary/unique keys (required for RELATIONSHIP targets):**
```sql
SHOW PRIMARY KEYS IN TABLE my_db.my_schema.orders;
SHOW UNIQUE KEYS IN TABLE my_db.my_schema.orders;
```

**Sample data to understand values:**
```sql
SELECT * FROM my_db.my_schema.orders LIMIT 20;
```

**If editing an existing semantic view, retrieve the current definition:**
```sql
SELECT GET_DDL('SEMANTIC VIEW', 'my_db.my_schema.orders_sv');
```

---

### Step 3: Author the Semantic View

#### SQL DDL Workflow

Follow this clause order exactly — Snowflake parses the DDL sequentially and references in later clauses depend on earlier declarations:

```sql
CREATE OR REPLACE SEMANTIC VIEW my_db.my_schema.orders_sv
  TABLES (
    orders PRIMARY KEY (order_id)
      COMMENT 'Transactional order records',
    customers PRIMARY KEY (customer_id)
      COMMENT 'Customer master'
  )
  RELATIONSHIPS (
    orders FOREIGN KEY (customer_id) REFERENCES customers
  )
  FACTS (
    orders (
      order_id   COMMENT 'Unique order identifier',
      order_date COMMENT 'Date the order was placed',
      order_total COMMENT 'Total order value in USD'
    )
  )
  DIMENSIONS (
    customers (
      customer_id    COMMENT 'Unique customer identifier',
      customer_name  COMMENT 'Full name of the customer',
      country        COMMENT 'Customer billing country'
    )
  )
  METRICS (
    total_revenue AS SUM(orders.order_total)
      COMMENT 'Sum of all order totals',
    order_count AS COUNT(DISTINCT orders.order_id)
      COMMENT 'Number of distinct orders',
    avg_order_value AS AVG(orders.order_total)
      COMMENT 'Average order total'
  )
  COMMENT = 'Semantic model for order analytics. Supports Cortex Analyst queries on revenue, customer behaviour, and order volume.'
  AI_SQL_GENERATION ENABLED
  AI_QUESTION_CATEGORIZATION ENABLED;
```

**Rules:**
- `facts` not `measures` — `measures` is deprecated
- All tables must declare a `PRIMARY KEY` or have one defined on the physical table
- `RELATIONSHIP` targets must have a unique or primary key on the referenced column
- Comments and descriptions are required on all facts, dimensions, and metrics — read existing Snowflake column comments first; never invent business terminology without user approval
- `AI_SQL_GENERATION ENABLED` unlocks Cortex Analyst; omitting it makes the view non-queryable by Cortex
- `AI_QUESTION_CATEGORIZATION ENABLED` groups suggested questions by topic — add unless told otherwise

**Validate with a temp name before final deployment:**
```sql
CREATE OR REPLACE SEMANTIC VIEW my_db.my_schema.orders_sv__tmp_validate
  -- same DDL as above
  ;

-- Smoke test
SELECT * FROM my_db.my_schema.orders_sv__tmp_validate LIMIT 1;

-- Clean up
DROP SEMANTIC VIEW my_db.my_schema.orders_sv__tmp_validate;
```

Only deploy the real name after validation passes.

---

#### YAML Workflow

When working iteratively or version-controlling the definition:

1. Author (or edit) the YAML spec locally as `orders_sv.semantic.yaml`
2. Verify without deploying (third arg `TRUE`):

```sql
SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'my_db.my_schema.orders_sv',
  $$ <yaml content here> $$,
  TRUE   -- verify-only, no deployment
);
```

If verify-only returns no errors:

3. Deploy:

```sql
SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'my_db.my_schema.orders_sv',
  $$ <yaml content here> $$,
  FALSE  -- deploy
);
```

YAML format mirrors the DDL structure — tables, relationships, facts, dimensions, metrics, comments — as a structured YAML document. Get the schema from `DESCRIBE SEMANTIC VIEW` on an existing view or Snowflake documentation.

---

#### FastGen Workflow

When FastGen is available:

```sql
SELECT SYSTEM$CORTEX_ANALYST_FAST_GENERATION(
  'my_db.my_schema',   -- target schema
  ARRAY_CONSTRUCT('orders', 'customers', 'products')  -- tables to include
);
```

FastGen returns a draft YAML. Review it before deploying:
- Check all identified relationships are correct
- Verify metric definitions match business intent
- Add or correct comments where FastGen has inferred generic descriptions
- Get user approval on metric formulas

Then deploy via the YAML workflow above.

---

### Step 4: Add Verified Queries (VQR)

Verified queries are example NL-question → SQL pairs that Cortex uses as few-shot examples. They dramatically improve accuracy on common questions.

**Rules:**
- The SQL in a VQR must use semantic view constructs — `orders_sv.total_revenue`, not `SUM(orders.order_total)`
- Run the SQL and confirm the result matches the expected answer exactly before adding
- Approximate matches = failure; results must be deterministic

**Add via DDL:**
```sql
ALTER SEMANTIC VIEW my_db.my_schema.orders_sv
  ADD AI_VERIFIED_QUERIES (
    (
      QUESTION = 'What was total revenue last month?',
      SQL = 'SELECT orders_sv.total_revenue FROM orders_sv WHERE DATE_TRUNC(''month'', orders_sv.order_date) = DATE_TRUNC(''month'', DATEADD(month, -1, CURRENT_DATE()))'
    ),
    (
      QUESTION = 'Who are the top 10 customers by revenue?',
      SQL = 'SELECT orders_sv.customer_name, orders_sv.total_revenue FROM orders_sv ORDER BY orders_sv.total_revenue DESC LIMIT 10'
    )
  );
```

Never add VQRs that return different results across runs (non-deterministic queries with relative date logic can drift — use fixed date ranges for testing, then adjust for production use).

---

### Step 5: Audit Workflow

When asked to audit all semantic views in an account or schema:

```sql
-- List all semantic views
SHOW SEMANTIC VIEWS IN DATABASE my_db;
```

```sql
-- Get DDL for each
SELECT GET_DDL('SEMANTIC VIEW', 'my_db.my_schema.orders_sv');
```

For each semantic view, check:

| Check | Pass Condition |
|---|---|
| All tables have PRIMARY KEY declared | No table block missing `PRIMARY KEY` |
| All RELATIONSHIP targets have unique key | Foreign key references a PK or UNIQUE key column |
| All facts/dimensions/metrics have COMMENTs | No empty COMMENT strings |
| `AI_SQL_GENERATION` is enabled | Present in DDL |
| At least 3 verified queries present | Count VQR entries in DDL |
| View compiles without error | `GET_DDL` returns without exception |
| Cortex can answer a test question | Run `CORTEX.ANALYST` with a test prompt |

Produce an audit table:

```
## Semantic View Audit — my_db
Date: {TODAY}

| View | Tables | Relationships | Metrics | VQRs | Missing Comments | AI Enabled | Status |
|------|--------|---------------|---------|------|-----------------|------------|--------|
| orders_sv | 2 | 1 | 3 | 5 | 0 | Yes | PASS |
| products_sv | 3 | 0 | 2 | 0 | 4 | Yes | WARN: no relationships, no VQRs, 4 missing comments |
```

---

### Step 6: Debug Workflow

When Cortex Analyst generates wrong SQL:

1. Retrieve the generated SQL from the Cortex response
2. Compare it to the semantic view DDL line by line
3. Common failure modes:

| Symptom | Likely cause | Fix |
|---|---|---|
| Wrong join path | Missing or incorrect RELATIONSHIP | Add/correct the foreign key relationship |
| Metric calculation wrong | Metric formula too broad (missing filter) | Refine metric definition or add a filtered variant |
| Missing column | Column not declared in FACTS or DIMENSIONS | Add the column with a comment |
| Ambiguous column name | Same name appears in multiple tables | Prefix in the fact/dimension block: `orders.status COMMENT '...'` |
| Date filter wrong | No temporal scope declared | Add a `temporal_scope` annotation or VQR with correct date logic |
| Wrong aggregation | Metric defined as SUM but user wants COUNT | Add a second metric, or clarify with a verified query |

4. Make the smallest targeted change to the view — don't rewrite everything
5. Validate with a temp object before deploying the fix
6. Add a VQR that covers the failing question to prevent regression

---

### Step 7: Stopping Points

Always ask before:
- Creating or replacing the final (non-temp) semantic view
- Dropping any non-temp object
- Adding inferred VQRs — present them for approval first
- Mining account query history to generate VQR suggestions (`ACCOUNT_USAGE.QUERY_HISTORY` — requires approval)
