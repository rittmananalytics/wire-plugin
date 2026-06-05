---
domain: DOMAIN_NAME
canonical_table: project.schema.table_name
owner: team@company.com
last_updated: YYYY-MM-DD
semantic_layer: dbt_semantic_layer  # or: lookml | metricflow | none
---

# [Domain Name] Domain Reference

## What This Domain Covers

[One paragraph describing what business questions this domain answers and what entities it contains.]

**Not in this domain:** [What is explicitly out of scope — redirect to other domain files.]

## Canonical Table

**`project.schema.table_name`**  
Grain: [one row per X]  
[Brief description of inclusion/exclusion rules.]

| Field | Type | Description |
|---|---|---|
| [entity]_pk | STRING | Surrogate key |
| [entity]_id | STRING | Source system identifier |
| [date_field] | DATE | [Description] |
| [measure_field] | NUMERIC | [Description including whether net/gross/pre/post] |

## Semantic Layer Metrics (use these first)

| Metric | dbt SL / LookML name | What it measures |
|---|---|---|
| [Display name] | `metric_name` | [Definition] |

Always query via the semantic layer for these metrics. Do not write raw SQL for metrics defined here — the semantic layer filter is the canonical definition.

## Common Questions and How to Answer Them

### "[Common question 1]"
→ Semantic layer: `dbt sl query --metrics metric_name --group-by dimension`

### "[Common question 2]"
→ Curated SQL:
```sql
SELECT
  [fields]
FROM `canonical_table`
WHERE [filter]
GROUP BY [dimensions]
ORDER BY [ordering]
```

## Known Limitations and Edge Cases

- [Timezone handling notes]
- [Null value behaviour]
- [Filter edge cases]
- [Known data quality issues]

## Deprecated Tables — Do Not Use

| Table | Replacement | Sunset date |
|---|---|---|
| [deprecated_table] | [canonical_table] | YYYY-MM-DD |
